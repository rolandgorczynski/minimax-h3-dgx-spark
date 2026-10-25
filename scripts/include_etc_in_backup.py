#!/usr/bin/python3 -I
"""Nur /etc als vollständige Backup-Quelle eintragen; startet nichts."""
import datetime
import fcntl
import json
import os
from pathlib import Path
import shutil


def main():
    if os.geteuid()!=0:raise SystemExit('Bitte einmal mit sudo ausführen.')
    path=Path('/etc/docker-rsnapshot.json')
    if path.is_symlink():raise SystemExit('Konfigurations-Symlink bitte zuerst prüfen.')
    data=json.loads(path.read_text())
    root=Path(data['state_root'])
    root.mkdir(mode=0o700,parents=True,exist_ok=True)
    with (root/'lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise SystemExit('Eine Sicherung läuft. Konfiguration nicht geändert.')
        for key in ('additional_sources','optional_sources'):
            data[key]=[s for s in data.get(key,[]) if not Path(s).is_relative_to('/etc')]
        data['additional_sources'].append('/etc')
        text=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
        if text==path.read_text():
            print('/etc ist bereits vollständig als Quelle eingerichtet. Nichts gestartet.');return
        stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        previous=path.with_name(path.name+'.vor-etc-'+stamp)
        shutil.copy2(path,previous)
        temporary=path.with_name(path.name+'.etc-tmp')
        if temporary.exists() or temporary.is_symlink():raise SystemExit('Temporäre Datei existiert; bitte zuerst prüfen.')
        info=path.stat()
        with temporary.open('x') as stream:
            stream.write(text);stream.flush();os.fsync(stream.fileno())
        os.chown(temporary,info.st_uid,info.st_gid);temporary.chmod(info.st_mode & 0o777)
        temporary.replace(path)
        fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)
        print('/etc vollständig als Backup-Quelle eingerichtet. Vorherige Konfiguration: '+str(previous))
        print('Keine Sicherung, keine Dienste und kein Cronjob gestartet.')


if __name__=='__main__':main()
