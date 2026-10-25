#!/usr/bin/python3 -I
"""Docker-Projekte offline mit rsnapshot sichern. Ohne Aktionsoption nur lesende Planung."""
import argparse
import datetime
import fcntl
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import signal
import subprocess
import sys


VOLATILE_CHECK_FILES=(Path('/etc/cups/subscriptions.conf'),Path('/etc/cups/subscriptions.conf.O'))
VOLATILE_CHECK_DIR_TIMES=(Path('/etc/cups'),)

def log(message):
    print(datetime.datetime.now().astimezone().isoformat(timespec='seconds')+' '+message, flush=True)


def command(args, **kwargs):
    result = subprocess.run(args, check=False, text=True, capture_output=True, **kwargs)
    if result.returncode:
        # Keine Docker-Umgebungsvariablen oder Zugangsdaten ausgeben.
        raise RuntimeError(f'{args[0]} {args[1] if len(args)>1 else ""}: Exit {result.returncode}; '+result.stderr[-1200:])
    return result.stdout


def atomic_json(path, value):
    tmp = path.with_name(path.name+'.tmp')
    with tmp.open('w') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    tmp.replace(path)
    sync_dir(path.parent)


def sync_dir(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)


def under(path, root):
    return Path(path).resolve().is_relative_to(Path(root).resolve())


def inspect_containers():
    ids=command(['docker','ps','-aq']).split()
    return json.loads(command(['docker','inspect',*ids])) if ids else []


def selected(container, root):
    labels=container['Config'].get('Labels') or {}
    working=labels.get('com.docker.compose.project.working_dir')
    files=labels.get('com.docker.compose.project.config_files','').split(',')
    return bool((working and under(working,root)) or any(p and under(p,root) for p in files))


def mount_check(settings):
    data=json.loads(command(['findmnt','--json','--target',settings['backup_mount'],'--output','TARGET,UUID,FSTYPE']))['filesystems'][0]
    if Path(data['target']) != Path(settings['backup_mount']) or data.get('uuid') != settings['backup_uuid']:
        raise RuntimeError('Backup-Laufwerk fehlt oder UUID stimmt nicht. Keine Dienste gestoppt.')
    if not under(settings['snapshot_root'], settings['backup_mount']) or Path(settings['snapshot_root']) == Path(settings['backup_mount']):
        raise RuntimeError('Snapshot-Verzeichnis muss unterhalb des Backup-Mounts liegen.')


def source_paths(settings, containers):
    sources={Path(settings['home']).resolve(), *[Path(p).resolve() for p in settings['additional_sources']]}
    sources.update(Path(p).resolve() for p in settings.get('optional_sources',[]) if Path(p).exists())
    for c in containers:
        for m in c['Mounts']:
            if m['Type'] not in ('bind','volume'):
                if m['Type'] == 'tmpfs': continue
                raise RuntimeError('Nicht unterstützter Mount-Typ: '+m['Type'])
            source=Path(m['Source']).resolve()
            # System-Sockets sind keine persistenten Anwendungsdaten.
            if source in (Path('/var/run/docker.sock').resolve(),Path('/run/docker.sock')): continue
            if m['Type']=='volume':
                name=m.get('Name')
                v=json.loads(command(['docker','volume','inspect',name]))[0]
                if v['Driver']!='local' or v.get('Options'):
                    raise RuntimeError('Volume benötigt eigene Sicherungsstrategie: '+name)
            sources.add(source)
    for p in sources:
        if not p.exists(): raise RuntimeError('Quellpfad fehlt: '+str(p))
        if str(p)=='/' or under(p,settings['backup_mount']) or under(settings['backup_mount'],p):
            raise RuntimeError('Unzulässige/rekursive Quelle: '+str(p))
        if any(ch.isspace() for ch in str(p)):
            raise RuntimeError('Quellpfad mit Leerraum benötigt explizite Konfiguration: '+str(p))
    return sorted((p for p in sources if not any(p!=q and p.is_relative_to(q) for q in sources)),key=str)


