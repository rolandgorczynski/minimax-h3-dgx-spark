#!/usr/bin/env python3
"""Gezielter Cron-Anstoß für die Skriptvorarbeit in einer bestehenden Codex-Unterhaltung."""
import argparse
from datetime import datetime
import fcntl
import json
import os
from pathlib import Path
import shlex
import sqlite3
import subprocess
import sys

PROJECT=Path(__file__).resolve().parents[1]
ROOT=Path('/home/jee/docker-data/comic-skript-cron')
CONFIG=ROOT/'config.json'
LEDGER=Path('/home/jee/docker-data/comic-sinnanalyse-redaktion/skriptauftrag.json')
CODEX=Path('/home/jee/.local/bin/codex')
STATE_DB=Path('/home/jee/.codex/state_5.sqlite')
TAG='# comic-skript-fortsetzen'
PREFIX='[Automatischer Comic-Skriptauftrag]'


def write_json(path,value):
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');tmp.replace(path)


def log(message):
    line=datetime.now().astimezone().isoformat(timespec='seconds')+' '+message
    print(line,flush=True)
    with (ROOT/'trigger.log').open('a') as f:f.write(line+'\n')


def progress(path=LEDGER):
    entries=json.loads(path.read_text())['entries']
    return sum(e['status']=='fertig' for e in entries),sum(e['status']!='fertig' for e in entries)


def thread_status(thread):
    with sqlite3.connect('file:'+str(STATE_DB)+'?mode=ro',uri=True) as db:
        row=db.execute('SELECT cwd,rollout_path,archived FROM threads WHERE id=?',(thread,)).fetchone()
    if not row or Path(row[0]).resolve()!=PROJECT or row[2]:
        raise RuntimeError('Zielunterhaltung fehlt, ist archiviert oder gehört zu einem anderen Projekt.')
    # Nur den Schluss lesen: die langjährige Unterhaltung ist mehrere hundert MB groß.
    with Path(row[1]).open('rb') as stream:
        stream.seek(0,2);size=stream.tell();start=max(0,size-8*1024*1024);stream.seek(start)
        if start:stream.readline()
        latest=None
        for line in stream:
            try:event=json.loads(line)
            except ValueError:continue
            payload=event.get('payload',{})
            if event.get('type')=='event_msg' and payload.get('type') in ('task_started','task_complete','turn_aborted'):
                latest=payload['type']
    if latest=='task_complete':return 'bereit'
    if latest=='task_started':return 'beschäftigt'
    return 'unbekannt oder unterbrochen'


def tick(config,send=False):
    if not config.get('enabled'):
        log('PAUSIERT: Kein Auftrag gesendet.');return
    done,pending=progress()
    if not pending:
        log('FERTIG: Alle Skripte erledigt, kein Auftrag gesendet.');return
    status=thread_status(config['thread_id'])
    state_path=ROOT/'status.json'
    previous=json.loads(state_path.read_text()) if state_path.exists() else {}
    if status!='bereit':
        log('WARTET: Unterhaltung '+status+'. Kein Auftrag gesendet.');return
    if previous.get('pending') and done<=previous['completed_before']:
        log('WARTET: Voriger Auftrag noch ohne bestätigten Fortschritt. Kein Doppelauftrag.');return
    message=(PREFIX+' Mach die nächsten vier noch offenen redaktionellen Comic-Skripte aus '
             '/home/jee/docker-data/comic-sinnanalyse-redaktion/skriptauftrag.json fertig. '
             'Lies zuerst docs/Comic_Skriptvorarbeit_Fortschritt.md und die betreffenden Quellen samt Sinnanalyse. '
             'Empfohlene Kachelzahl übernehmen, Handlung und Kontinuität prüfen, deutsche Texte und eindeutige Sprecher. '
             'Schreibe die Skripte selbst; kein lokales oder separates Modell als Ersatzautor. '
             'Nur als neue Geschichten importieren, Beschriftung prüfen, Auftragsstatus und Fortschrittsdatei aktualisieren. '
             'Keine Bilder erzeugen, keine vorhandenen Geschichten überschreiben, keine anderen todo-Punkte bearbeiten. '
             'Pro Trigger höchstens vier Skripte. Bei fehlendem Limit oder einem Fehler offen berichten, keine Erfolgsmeldung vortäuschen. '
             'Neuere manuelle Anweisungen des Nutzers haben Vorrang; bei Pause oder Abbruch keine Skriptarbeit starten und den Cron pausieren.')
    if not send:
        log(f'PLAN: {done} fertig, {pending} offen. Ein Folgeauftrag an {config["thread_id"]}; nichts gesendet.');return
    # Vor dem Senden markieren: auch bei Absturz/Timeout keine blinde Doppelzustellung.
    state={'pending':True,'completed_before':done,'sent_at':datetime.now().astimezone().isoformat(),'phase':'senden'}
    write_json(state_path,state)
    result=subprocess.run([str(CODEX),'queue','--thread',config['thread_id'],'--message',message],cwd=PROJECT,text=True,capture_output=True,timeout=60)
    state['phase']='eingereiht' if result.returncode==0 else 'sendefehler'
    state['exit_code']=result.returncode;write_json(state_path,state)
    if result.returncode:
        raise RuntimeError('Codex hat die Zustellung nicht bestätigt. Status prüfen; kein automatischer Doppelversuch.')
    log(f'EINGEREIHT: Nächste vier Skripte; vorher {done} fertig, {pending} offen.')


def cron(config,remove=False):
    result=subprocess.run(['/usr/bin/crontab','-l'],text=True,capture_output=True)
    if result.returncode not in (0,1):raise RuntimeError('Crontab konnte nicht gelesen werden.')
    if result.returncode==1 and result.stdout.strip():raise RuntimeError('Unerwartete Crontab-Antwort.')
    before=result.stdout
    lines=[line for line in before.splitlines() if not line.endswith(TAG)]
    if not remove:
        lines.append(config['schedule']+' /usr/bin/python3 '+shlex.quote(str(Path(__file__).resolve()))+' --tick >> '+shlex.quote(str(ROOT/'cron.log'))+' 2>&1 '+TAG)
    backup=ROOT/('crontab-vorher-'+datetime.now().strftime('%Y%m%dT%H%M%S%f')+'.txt');backup.write_text(before)
    subprocess.run(['/usr/bin/crontab','-'],input='\n'.join(lines)+'\n',text=True,check=True)
    log('Cron entfernt.' if remove else 'Cron eingerichtet: '+config['schedule']+'. Noch kein Arbeitsauftrag gesendet.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tick',action='store_true',help='Einen Auftrag senden, sofern alle Prüfungen bestanden sind.')
    parser.add_argument('--install',action='store_true',help='Cron einrichten, keinen Auftrag sofort senden.')
    parser.add_argument('--disable',action='store_true',help='Pausieren und ausschließlich eigenen Cron entfernen.')
    args=parser.parse_args()
    if sum((args.tick,args.install,args.disable))>1:parser.error('Nur eine Aktion wählen.')
    os.umask(0o077);ROOT.mkdir(parents=True,exist_ok=True)
    with (ROOT/'lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return
        config=json.loads(CONFIG.read_text())
        if args.disable:
            config['enabled']=False;write_json(CONFIG,config);cron(config,remove=True)
        elif args.install:
            config['enabled']=True;write_json(CONFIG,config);cron(config)
        else:tick(config,send=args.tick)

if __name__=='__main__':
    try:main()
    except Exception as exc:
        print('FEHLER: '+str(exc),file=sys.stderr);sys.exit(1)
