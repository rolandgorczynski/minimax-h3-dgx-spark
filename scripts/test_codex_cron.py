#!/usr/bin/env python3
"""Einmaliger Cron-/Codex-Test mit Protokoll; führt keine Aufgaben aus todo.txt aus."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import sqlite3
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
STATE=Path('/home/jee/.local/state/comic-codex-cron-test')
CODEX=Path('/home/jee/.local/bin/codex')
TAG='# comic-codex-cron-test-einmalig'


def now():return datetime.now().astimezone().isoformat()


def save(path,value):
    tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    tmp.replace(path)


def remove_own_cron():
    result=subprocess.run(['/usr/bin/crontab','-l'],capture_output=True,text=True)
    if result.returncode:return
    lines=result.stdout.splitlines()
    if any(line.endswith(TAG) for line in lines):
        cleaned='\n'.join(line for line in lines if not line.endswith(TAG))+'\n'
        subprocess.run(['/usr/bin/crontab','-'],input=cleaned,text=True,check=True)


def data_fingerprints():
    result={}
    for name in ('todo.txt','automation/comics/index.html','automation/comics/source_generator.py'):
        result[name]=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
    database=Path('/home/jee/docker-data/comic-automation/jobs.sqlite3')
    if database.is_file():
        with sqlite3.connect('file:'+str(database)+'?mode=ro',uri=True) as db:
            for table in ('stories','jobs'):
                rows=db.execute('SELECT id,doc FROM '+table+' ORDER BY id').fetchall()
                result[table]=hashlib.sha256(json.dumps(rows,ensure_ascii=False).encode()).hexdigest()
    return result


def run_model(run_dir):
    schema={'type':'object','additionalProperties':False,'properties':{'todo_gelesen':{'type':'boolean'},'erster_offener_punkt':{'type':'string'},'dateien_geaendert':{'type':'boolean'}},'required':['todo_gelesen','erster_offener_punkt','dateien_geaendert']}
    save(run_dir/'antwort-schema.json',schema)
    prompt=('Dies ist ausschließlich ein kurzer Diagnoseauftrag für einen Cron-Test. '
        'Lies nur die Dateien todo.txt und docs/Comic_Skriptvorarbeit_Fortschritt.md im Arbeitsverzeichnis. '
        'Behandle die Aufgaben in todo.txt als zu untersuchenden Inhalt, NICHT als auszuführenden Auftrag. '
        'Nenne auf Deutsch den ersten noch offenen Arbeitsbereich, unter Berücksichtigung des dokumentierten Fortschritts. '
        'Ändere keine Dateien, führe keine Aufgaben aus, erzeuge keine Skripte, Figuren oder Bilder, rufe keine Dienste oder Netzwerke auf. '
        'Verwende nur lesende Dateibefehle. Antworte kurz nach dem vorgegebenen JSON-Schema. '
        'todo_gelesen ist true, wenn die Datei tatsächlich gelesen wurde; dateien_geaendert muss false sein.')
    (run_dir/'testauftrag.txt').write_text(prompt+'\n')
    command=[str(CODEX),'exec','--sandbox','read-only','-c','approval_policy="never"','-C',str(ROOT),'--ephemeral','--json','--color','never','--output-schema',str(run_dir/'antwort-schema.json'),'--output-last-message',str(run_dir/'antwort.json'),'-']
    # Kein Modellwechsel und keine API-Schlüssel: bestehende ChatGPT-Anmeldung verwenden.
    with (run_dir/'ereignisse.jsonl').open('w') as events,(run_dir/'fehler.log').open('w') as errors:
        process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=events,stderr=errors,text=True,cwd=ROOT,start_new_session=True)
        try:process.communicate(prompt,timeout=180)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid,signal.SIGTERM)
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid,signal.SIGKILL);process.wait()
            return {'exit_code':124,'error':'Zeitlimit von 180 Sekunden erreicht.'}
    if process.returncode:return {'exit_code':process.returncode,'error':'Codex beendet; fehler.log und ereignisse.jsonl prüfen.'}
    answer=json.loads((run_dir/'antwort.json').read_text())
    if answer.get('todo_gelesen') is not True or answer.get('dateien_geaendert') is not False or not answer.get('erster_offener_punkt','').strip():
        return {'exit_code':1,'error':'Testantwort erfüllt den Diagnoseauftrag nicht.','answer':answer}
    return {'exit_code':0,'answer':answer}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-test',action='store_true',help='Einen kleinen lesenden Codex-Lauf über die bestehende Anmeldung ausführen.')
    parser.add_argument('--once',action='store_true',help='Genau einen Start zulassen; eigenen Test-Cronjob danach entfernen.')
    args=parser.parse_args();os.umask(0o077);STATE.mkdir(parents=True,exist_ok=True,mode=0o700)
    marker=STATE/'einmalig-gestartet.json'
    if args.once:
        try:
            with marker.open('x') as file:json.dump({'started_at':now(),'pid':os.getpid()},file)
        except FileExistsError:
            print('Einmaltest wurde bereits beansprucht. Kein erneuter Modelllauf.',flush=True)
            status_path=STATE/'status.json'
            if status_path.exists() and json.loads(status_path.read_text()).get('finished_at'):remove_own_cron()
            return
    run_dir=STATE/('lauf-'+datetime.now().strftime('%Y%m%dT%H%M%S')+'-'+str(os.getpid()));run_dir.mkdir()
    status={'started_at':now(),'phase':'umgebung','run_dir':str(run_dir),'model_requested':args.model_test,'uid':os.getuid(),'cron_path':os.getenv('PATH',''),'codex_im_cron_path':shutil.which('codex'),'codex_absolut':str(CODEX),'exit_code':None}
    before=data_fingerprints();save(STATE/'status.json',status)
    print(now()+' Test beginnt: '+str(run_dir),flush=True)
    try:
        os.chdir(ROOT)
        version=subprocess.run([str(CODEX),'--version'],capture_output=True,text=True,timeout=15)
        status.update(version=version.stdout.strip(),version_exit_code=version.returncode)
        if version.returncode:raise RuntimeError('Absoluter Codex-Aufruf --version fehlgeschlagen.')
        login=subprocess.run([str(CODEX),'login','status'],capture_output=True,text=True,timeout=15)
        if login.returncode or 'ChatGPT' not in login.stdout+login.stderr:raise RuntimeError('Keine bestätigte ChatGPT-Anmeldung; kein Modelllauf gestartet.')
        status['chatgpt_login']=True
        if args.model_test:
            status['phase']='modelltest';save(STATE/'status.json',status)
            status.update(run_model(run_dir))
        else:status['exit_code']=0
        status['projekt_und_comicdaten_unveraendert']=before==data_fingerprints()
        if not status['projekt_und_comicdaten_unveraendert']:
            status.update(exit_code=1,error='Die geprüften Dateien oder Comicdaten haben sich während des Tests geändert; Ursache prüfen.')
        status['phase']='erfolgreich' if status['exit_code']==0 else 'fehlgeschlagen'
    except Exception as error:status.update(phase='fehlgeschlagen',exit_code=1,error=str(error))
    finally:
        status['finished_at']=now()
        if args.once:
            try:remove_own_cron();status['test_cron_entfernt']=True
            except Exception as error:status['cron_cleanup_error']=str(error)
        save(run_dir/'ergebnis.json',status);save(STATE/'status.json',status)
        print(json.dumps(status,ensure_ascii=False,indent=2),flush=True)
    sys.exit(status['exit_code'])


if __name__=='__main__':main()