def plan(settings):
    mount_check(settings)
    all_containers=inspect_containers()
    targets=[c for c in all_containers if selected(c,settings['project_root'])]
    if not targets: raise RuntimeError('Keine passenden Compose-Container gefunden.')
    if any(c['State'].get('Paused') or c['State'].get('Restarting') for c in targets):
        raise RuntimeError('Pausierte/neustartende Container zuerst manuell klären.')
    sources=source_paths(settings,targets)
    for other in all_containers:
        if other in targets or not other['State']['Running']: continue
        for m in other['Mounts']:
            if m.get('RW') and m.get('Source') and any(under(m['Source'],p) or under(p,m['Source']) for p in sources):
                raise RuntimeError('Weiterer laufender Container schreibt in Sicherungsquellen: '+other['Name'])
    services=[]
    for name in settings['host_services']:
        info=dict(line.split('=',1) for line in command(['systemctl','show',name,'-p','LoadState','-p','ActiveState','-p','UnitFileState']).splitlines() if '=' in line)
        if info.get('LoadState')!='loaded': raise RuntimeError('Host-Dienst fehlt: '+name)
        if info.get('ActiveState') not in ('active','inactive','failed'):
            raise RuntimeError('Host-Dienst in Übergangszustand: '+name)
        if info.get('UnitFileState') not in ('enabled','disabled','static','masked','enabled-runtime'):
            raise RuntimeError('Nicht unterstützter Autostart-Zustand: '+name)
        services.append({'name':name,'active':info['ActiveState']=='active','enabled':info['UnitFileState']})
    return targets,sources,services


def container_state(c):
    return {'id':c['Id'],'name':c['Name'].lstrip('/'),'running':c['State']['Running'],
            'restart_policy':c['HostConfig']['RestartPolicy']}


def policy_arg(policy):
    name=policy.get('Name') or 'no'
    return name+(':'+str(policy['MaximumRetryCount']) if name=='on-failure' and policy.get('MaximumRetryCount') else '')


def stopped(state):
    for c in state['containers']:
        current=json.loads(command(['docker','inspect',c['id']]))[0]
        if current['State']['Running']: raise RuntimeError('Container läuft weiterhin: '+c['name'])
    for service in state['services']:
        status=command(['systemctl','show',service['name'],'-p','ActiveState','--value']).strip()
        if status not in ('inactive','failed'): raise RuntimeError('Host-Dienst läuft weiterhin: '+service['name'])


def stop_services(state, persist):
    state['phase']='stoppen'; persist()
    # Vor dem Stoppen persistent festhalten; bei Stromausfall kein Docker-Autostart.
    for c in state['containers']:
        command(['docker','update','--restart=no',c['id']])
    for s in state['services']:
        if s['enabled']=='enabled': command(['systemctl','disable',s['name']])
        if s['enabled']=='enabled-runtime': command(['systemctl','disable','--runtime',s['name']])
    running=[c['id'] for c in state['containers'] if c['running']]
    if running: command(['docker','stop','--time','120',*running])
    for s in state['services']:
        if s['active']: command(['systemctl','stop',s['name']])
    stopped(state)
    state['phase']='gestoppt'; persist()


def restart_services(state, persist):
    if not state.get('verified'): raise RuntimeError('Ohne erfolgreiche Prüfung kein Neustart.')
    state['phase']='starten'; persist()
    for s in state['services']:
        if s['enabled']=='enabled': command(['systemctl','enable',s['name']])
        if s['enabled']=='enabled-runtime': command(['systemctl','enable','--runtime',s['name']])
        if s['active']:
            command(['systemctl','start',s['name']])
            if command(['systemctl','show',s['name'],'-p','ActiveState','--value']).strip()!='active':
                raise RuntimeError('Host-Dienst nicht aktiv: '+s['name'])
    for c in state['containers']:
        command(['docker','update','--restart='+policy_arg(c['restart_policy']),c['id']])
    for c in reversed(state['containers']):
        if c['running']: command(['docker','start',c['id']])
    for c in state['containers']:
        current=json.loads(command(['docker','inspect',c['id']]))[0]
        if current['State']['Running']!=c['running']:
            raise RuntimeError('Dienstzustand stimmt nach Neustart nicht: '+c['name'])
    state['phase']='fertig'; persist()


