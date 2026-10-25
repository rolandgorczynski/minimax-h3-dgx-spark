#!/usr/bin/python3 -I
"""Ollama-Modelle nach /home/jee/models/ollama kopieren. Startet keine Dienste."""
import argparse
import datetime
import fcntl
import grp
import json
import os
from pathlib import Path
import pwd
import shlex
import shutil
import signal
import stat
import subprocess
import sys

HOME=Path('/home/jee')
SOURCE=Path('/usr/share/ollama/.ollama/models')
TARGET=Path('/home/jee/models/ollama')
STATE=Path('/var/lib/ollama-model-move')
DROPIN=Path('/etc/systemd/system/ollama.service.d/zz-model-path.conf')
PROJECT=Path('/home/jee/docker/minimax-h3-dgx-spark')
BACKUP_CONFIGS=(PROJECT/'backup/docker-rsnapshot.json',Path('/etc/docker-rsnapshot.json'))


def log(text):
    print(datetime.datetime.now().astimezone().isoformat(timespec='seconds')+' '+text,flush=True)


def run(args, live=False):
    result=subprocess.run(args,text=True,check=False,**({} if live else {'capture_output':True}))
    if result.returncode:
        raise RuntimeError(f'{args[0]}: Exit {result.returncode}'+('' if live else '\n'+result.stderr[-1500:]))
    return '' if live else result.stdout


def atomic_text(path,text,mode=0o600):
    temporary=path.with_name(path.name+'.modellumzug-tmp')
    with temporary.open('w') as stream:
        stream.write(text);stream.flush();os.fsync(stream.fileno())
    temporary.chmod(mode);temporary.replace(path)
    fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)


def save(state):
    atomic_text(STATE/'status.json',json.dumps(state,ensure_ascii=False,indent=2)+'\n')


def properties():
    return dict(line.split('=',1) for line in run(['systemctl','show','ollama.service',
        '-p','User','-p','Group','-p','ActiveState','-p','UnitFileState','-p','ProtectHome',
        '-p','SupplementaryGroups','-p','ReadOnlyPaths','-p','InaccessiblePaths','-p','RootDirectory','-p','RootImage','-p','BindPaths','-p','BindReadOnlyPaths','-p','Environment']).splitlines() if '=' in line)


def environment(info):
    return dict(part.split('=',1) for part in shlex.split(info.get('Environment','')) if '=' in part)


def copy_args(check=False):
    # Die Zielbesitzer werden bewusst auf den tatsächlichen Dienstbenutzer vereinheitlicht.
    return ['rsync','-aHAX','--numeric-ids','--checksum','--delete','--chown=ollama:ollama',
            *(['--dry-run','--itemize-changes','--out-format=%i %n%L'] if check else ['--info=progress2,stats2']),
            str(SOURCE)+'/',str(TARGET)+'/']


def update_backup_config(path):
    data=json.loads(path.read_text())
    if not TARGET.is_relative_to(Path(data['home']).resolve()):
        raise RuntimeError('Backup-Home umfasst das neue Modellverzeichnis nicht: '+str(path))
    for key in ('additional_sources','optional_sources'):
        if key in data:data[key]=[p for p in data[key] if Path(p).resolve()!=SOURCE.resolve()]
    return json.dumps(data,ensure_ascii=False,indent=2)+'\n'


def backup_file(path,index):
    record=STATE/'originale'/str(index)
    record.mkdir(mode=0o700,parents=True,exist_ok=True)
    if (record/'pfad.json').exists():return
    if path.is_symlink():raise RuntimeError('Konfigurations-Symlink zuerst manuell prüfen: '+str(path))
    if path.exists():shutil.copy2(path,record/'inhalt')
    atomic_text(record/'pfad.json',json.dumps({'path':str(path),'existed':path.exists()})+'\n')


