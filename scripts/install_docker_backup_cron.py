#!/usr/bin/python3 -I
"""Wöchentlichen Root-Cronjob ergänzen; startet jetzt keine Sicherung."""
import datetime
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess

JOB='0 3 * * 0 /usr/local/sbin/docker-rsnapshot-weekly --run >> /var/log/docker-offline-backup.log 2>&1'
MARKER='# Docker-Offline-Sicherung: Sonntag 03:00, lokale Systemzeit; Inhaltsprüfung separat.'


def merge(current):
    active=[line.strip() for line in current.splitlines() if line.strip() and not line.lstrip().startswith('#')]
    if JOB in active:return current,False
    if any('/usr/local/sbin/docker-rsnapshot-weekly' in line for line in active):
        raise RuntimeError('Ein anderer Zeitplan für dieses Backup existiert bereits; bitte bewusst zusammenführen.')
    if any(re.search(r'(^|[ /])rsnapshot(?:\s|$)',line) for line in active):
        raise RuntimeError('Direkter rsnapshot-Cronjob vorhanden; parallele Zeitpläne zuerst klären.')
    if any(re.match(r'(?:CRON_TZ|TZ)\s*=',line) for line in active):
        raise RuntimeError('Zeitzonenüberschreibung in der Root-Crontab bitte zuerst prüfen.')
    return current.rstrip()+'\n\n'+MARKER+'\n'+JOB+'\n',True


def main():
    if os.geteuid()!=0:raise SystemExit('Bitte einmal mit sudo ausführen.')
    os.umask(0o077)
    wrapper=Path('/usr/local/sbin/docker-rsnapshot-weekly')
    checker=Path('/usr/local/sbin/docker-rsnapshot-checksums')
    if not wrapper.is_file() or not checker.is_file():
        raise SystemExit('Zuerst scripts/update_docker_rsnapshot.py mit sudo installieren.')
    data=json.loads(Path('/etc/docker-rsnapshot.json').read_text())
    if '/etc' not in data['additional_sources']:
        raise SystemExit('Die vollständige /etc-Quelle fehlt; zuerst scripts/update_docker_rsnapshot.py mit sudo ausführen.')
    old=Path('/etc/cron.d/rsnapshot')
    if old.exists() and any(line.strip() and not line.lstrip().startswith('#') and 'rsnapshot' in line
                           for line in old.read_text().splitlines()):
        raise SystemExit('Direkte rsnapshot-Jobs in /etc/cron.d/rsnapshot sind noch aktiv. Nicht parallel aktivieren.')
    root=Path(data['state_root']);root.mkdir(mode=0o700,parents=True,exist_ok=True)
    with (root/'lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise SystemExit('Backup oder Inhaltsprüfung läuft noch; Cron-Einrichtung später ausführen.')
        result=subprocess.run(['crontab','-l'],capture_output=True,text=True,env={**os.environ,'LC_ALL':'C'})
        if result.returncode==0:current=result.stdout
        elif result.returncode==1 and 'no crontab for' in result.stderr.lower():current=''
        else:raise SystemExit('Root-Crontab konnte nicht gelesen werden: '+result.stderr.strip())
        updated,changed=merge(current)
        if not changed:
            print('Dieser Cronjob ist bereits eingetragen. Nichts gestartet.');return
        previous=root/'cron-originale';previous.mkdir(mode=0o700,exist_ok=True)
        stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        with (previous/(stamp+'.crontab')).open('x') as stream:
            stream.write(current);stream.flush();os.fsync(stream.fileno())
        subprocess.run(['crontab','-'],input=updated,text=True,check=True)
        print('Root-Cronjob aktiviert: jeden Sonntag 03:00 Uhr, lokale Systemzeit.')
        print('Log: /var/log/docker-offline-backup.log. Prüfsummenprüfung bleibt manuell.')
        print('Jetzt wurde keine Sicherung gestartet und kein Dienstzustand geändert.')
        journal=root/'status.json'
        if journal.exists() and json.loads(journal.read_text()).get('phase')!='fertig':
            print('Achtung: Der vorherige Lauf ist nicht abgeschlossen. Bis zur Klärung blockiert dieses Journal auch Cron-Läufe.')


if __name__=='__main__':main()