def export_images(targets, export):
    images=export/'images'; images.mkdir(exist_ok=True)
    for image in sorted({c['Image'] for c in targets}):
        dest=images/(image.replace(':','-')+'.tar')
        sidecar=dest.with_suffix('.sha256')
        if dest.exists() and sidecar.exists(): continue
        tmp=dest.with_suffix('.partial')
        log('Docker-Abbild exportieren: '+image[:24])
        command(['docker','image','save','--output',str(tmp),image])
        with tmp.open('rb') as stream:
            digest=hashlib.file_digest(stream,'sha256').hexdigest(); os.fsync(stream.fileno())
        tmp.replace(dest)
        sidecar.write_text(digest+'  '+dest.name+'\n')
        sync_dir(images)
    # Nur verwendete Abbilddateien spiegeln; ältere Versionen bleiben in Snapshots.
    used={c['Image'].replace(':','-') for c in targets}
    for p in images.iterdir():
        if p.stem not in used: p.unlink()


def export_rootfs(targets, export):
    """Container-Schreibschichten mitnehmen; Volumes werden separat gesichert."""
    directory=export/'container-rootfs'; directory.mkdir(exist_ok=True)
    used=set()
    for c in targets:
        name=c['Id']; used.add(name)
        dest=directory/(name+'.tar'); tmp=directory/(name+'.partial')
        sidecar=directory/(name+'.sha256')
        log('Container-Dateisystem exportieren: '+c['Name'].lstrip('/'))
        command(['docker','export','--output',str(tmp),c['Id']])
        with tmp.open('rb') as stream:
            digest=hashlib.file_digest(stream,'sha256').hexdigest(); os.fsync(stream.fileno())
        if dest.exists() and sidecar.exists() and sidecar.read_text().split()[0]==digest:
            # Unveränderte Archive behalten ihren Zeitstempel für rsnapshot-Hardlinks.
            tmp.unlink()
        else:
            tmp.replace(dest)
            sidecar.write_text(digest+'  '+dest.name+'\n')
        sync_dir(directory)
    for path in directory.iterdir():
        if path.stem not in used: path.unlink()


def config_text(base,sources,snapshot_root):
    # Keine versteckten Hooks/zusätzlichen Quellen aus einer anderen Konfiguration.
    forbidden={'backup','backup_script','cmd_preexec','cmd_postexec','include_conf','include_conf_dir','exclude','exclude_file','include','include_file'}
    for line in base.splitlines():
        if line.strip() and not line.lstrip().startswith('#') and line.split()[0] in forbidden:
            raise RuntimeError('Nicht unterstützte Basis-Konfiguration: '+line.split()[0])
    if 'snapshot_root\t'+str(snapshot_root).rstrip('/')+'/' not in base:
        raise RuntimeError('snapshot_root in Einstellungen und rsnapshot-Konfiguration verschieden.')
    # Die vollständige Inhaltsprüfung ist ausschließlich ein separater manueller Job.
    lines=[]
    for line in base.splitlines():
        fields=line.split()
        if fields and fields[0]=='rsync_long_args':
            line='rsync_long_args\t'+' '.join(a for a in fields[1:] if a not in ('--checksum','-c'))
        if fields and fields[0]=='rsync_short_args':
            line='rsync_short_args\t'+' '.join(a.replace('c','') if a.startswith('-') and not a.startswith('--') else a for a in fields[1:])
        lines.append(line)
    return '\n'.join(lines)+'\n'+''.join('backup\t'+str(p)+('/' if p.is_dir() else '')+'\tlocalhost/\n' for p in sources)