def preflight(resume):
    if os.geteuid()!=0:raise RuntimeError('Dieses Skript einmal mit sudo ausführen.')
    for tool in ('docker','rsync','systemctl','runuser','du'):
        if not shutil.which(tool):raise RuntimeError('Werkzeug fehlt: '+tool)
    if run(['docker','ps','-q']).strip():
        raise RuntimeError('Es laufen Docker-Container. Vorher ausdrücklich stoppen; dieses Skript startet oder stoppt keine Container.')
    if not SOURCE.is_dir() or SOURCE.is_symlink():raise RuntimeError('Ursprüngliches Modellverzeichnis fehlt oder ist ein Symlink.')
    if not TARGET.parent.is_dir() or TARGET.parent.is_symlink() or TARGET.is_symlink():
        raise RuntimeError('Modell-Elternverzeichnis fehlt oder Ziel ist ein Symlink.')
    if STATE.is_symlink() or DROPIN.is_symlink():raise RuntimeError('Unerwarteter Symlink am Status-/Konfigurationspfad.')
    account=pwd.getpwnam('ollama');group=grp.getgrnam('ollama');jee=pwd.getpwnam('jee')
    if group.gr_gid not in os.getgrouplist('jee',jee.pw_gid):
        raise RuntimeError('jee ist noch nicht Mitglied der Modellgruppe ollama; bitte zuerst gezielt einrichten.')
    home=HOME.stat()
    if home.st_gid!=grp.getgrnam('jee').gr_gid or not home.st_mode & 0o010:
        raise RuntimeError('Gruppe jee besitzt keinen Durchgang durch /home/jee. Keine Home-Rechte automatisch geändert.')
    info=properties()
    if info.get('User')!='ollama' or info.get('Group')!='ollama':
        raise RuntimeError('Unerwarteter Dienstbenutzer; erwartet ollama:ollama.')
    if info.get('ProtectHome') not in ('no','false'):
        raise RuntimeError('ProtectHome muss vor dem Umzug geprüft werden.')
    for setting in ('ReadOnlyPaths','InaccessiblePaths','RootDirectory','RootImage','BindPaths','BindReadOnlyPaths'):
        if info.get(setting):raise RuntimeError('Dienst-Einschränkung zuerst manuell prüfen: '+setting)
    if info.get('ActiveState') not in ('active','inactive','failed'):
        raise RuntimeError('Ollama befindet sich in einem Übergangszustand.')
    if info.get('UnitFileState') not in ('enabled','enabled-runtime','disabled','static'):
        raise RuntimeError('Autostart-Zustand zuerst manuell klären.')
    current=environment(info).get('OLLAMA_MODELS',str(SOURCE))
    if current not in (str(SOURCE),str(TARGET) if resume else str(SOURCE)):
        raise RuntimeError('Ein anderer Modellpfad ist konfiguriert; nicht automatisch überschrieben.')
    for config in BACKUP_CONFIGS:
        if config.exists():update_backup_config(config)
    if not resume and DROPIN.exists():raise RuntimeError('Der geplante neue Drop-in existiert bereits; zuerst manuell prüfen.')
    return info,account,group


def check_source_tree():
    for directory,dirs,files in os.walk(SOURCE,onerror=lambda error: (_ for _ in ()).throw(error)):
        for name in dirs+files:
            path=Path(directory)/name
            mode=path.lstat().st_mode
            if stat.S_ISLNK(mode):
                link=os.readlink(path)
                if os.path.isabs(link) or not path.resolve().is_relative_to(SOURCE.resolve()) or not path.exists():
                    raise RuntimeError('Absoluten, externen oder defekten Modell-Symlink zuerst klären: '+str(path))
            elif not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
                raise RuntimeError('Unerwartete Spezialdatei im Modellverzeichnis: '+str(path))


