#!/usr/bin/python3 -I
"""/etc aufnehmen und manuelle Inhaltsprüfung installieren. Startet keine Jobs/Dienste."""
import ast
import datetime
import fcntl
import json
import os
from pathlib import Path
import shutil

CONFIG=Path('/etc/docker-rsnapshot.json')
WRAPPER=Path('/usr/local/sbin/docker-rsnapshot-weekly')
CHECKER=Path('/usr/local/sbin/docker-rsnapshot-checksums')
PROJECT=Path(__file__).resolve().parents[1]


def add_etc(data):
    for key in ('additional_sources','optional_sources'):
        data[key]=[p for p in data.get(key,[]) if not Path(p).is_relative_to('/etc')]
    data['additional_sources'].append('/etc')
    return data


def no_content_checks(base):
    lines=[]
    for line in base.splitlines():
        fields=line.split()
        if fields and fields[0]=='rsync_long_args':
            line='rsync_long_args\t'+' '.join(a for a in fields[1:] if a not in ('--checksum','-c'))
        if fields and fields[0]=='rsync_short_args':
            line='rsync_short_args\t'+' '.join(a.replace('c','') if a.startswith('-') and not a.startswith('--') else a for a in fields[1:])
        lines.append(line)
    return '\n'.join(lines)+'\n'


def replace(path,text,default_mode):
    old=path.stat() if path.exists() else None
    temporary=path.with_name(path.name+'.update-tmp')
    with temporary.open('x') as stream:
        stream.write(text);stream.flush();os.fsync(stream.fileno())
    os.chown(temporary,old.st_uid if old else 0,old.st_gid if old else 0)
    temporary.chmod(old.st_mode & 0o777 if old else default_mode)
    temporary.replace(path)
    fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)


def main():
    if os.geteuid()!=0:raise SystemExit('Bitte einmal mit sudo ausführen.')
    data=json.loads(CONFIG.read_text())
    root=Path(data['state_root']);root.mkdir(mode=0o700,parents=True,exist_ok=True)
    with (root/'lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise SystemExit('Backup oder Prüfung läuft noch. Nichts geändert; später erneut ausführen.')
        program=(PROJECT/'scripts/docker_rsnapshot_weekly.py').read_text();ast.parse(program)
        checker=(PROJECT/'scripts/docker_rsnapshot_checksums.sh').read_text()
        base=Path(data['base_config'])
        changes=[(WRAPPER,program,0o700),(CHECKER,checker,0o700),
                 (CONFIG,json.dumps(add_etc(data),ensure_ascii=False,indent=2)+'\n',0o600),
                 (base,no_content_checks(base.read_text()),0o600)]
        for path,_,_ in changes:
            if path.is_symlink():raise SystemExit('Symlink zuerst prüfen: '+str(path))
            if path.with_name(path.name+'.update-tmp').exists() or path.with_name(path.name+'.update-tmp').is_symlink():
                raise SystemExit('Temporäre Updatedatei existiert: '+str(path))
        stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        previous=root/'updates'/stamp;previous.mkdir(parents=True,mode=0o700)
        for index,(path,_,_) in enumerate(changes):
            if path.exists():shutil.copy2(path,previous/(str(index)+'-'+path.name))
        for path,text,mode in changes:replace(path,text,mode)
        print('/etc ist vollständig aufgenommen. Reguläres Backup prüft Größe, Zeitstempel und Metadaten.')
        print('Codex-Daten, Browser-Caches und CUPS-Abonnementdateien werden mitgesichert; ihre Änderungen blockieren die Abschlussprüfung nicht.')
        print('Manuelle Inhaltsprüfung: sudo /usr/local/sbin/docker-rsnapshot-checksums')
        print('Originale vor Update: '+str(previous))
        journal=root/'status.json'
        if journal.exists() and json.loads(journal.read_text()).get('phase')!='fertig':
            print('Hinweis: Der vorige Backup-Lauf ist laut Journal nicht abgeschlossen. Status bleibt unverändert; vor erneutem Backup prüfen.')
            print('Bei einem gescheiterten Quellenvergleich: sudo /usr/local/sbin/docker-rsnapshot-weekly --resume')
        print('Keine Sicherung, keine Prüfung, kein Cronjob und keine Dienste gestartet.')


if __name__=='__main__':main()