def verification_ignores(settings):
    home=Path(settings.get('home','/home/jee'))
    # Nur die Abschlussprüfung: Diese Daten werden weiterhin vollständig kopiert.
    return [home/'.codex',home/'.cache/google-chrome',home/'.cache/chromium',
            home/'.cache/mozilla',home/'.cache/BraveSoftware',
            home/'.config/google-chrome/BrowserMetrics',home/'.config/chromium/BrowserMetrics']


def essential_differences(text):
    differences=[]
    for line in text.splitlines():
        fields=line.split(None,1)
        if len(fields)==2 and fields[0]=='.d..t......':
            path=Path('/'+fields[1].lstrip('/').rstrip('/'))
            if path in VOLATILE_CHECK_DIR_TIMES:
                log('Hinweis: veränderlicher Verzeichniszeitstempel wird nicht als Fehler bewertet: '+str(path))
                continue
        if line.strip():differences.append(line)
    return '\n'.join(differences)


def verify(sources,dest,checksums=True,ignore_paths=()):
    for source in sources:
        log(('Prüfsummenvergleich: ' if checksums else 'Größe, Zeitstempel und Metadaten prüfen: ')+str(source))
        ignored=[Path(p) for p in ignore_paths if Path(p).is_relative_to(source)]
        files=[p for p in VOLATILE_CHECK_FILES if p.is_relative_to(source)]
        filters=['--exclude=/'+str(p).lstrip('/')+'/***' for p in ignored]
        filters+=['--exclude=/'+str(p).lstrip('/') for p in files]
        for path in files:log('Hinweis: veränderliche Dienstdatei wird mitgesichert, aber nicht streng geprüft: '+str(path))
        for path in ignored:log('Hinweis: laufend veränderliche Daten werden mitgesichert, aber nicht streng geprüft: '+str(path))
        # --delete-excluded würde im Dry-Run die absichtlich ignorierten Kopien
        # als Löschung ausgeben. Standardmäßig schützt rsync diese Dateien.
        # --relative führt auch Elternverzeichnisse mit. Deren Metadaten sind
        # außerhalb des gewählten Quellbaums (z.B. Journal neben export).
        result=command(['rsync','-aHAXnci' if checksums else '-aHAXni','--numeric-ids','--relative','--no-implied-dirs','--delete',
                        *filters,'--out-format=%i %n%L',str(source)+('/' if source.is_dir() else ''),str(dest)+'/'])
        result=essential_differences(result)
        if result.strip():
            raise RuntimeError('Sicherung weicht von Quelle ab: '+str(source)+'\n'+result[:2000])


def space_check(settings,sources,targets,snapshot):
    free=shutil.disk_usage(snapshot).free
    minimum=settings['reserve_bytes']
    if not (snapshot/'.sync').exists() and not any(snapshot.glob('weekly.*')):
        # Beim ersten Lauf werden Quellen plus lokale Export-Stufe plus deren Kopie benötigt.
        total=command(['du','--summarize','--total','--apparent-size','--block-size=1','--',*map(str,sources)])
        source_bytes=int(total.splitlines()[-1].split()[0])
        image_ids=sorted({c['Image'] for c in targets})
        images=json.loads(command(['docker','image','inspect',*image_ids]))
        image_sizes={i['Id']:i['Size'] for i in images}
        sized=json.loads(command(['docker','inspect','--size',*[c['Id'] for c in targets]]))
        rootfs=sum(c.get('SizeRootFs',image_sizes[c['Image']])+c.get('SizeRw',0) for c in sized)
        exports=sum(image_sizes.values())+rootfs
        minimum+=int((source_bytes+2*exports)*1.10)
        # Auch die lokale Export-Stufe muss auf dem Host-Dateisystem Platz haben.
        if shutil.disk_usage(settings['state_root']).free < exports+settings['reserve_bytes']:
            raise RuntimeError('Zu wenig freier Platz auf dem Host für Docker-Exporte.')
    log('Freier Backup-Platz: %.1f GiB; Mindestbedarf: %.1f GiB'%(free/1024**3,minimum/1024**3))
    if free < minimum:
        raise RuntimeError('Freier Backup-Platz unterschreitet Mindestbedarf. Keine Dienste gestoppt.')


