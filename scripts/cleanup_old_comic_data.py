#!/usr/bin/python3 -I
"""Alte Modell-/Volume-Kopien nach bestätigter Sicherung manuell bereinigen."""
import argparse
import datetime
import fcntl
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

CONFIG=Path('/etc/docker-rsnapshot.json')
OLD_MODELS=Path('/usr/share/ollama/.ollama/models')
NEW_MODELS=Path('/home/jee/models/ollama')
MIGRATION=Path('/var/lib/ollama-model-move/status.json')
VOLUMES={'comic-automation_comic-automation-data':('/home/jee/docker-data/comic-automation','/data','comic-automation-comic-automation-1'),
         'linux-open-source-games_updater_state':('/home/jee/docker-data/games-updater','/state','linux-open-source-games-updater-1')}
OLD_RULE=Path('/etc/sudoers.d/comic-backup-ollama')
OLD_HELPER=Path('/usr/local/sbin/comic-backup-ollama')


def command(args):
    return subprocess.check_output(args,text=True)


def prerequisites(settings,containers,volumes):
    root=Path(settings['state_root']);status=json.loads((root/'status.json').read_text())
    if status.get('phase')!='fertig' or not status.get('verified'):
        raise RuntimeError('Kein bestätigter erfolgreicher Backup-Lauf. Keine Löschung.')
    mount=json.loads(command(['findmnt','--json','--target',settings['backup_mount'],'--output','TARGET,UUID']))['filesystems'][0]
    if mount['target']!=settings['backup_mount'] or mount.get('uuid')!=settings['backup_uuid']:
        raise RuntimeError('Erwartetes Backup-Laufwerk fehlt.')
    snapshot=Path(settings['snapshot_root'])/'weekly.0'
    if not snapshot.is_dir() or snapshot.is_symlink():raise RuntimeError('Erfolgreicher Wochenstand fehlt.')
    original=snapshot/'localhost'/str(root).lstrip('/')/'export'/'dienstzustand.json'
    saved=json.loads(original.read_text())
    if saved.get('started')!=status.get('started'):raise RuntimeError('Backup-Journal passt nicht zum Snapshot.')
    migration=json.loads(MIGRATION.read_text())
    if migration.get('phase')!='fertig' or migration.get('source')!=str(OLD_MODELS) or migration.get('target')!=str(NEW_MODELS):
        raise RuntimeError('Modellumzug ist nicht erfolgreich dokumentiert.')
    if datetime.datetime.fromisoformat(status['started'])<datetime.datetime.fromisoformat(migration['finished']):
        raise RuntimeError('Die Sicherung ist älter als der Modellumzug.')
    for path in [NEW_MODELS,*[Path(v[0]) for v in VOLUMES.values()]]:
        if not path.is_dir() or path.is_symlink():raise RuntimeError('Neues Datenverzeichnis fehlt: '+str(path))
        copied=snapshot/'localhost'/str(path).lstrip('/')
        if not copied.is_dir() or copied.is_symlink():raise RuntimeError('Neuer Datenpfad ist nicht im Snapshot: '+str(path))
        if not any(path.is_relative_to(Path(p)) for p in saved['sources']):
            raise RuntimeError('Neuer Datenpfad war keine erfasste Sicherungsquelle: '+str(path))
    active=command(['systemctl','show','ollama','-p','ActiveState','--value']).strip()
    if active not in ('inactive','failed'):raise RuntimeError('Ollama muss für diese Bereinigung bereits gestoppt sein.')
    values=shlex.split(command(['systemctl','show','ollama','-p','Environment','--value']))
    env=dict(s.split('=',1) for s in values if '=' in s)
    if env.get('OLLAMA_MODELS')!=str(NEW_MODELS):raise RuntimeError('Ollama verwendet laut Konfiguration nicht den neuen Modellpfad.')
    for c in containers:
        for mount in c['Mounts']:
            source=mount.get('Source')
            if source and (Path(source).is_relative_to(OLD_MODELS) or OLD_MODELS.is_relative_to(Path(source))):
                raise RuntimeError('Alter Modellpfad wird noch von einem Container eingebunden: '+c['Name'])
    # Auch verschachtelte Mounts nicht versehentlich rekursiv löschen.
    for line in Path('/proc/self/mountinfo').read_text().splitlines():
        mountpoint=Path(line.split()[4].replace('\\040',' '))
        if mountpoint.is_relative_to(OLD_MODELS):
            raise RuntimeError('Mount am alten Modellpfad zuerst manuell klären: '+str(mountpoint))
    names={c['Name'].lstrip('/'):c for c in containers}
    for name,(new,destination,container_name) in VOLUMES.items():
        for c in containers:
            if any(m.get('Name')==name or m.get('Source','').startswith('/var/lib/docker/volumes/'+name+'/') for m in c['Mounts']):
                raise RuntimeError('Altes Volume wird noch referenziert: '+name+' durch '+c['Name'])
        if container_name not in names:raise RuntimeError('Umgestellter Container fehlt: '+container_name)
        c=names[container_name]
        if c['State']['Running']:raise RuntimeError('Betroffener Container muss bereits gestoppt sein: '+container_name)
        if not any(m['Type']=='bind' and m['Destination']==destination and m['Source']==new for m in c['Mounts']):
            raise RuntimeError('Neuer Bind-Mount ist nicht eingerichtet: '+container_name)
        for info in volumes:
            if info['Name']==name and (info['Driver']!='local' or info.get('Options')):
                raise RuntimeError('Unerwarteter Volume-Typ: '+name)
    if OLD_MODELS.exists() and (OLD_MODELS.is_symlink() or OLD_MODELS.resolve()!=OLD_MODELS):
        raise RuntimeError('Unerwarteter Symlink am alten Modellpfad.')


