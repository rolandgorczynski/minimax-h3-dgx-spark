#!/usr/bin/python3 -I
"""Backup-Abschluss prüfen, /etc-Update und Wochen-Cron einrichten. Startet keine Dienste."""
import datetime
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys

PROJECT=Path(__file__).resolve().parents[1]
CONFIG=Path('/etc/docker-rsnapshot.json')


def check_success(settings):
    root=Path(settings['state_root'])
    journal=root/'status.json'
    if not journal.exists():raise RuntimeError('Kein abgeschlossener Backup-Lauf dokumentiert.')
    state=json.loads(journal.read_text())
    print('Letzter Backup-Start: '+state.get('started','unbekannt'),flush=True)
    print('Letzte Phase: '+state.get('phase','unbekannt'),flush=True)
    if state.get('phase')!='fertig' or not state.get('verified'):
        detail=state.get('error','Kein erfolgreicher Abschluss dokumentiert.')
        raise RuntimeError('Voriger Lauf ist nicht erfolgreich abgeschlossen: '+detail+'\nStatus: '+str(journal))
    mount=json.loads(subprocess.check_output(['findmnt','--json','--target',settings['backup_mount'],
                                            '--output','TARGET,UUID'],text=True))['filesystems'][0]
    if mount['target']!=settings['backup_mount'] or mount.get('uuid')!=settings['backup_uuid']:
        raise RuntimeError('Das erwartete Backup-Laufwerk ist nicht eingehängt.')
    snapshot=Path(settings['snapshot_root'])/'weekly.0'
    if snapshot.is_symlink() or not snapshot.is_dir():raise RuntimeError('weekly.0 fehlt oder ist ein Symlink.')
    frozen=snapshot/'localhost'/str(root).lstrip('/')/'export'/'dienstzustand.json'
    saved=json.loads(frozen.read_text())
    if saved.get('started')!=state.get('started'):
        raise RuntimeError('Journal und jüngster Snapshot gehören nicht zum gleichen Lauf.')
    print('Erfolgreicher Wochenstand bestätigt: '+str(snapshot),flush=True)
    return state


def checked_status(settings):
    root=Path(settings['state_root'])
    if not root.is_dir():raise RuntimeError('Backup-Zustandsverzeichnis fehlt.')
    with (root/'lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        return check_success(settings)


def main():
    if os.geteuid()!=0:raise RuntimeError('Bitte einmal mit sudo ausführen.')
    os.umask(0o077)
    settings=json.loads(CONFIG.read_text())
    checked_status(settings)
    print('Installiere /etc und separaten manuellen Prüfsummenjob …',flush=True)
    subprocess.run(['/usr/bin/python3','-I',str(PROJECT/'scripts/update_docker_rsnapshot.py')],check=True)
    # Die Helfer verwenden dasselbe Lock. Bei einem inzwischen gestarteten Lauf
    # abbrechen, statt einen ungeprüften bzw. parallelen Zustand zu übergehen.
    settings=json.loads(CONFIG.read_text());checked_status(settings)
    print('Richte Root-Cronjob für Sonntag 03:00 Uhr ein …',flush=True)
    subprocess.run(['/usr/bin/python3','-I',str(PROJECT/'scripts/install_docker_backup_cron.py')],check=True)
    report={'finished':datetime.datetime.now().astimezone().isoformat(),
            'backup_confirmed':True,'etc_enabled':True,'checksums_manual':True,
            'cron':'Sonntag 03:00 lokale Systemzeit','services_started':False,'old_data_deleted':False}
    path=Path(settings['state_root'])/'einrichtung-abgeschlossen.json'
    with path.open('w') as stream:
        json.dump(report,stream,ensure_ascii=False,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
    print('FERTIG: Backup-Abschluss bestätigt, Update installiert und Wochen-Cron eingerichtet.')
    print('Keine Dienste oder Sicherung gestartet. Alte Modelle und Volumes bleiben erhalten.')


if __name__=='__main__':
    try:main()
    except (Exception,KeyboardInterrupt) as error:
        print('ANGEHALTEN: '+(str(error) or type(error).__name__),file=sys.stderr)
        print('Kein Backup-Status als erfolgreich umgeschrieben und keine Dienste gestartet.',file=sys.stderr)
        sys.exit(1)