def migrate(resume=False):
    info,account,group=preflight(resume)
    os.umask(0o077)
    STATE.mkdir(mode=0o700,parents=True,exist_ok=True)
    with (STATE/'lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        journal=STATE/'status.json'
        if journal.exists():
            state=json.loads(journal.read_text())
            if state.get('phase')=='fertig':raise RuntimeError('Umzug bereits abgeschlossen. Keine Dienste gestartet.')
            if not resume:raise RuntimeError('Unterbrochener Lauf vorhanden. Status prüfen; zum Fortsetzen ausdrücklich --resume verwenden.')
            if state.get('source')!=str(SOURCE) or state.get('target')!=str(TARGET):
                raise RuntimeError('Status gehört zu anderen Pfaden.')
        else:
            if resume:raise RuntimeError('Kein unterbrochener Lauf zum Fortsetzen vorhanden.')
            if TARGET.exists() and next(TARGET.iterdir(),None) is not None:
                raise RuntimeError('Ziel ist nicht leer; nichts überschrieben.')
            state={'source':str(SOURCE),'target':str(TARGET),'phase':'vorbereitet',
                   'started':datetime.datetime.now().astimezone().isoformat(),
                   'original_active':info['ActiveState'],'original_autostart':info['UnitFileState'],
                   'original_environment':environment(info),'source_retained':True}
            save(state)
        try:
            state['phase']='stoppen';save(state)
            # Persistente Deaktivierung verhindert Autostart nach einem Stromausfall.
            if info['UnitFileState']=='enabled':run(['systemctl','disable','ollama.service'])
            elif info['UnitFileState']=='enabled-runtime':run(['systemctl','disable','--runtime','ollama.service'])
            run(['systemctl','stop','ollama.service'])
            if properties()['ActiveState'] not in ('inactive','failed'):
                raise RuntimeError('Ollama konnte nicht vollständig gestoppt werden.')
            log('Ollama gestoppt. Autostart bleibt bis zur bewussten Freigabe deaktiviert.')
            check_source_tree()
            size=int(run(['du','--summarize','--apparent-size','--block-size=1',str(SOURCE)]).split()[0])
            # Auch bei --resume konservativ eine weitere vollständige Kopie kalkulieren.
            required=int(size*1.05)+10*1024**3
            if shutil.disk_usage(TARGET.parent).free<required:
                raise RuntimeError('Zu wenig freier Speicher für vollständige Kopie plus Reserve.')
            TARGET.mkdir(mode=0o700,exist_ok=True)
            state['phase']='kopieren';save(state)
            log('Kopiere Modelle. Die Originaldateien bleiben erhalten.')
            run(copy_args(),live=True)
            state['phase']='pruefen';save(state)
            log('Prüfe vollständige Kopie mit erneutem Prüfsummen- und Metadatenvergleich.')
            differences=run(copy_args(check=True))
            if differences.strip():raise RuntimeError('Kopie weicht von Quelle ab:\n'+differences[:2000])
            os.chown(TARGET,account.pw_uid,group.gr_gid);TARGET.chmod(0o2770)
            # Derselbe Benutzer mit der geplanten zusätzlichen Dienstgruppe muss alles lesen können.
            probe='''import os, pathlib, tempfile
root=pathlib.Path('/home/jee/models/ollama')
count=0
for directory,dirs,files in os.walk(root, onerror=lambda error: (_ for _ in ()).throw(error)):
    if not os.access(directory,os.R_OK|os.W_OK|os.X_OK):
        raise SystemExit('Keine vollständigen Verzeichnisrechte: '+directory)
    for name in files:
        with open(os.path.join(directory,name),'rb') as stream:stream.read(1)
        count+=1
with tempfile.TemporaryFile(dir=root):pass
print('Dienstbenutzer-Zugriff geprüft: '+str(count)+' Dateien lesbar, Ziel beschreibbar.')
'''
            log(run(['runuser','--user','ollama','--group','ollama','--supp-group','jee','--',
                     '/usr/bin/python3','-I','-c',probe]).strip())
            if run(['docker','ps','-q']).strip():raise RuntimeError('Inzwischen laufen Docker-Container; vor Umschaltung erneut prüfen.')
            if properties()['ActiveState'] not in ('inactive','failed'):raise RuntimeError('Ollama wurde zwischenzeitlich gestartet.')
            state['phase']='konfigurieren';save(state)
            DROPIN.parent.mkdir(exist_ok=True)
            backup_file(DROPIN,0)
            atomic_text(DROPIN,'[Service]\nEnvironment="OLLAMA_MODELS=/home/jee/models/ollama"\nSupplementaryGroups=jee\nReadWritePaths=/home/jee/models/ollama\nUMask=0007\n',0o644)
            changed=[]
            for index,config in enumerate(BACKUP_CONFIGS,1):
                if config.exists():
                    text=update_backup_config(config);backup_file(config,index)
                    mode=config.stat().st_mode & 0o777
                    uid,gid=config.stat().st_uid,config.stat().st_gid
                    atomic_text(config,text,mode);os.chown(config,uid,gid);changed.append(str(config))
            run(['systemctl','daemon-reload'])
            effective=properties();env=environment(effective)
            if env.get('OLLAMA_MODELS')!=str(TARGET):raise RuntimeError('Neuer Modellpfad ist in systemd nicht wirksam.')
            for key,value in state['original_environment'].items():
                if key!='OLLAMA_MODELS' and env.get(key)!=value:
                    raise RuntimeError('Bestehende Dienst-Umgebung wurde unerwartet verändert: '+key)
            if 'jee' not in effective.get('SupplementaryGroups','').split():
                raise RuntimeError('Zusätzliche Dienstgruppe ist nicht wirksam.')
            if effective['ActiveState'] not in ('inactive','failed'):
                raise RuntimeError('Dienst läuft unerwartet. Kein erfolgreicher Abschluss.')
            if effective['UnitFileState'] not in ('disabled','static'):
                raise RuntimeError('Autostart ist noch aktiviert. Bitte vor Abschluss prüfen.')
            os.sync()
            state['phase']='fertig';state['finished']=datetime.datetime.now().astimezone().isoformat()
            state['backup_configs_updated']=changed;save(state)
            log('FERTIG: Modelle kopiert, geprüft und Konfiguration umgestellt.')
            log('Ollama bleibt gestoppt; Autostart bleibt deaktiviert. Keine Docker-Container gestartet.')
            log('Alte Modelle bleiben unter '+str(SOURCE)+'. Status: '+str(journal))
        except BaseException as error:
            state['failed_phase']=state['phase'];state['phase']='fehler';state['error']=str(error) or type(error).__name__;save(state)
            log('FEHLER: '+state['error'])
            log('Kein Neustart und keine Löschung der alten Modelle. Status prüfen: '+str(journal))
            raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--resume',action='store_true',help='Unterbrochenen, zuvor geprüften Umzug ausdrücklich fortsetzen.')
    args=parser.parse_args()
    signal.signal(signal.SIGTERM,lambda *_: (_ for _ in ()).throw(KeyboardInterrupt('SIGTERM')))
    try:migrate(args.resume)
    except (Exception,KeyboardInterrupt) as error:
        log('ABGEBROCHEN: '+(str(error) or type(error).__name__));sys.exit(1)