def remove_old_helper(root):
    expected='jee ALL=(root) NOPASSWD: /usr/local/sbin/comic-backup-ollama ""'
    if OLD_RULE.is_symlink() or OLD_HELPER.is_symlink():
        print('Alten sudo-Helfer wegen Symlink nicht entfernt; manuell prüfen.');return
    if OLD_RULE.exists() and OLD_RULE.read_text().strip()!=expected:
        print('Veränderte alte sudo-Regel nicht entfernt; manuell prüfen.');return
    if OLD_HELPER.exists() and ('Ausschließlich Ollama-Modelle als Archiv nach stdout lesen.' not in OLD_HELPER.read_text()):
        print('Veränderten alten sudo-Helfer nicht entfernt; manuell prüfen.');return
    previous=root/'alte-sudo-regel';previous.mkdir(mode=0o700,exist_ok=True)
    for path in (OLD_RULE,OLD_HELPER):
        if path.exists():shutil.copy2(path,previous/path.name);path.unlink();print('Entfernt: '+str(path))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group()
    group.add_argument('--delete',action='store_true',help='Die ausdrücklich aufgeführten alten Kopien endgültig entfernen.')
    group.add_argument('--plan',action='store_true',help='Nur prüfen und anzeigen (Standard).')
    args=parser.parse_args()
    if os.geteuid()!=0:raise RuntimeError('Bitte mit sudo ausführen.')
    os.umask(0o077)
    settings=json.loads(CONFIG.read_text());root=Path(settings['state_root'])
    with (root/'lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        ids=command(['docker','ps','-aq']).split()
        containers=json.loads(command(['docker','inspect',*ids])) if ids else []
        volume_names=set(command(['docker','volume','ls','--format','{{.Name}}']).splitlines())
        selected=sorted(volume_names.intersection(VOLUMES))
        volumes=json.loads(command(['docker','volume','inspect',*selected])) if selected else []
        prerequisites(settings,containers,volumes)
        print('Zur Bereinigung vorgesehen:')
        for name in selected:print('  Docker-Volume: '+name)
        if OLD_MODELS.exists():print('  Alte Modelle: '+str(OLD_MODELS))
        for path in (OLD_RULE,OLD_HELPER):
            if path.exists():print('  Überholter sudo-Helfer: '+str(path))
        print('Bleiben erhalten: neue Daten, sämtliche rsnapshot-Stände, DATA, Logs, Konfigurationskopien und Docker-Exportcache.')
        if not args.delete:
            print('Nur Planung. Nichts gelöscht und keine Dienste gestartet. Zum Löschen ausdrücklich --delete verwenden.');return
        report={'started':datetime.datetime.now().astimezone().isoformat(),'phase':'bereinigen','removed':[]}
        status=root/'bereinigung.json'
        def save():
            tmp=status.with_name(status.name+'.tmp')
            with tmp.open('w') as stream:
                json.dump(report,stream,ensure_ascii=False,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
            tmp.replace(status)
        save()
        try:
            for name in selected:
                subprocess.run(['docker','volume','rm',name],check=True)  # Kein --force, kein prune.
                report['removed'].append('volume:'+name);save()
            if OLD_MODELS.exists():
                shutil.rmtree(OLD_MODELS)
                report['removed'].append(str(OLD_MODELS));save()
            remove_old_helper(root)
            os.sync();report['phase']='fertig';save()
            print('FERTIG: Alte Kopien bereinigt. Keine Dienste gestartet.')
        except BaseException as error:
            report.update(phase='fehler',error=str(error) or type(error).__name__);save();raise


if __name__=='__main__':
    try:main()
    except (Exception,KeyboardInterrupt) as error:
        print('ANGEHALTEN: '+(str(error) or type(error).__name__),file=sys.stderr);sys.exit(1)