def run(settings,resume=False):
    if os.geteuid()!=0: raise RuntimeError('--run erfordert root.')
    os.umask(0o077)
    root=Path(settings['state_root']); root.mkdir(mode=0o700,parents=True,exist_ok=True)
    with (root/'lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        journal=root/'status.json'
        previous=None
        if journal.exists():
            recorded=json.loads(journal.read_text())
            if recorded.get('phase')!='fertig':
                if not resume:
                    raise RuntimeError('Voriger Lauf unvollständig. status.json und Dienste manuell prüfen; kein automatischer Wiederanlauf.')
                if (recorded.get('phase')!='fehler' or recorded.get('failed_phase')!='pruefen'
                        or not recorded.get('error','').startswith('Sicherung weicht von Quelle ab:')):
                    raise RuntimeError('Nur einen gescheiterten Quellenvergleich ausdrücklich mit --resume fortsetzen; andere Fehler zuerst klären.')
                previous=recorded
        if resume and previous is None:
            raise RuntimeError('Kein passender fehlgeschlagener Quellenvergleich zum Fortsetzen vorhanden.')
        targets,sources,services=plan(settings)
        snapshot=Path(settings['snapshot_root']); snapshot.mkdir(mode=0o700,exist_ok=True)
        space_check(settings,sources,targets,snapshot)
        export=root/'export'; export.mkdir(mode=0o700,exist_ok=True)
        sources.append(export)
        cfg=root/'rsnapshot.conf'
        cfg.write_text(config_text(Path(settings['base_config']).read_text(),sources,snapshot))
        command(['rsnapshot','-c',str(cfg),'configtest'])
        state={'started':datetime.datetime.now().astimezone().isoformat(),'phase':'vorbereitet','verified':False,'verification':'metadata','checksums_verified':False,
               'containers':[container_state(c) for c in targets],'services':services,'sources':list(map(str,sources)),
               'verification_ignored_paths':list(map(str,verification_ignores(settings))),
               'verification_ignored_files':list(map(str,VOLATILE_CHECK_FILES)),
               'verification_ignored_directory_timestamps':list(map(str,VOLATILE_CHECK_DIR_TIMES))}
        persist=lambda: atomic_json(journal,state)
        if previous is not None:
            history=root/'fehlerhistorie';history.mkdir(mode=0o700,exist_ok=True)
            stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            atomic_json(history/(stamp+'.json'),previous)
            state['resumes_from']=previous.get('started')
            log('Fehlerstatus aufbewahrt. Vorhandenen rsnapshot-Arbeitsstand inkrementell aktualisieren und neu prüfen.')
            # Vor dem Fehler deaktivierte Autostarts wieder mit dem ursprünglichen
            # Sollwert führen; gestartet werden nur jetzt bereits laufende Dienste.
            policies={c['id']:c['restart_policy'] for c in previous.get('containers',[])}
            for c in state['containers']:
                if c['id'] in policies:c['restart_policy']=policies[c['id']]
            enabled={v['name']:v['enabled'] for v in previous.get('services',[])}
            for service in state['services']:
                if service['name'] in enabled:service['enabled']=enabled[service['name']]
        persist()
        try:
            stop_services(state,persist)
            state['phase']='exportieren'; persist()
            atomic_json(export/'containers.json',targets)
            atomic_json(export/'einstellungen.json',settings)
            (export/'rsnapshot-basis.conf').write_text(Path(settings['base_config']).read_text())
            shutil.copyfile(Path(__file__),export/'docker_rsnapshot_weekly.py')
            volumes={m['Name'] for c in targets for m in c['Mounts'] if m['Type']=='volume'}
            atomic_json(export/'volumes.json',json.loads(command(['docker','volume','inspect',*sorted(volumes)])) if volumes else [])
            atomic_json(export/'dienstzustand.json',state)
            export_images(targets,export)
            export_rootfs(targets,export)
            for name in ('containers.json','volumes.json','dienstzustand.json'):
                os.chmod(export/name,0o600)
            state['phase']='synchronisieren'; persist()
            log('rsnapshot sync beginnt; alle betroffenen Dienste bleiben gestoppt.')
            log(command(['rsnapshot','-c',str(cfg),'sync']).strip())
            stopped(state)
            state['phase']='pruefen'; persist()
            verify(sources,snapshot/'.sync'/'localhost',checksums=False,ignore_paths=verification_ignores(settings))
            stopped(state)
            state['phase']='rotieren'; persist()
            log(command(['rsnapshot','-c',str(cfg),'weekly']).strip())
            # Erst nach erfolgreicher Rotation und dauerhaft geschriebenem Stand freigeben.
            os.sync()
            state['verified']=True; persist()
            restart_services(state,persist)
            log('ERFOLGREICH: kopiert, Metadaten geprüft und vorherigen Dienstzustand wiederhergestellt. Inhaltsprüfung separat bei Bedarf.')
        except BaseException as error:
            failed_phase=state['phase']
            if failed_phase=='starten':
                try:
                    # Auch einen teilweise gelungenen Wiederanlauf zurücknehmen.
                    stop_services(state,persist)
                except BaseException as stop_error:
                    state['stop_error']=str(stop_error)
                    log('ACHTUNG: Nicht alle Dienste konnten erneut gestoppt werden: '+str(stop_error))
            state['failed_phase']=failed_phase; state['phase']='fehler'; state['error']=str(error) or type(error).__name__; persist()
            log('FEHLER: '+state['error'])
            log('Kein automatischer Neustart. Journal: '+str(journal))
            raise


def verify_snapshot(settings,name='weekly.0'):
    """Manueller Inhaltsvergleich; keine Dienste stoppen/starten, keine Snapshots ändern."""
    if os.geteuid()!=0:raise RuntimeError('--verify erfordert root.')
    if not re.fullmatch(r'weekly\.[0-9]+',name):
        raise RuntimeError('Nur abgeschlossene weekly.N-Snapshots auswählen; kein .sync.')
    mount_check(settings)
    root=Path(settings['state_root']);root.mkdir(mode=0o700,parents=True,exist_ok=True)
    with (root/'lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        snapshot=Path(settings['snapshot_root'])/name
        if snapshot.is_symlink() or not snapshot.is_dir():
            raise RuntimeError('Abgeschlossener Snapshot fehlt: '+str(snapshot))
        saved=snapshot/'localhost'/str(root).lstrip('/')/'export'/'dienstzustand.json'
        original=json.loads(saved.read_text())
        sources=[Path(p) for p in original['sources']]
        if not sources or any(not p.is_absolute() or str(p)=='/' for p in sources):
            raise RuntimeError('Ungültige Quellen im Snapshot.')
        # Prüft auch neue/ersetzte Container der betroffenen Projekte.
        targets,_,services=plan(settings)
        original_state={'containers':original['containers'],'services':original['services']}
        current_state={'containers':[container_state(c) for c in targets],'services':services}
        # Ursprüngliche Container können inzwischen neu erstellt worden sein; ihre alten IDs
        # deshalb nur berücksichtigen, wenn sie im aktuellen Docker-Bestand noch vorkommen.
        existing={c['Id'] for c in inspect_containers()}
        original_state['containers']=[c for c in original_state['containers'] if c['id'] in existing]
        stopped(original_state);stopped(current_state)
        report={'snapshot':str(snapshot),'started':datetime.datetime.now().astimezone().isoformat(),
                'phase':'pruefen','checksums_verified':False,'sources':list(map(str,sources)),
                'verification_ignored_paths':list(map(str,verification_ignores(settings))),
               'verification_ignored_files':list(map(str,VOLATILE_CHECK_FILES)),
               'verification_ignored_directory_timestamps':list(map(str,VOLATILE_CHECK_DIR_TIMES))}
        status=root/'checksums-status.json'
        atomic_json(status,report)
        try:
            log('Manueller Inhaltsvergleich: '+str(snapshot))
            log('Vergleicht mit den heutigen Quellen; spätere Änderungen erscheinen ebenfalls als Abweichungen.')
            for source in sources:
                if not source.exists():raise RuntimeError('Heutige Quelle fehlt: '+str(source))
            verify(sources,snapshot/'localhost',checksums=True,ignore_paths=verification_ignores(settings))
            stopped(original_state);stopped(current_state)
            report.update(phase='fertig',checksums_verified=True,
                          finished=datetime.datetime.now().astimezone().isoformat())
            atomic_json(status,report)
            log('ERFOLGREICH: Dateiinhalte der geprüften Bereiche stimmen mit den heutigen Quellen überein; ausgenommene Laufzeitdaten bleiben ungeprüft. Keine Dienste gestartet.')
        except BaseException as error:
            report.update(phase='fehler',error=str(error) or type(error).__name__)
            atomic_json(status,report)
            log('Prüfung nicht erfolgreich. Eine Abweichung kann auch seit der Sicherung entstandene Änderungen bedeuten.')
            raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--settings',default='/etc/docker-rsnapshot.json')
    parser.add_argument('--resume',action='store_true',help='Gescheiterten Quellenvergleich ausdrücklich inkrementell fortsetzen und erneut prüfen.')
    parser.add_argument('--run',action='store_true',help='Dienste stoppen, sichern, prüfen und bei Erfolg vorherigen Zustand herstellen.')
    parser.add_argument('--plan',action='store_true',help='Nur lesend planen (Standard).')
    parser.add_argument('--verify',action='store_true',help='Separater manueller Prüfsummenvergleich; betroffene Dienste müssen bereits gestoppt sein.')
    parser.add_argument('--snapshot',default='weekly.0',help='Snapshot für --verify, Standard weekly.0.')
    args=parser.parse_args()
    if sum((args.run,args.plan,args.verify,args.resume))>1:parser.error('--run, --resume, --plan und --verify schließen sich aus.')
    if args.snapshot!='weekly.0' and not args.verify:parser.error('--snapshot nur zusammen mit --verify verwenden.')
    settings=json.loads(Path(args.settings).read_text())
    for tool in ('docker','systemctl','findmnt','rsnapshot','rsync'):
        if not shutil.which(tool): raise RuntimeError('Werkzeug fehlt: '+tool)
    if args.verify:
        verify_snapshot(settings,args.snapshot)
    elif args.run or args.resume:
        run(settings,resume=args.resume)
    else:
        targets,sources,services=plan(settings)
        for c in targets: log(('STOPPEN: ' if c['State']['Running'] else 'BLEIBT GESTOPPT: ')+c['Name'].lstrip('/'))
        for s in services: log(('STOPPEN: ' if s['active'] else 'BLEIBT GESTOPPT: ')+s['name'])
        for p in sources: log('Quelle: '+str(p))
        log('Ziel: '+settings['snapshot_root'])
        log('Inhaltsprüfung: separater manueller Job; reguläres Backup prüft Größe, Zeitstempel und Metadaten.')
        for path in verification_ignores(settings):log('Nur von strenger Abschlussprüfung ausgenommen, weiterhin gesichert: '+str(path))
        log('Nur Planung. Keine Dienste und keine Dateien verändert.')


if __name__=='__main__':
    signal.signal(signal.SIGTERM,lambda *_: (_ for _ in ()).throw(KeyboardInterrupt('Abbruch durch SIGTERM')))
    try: main()
    except (Exception,KeyboardInterrupt) as error:
        log('ABGEBROCHEN: '+(str(error) or type(error).__name__))
        sys.exit(1)
