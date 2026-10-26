#!/usr/bin/python3
"""Nur die zwei alten, durch Bind-Mounts ersetzten Docker-Volumes entfernen."""
import json
import os
from pathlib import Path
import subprocess
import sys

TARGETS = {
    "comic-automation_comic-automation-data": (
        "comic-automation-comic-automation-1", "/home/jee/docker-data/comic-automation", "/data", "jobs.sqlite3"
    ),
    "linux-open-source-games_updater_state": (
        "linux-open-source-games-updater-1", "/home/jee/docker-data/games-updater", "/state", "status.json"
    ),
}

def run(*args):
    return subprocess.check_output(args, text=True)

def main():
    if os.geteuid() != 0:
        raise RuntimeError("Bitte mit sudo python3 -I ausführen.")
    ids = run("docker", "ps", "-aq").split()
    containers = json.loads(run("docker", "inspect", *ids)) if ids else []
    names = {c["Name"].lstrip("/"): c for c in containers}
    existing = set(run("docker", "volume", "ls", "-q").split())
    selected = []
    # Sämtliche Prüfungen vor der ersten Löschung.
    for volume, (container, source, destination, marker) in TARGETS.items():
        if volume not in existing:
            print("Bereits entfernt: " + volume)
            continue
        info = json.loads(run("docker", "volume", "inspect", volume))[0]
        if info["Driver"] != "local" or info.get("Options"):
            raise RuntimeError("Unerwarteter Volume-Typ: " + volume)
        for c in containers:
            if any(m.get("Name") == volume or
                   m.get("Source", "").rstrip("/") == info["Mountpoint"].rstrip("/")
                   for m in c["Mounts"]):
                raise RuntimeError("Volume wird noch verwendet: " + volume + " durch " + c["Name"])
        c = names.get(container)
        if not c or not c["State"]["Running"]:
            raise RuntimeError("Erwartete Anwendung läuft nicht: " + container)
        if c["State"].get("Health", {}).get("Status") != "healthy":
            raise RuntimeError("Anwendung ist nicht gesund: " + container)
        path = Path(source)
        if path.is_symlink() or not path.is_dir() or not (path / marker).is_file():
            raise RuntimeError("Neue Anwendungsdaten fehlen: " + source)
        if not any(m["Type"] == "bind" and m["Source"] == source and
                   m["Destination"] == destination and m.get("RW")
                   for m in c["Mounts"]):
            raise RuntimeError("Erwartete neue Einbindung fehlt: " + container)
        selected.append(volume)
    for volume in selected:
        # Ohne --force: Docker verweigert zwischenzeitlich belegte Volumes.
        subprocess.run(["docker", "volume", "rm", volume], check=True)
    print("Fertig. Nur die aufgeführten alten Volumes entfernt. Keine Dienste gestoppt oder gestartet.")

if __name__ == "__main__":
    try:
        main()
    except (Exception, KeyboardInterrupt) as error:
        print("ABGEBROCHEN: " + str(error), file=sys.stderr)
        sys.exit(1)
