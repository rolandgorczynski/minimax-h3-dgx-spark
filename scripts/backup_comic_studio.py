#!/usr/bin/env python3
"""Comic-Studio lokal sichern: zwei Dienste, Daten und Offline-Abbilder, mit lokalen Modellen, ohne Recovery-Test."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

PROJECT = Path(__file__).resolve().parents[1]
AREAS = {'input': '/opt/ComfyUI/input', 'output': '/opt/ComfyUI/output',
         'temp': '/opt/ComfyUI/temp', 'user': '/opt/ComfyUI/user',
         'custom_nodes': '/opt/ComfyUI/custom_nodes'}
COMPOSE_FILES = ('docker-compose.yml', 'docker-compose.posters.yml', 'docker-compose.comic-automation.yml')
PROJECT_PATHS = (*COMPOSE_FILES, 'Dockerfile', '.env', 'automation/comics',
                 'extensions', 'examples/comics', 'docker', 'scripts', 'docs',
                 'README.md', 'Makefile')
EXCLUDES = ('.git', '*/.git', '__pycache__', '*/__pycache__')


def say(message):
    print(message, flush=True)


def capture(command):
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode:
        # Keine Compose-Konfiguration oder Umgebungswerte auf dem Terminal ausgeben.
        raise RuntimeError('Befehl fehlgeschlagen: ' + command[0] + ' ' + command[1])
    return result.stdout.strip()


def inspect(name):
    return json.loads(capture(['docker', 'inspect', name]))[0]


def discover(comfy_name, comic_name):
    comfy = inspect(comfy_name)
    if comic_name:
        comic = inspect(comic_name)
    else:
        ids = capture(['docker', 'ps', '-a', '-q', '--filter',
                       'label=com.docker.compose.service=comic-automation']).splitlines()
        candidates = [inspect(ident) for ident in ids]
        candidates = [c for c in candidates if Path(c['Config']['Labels'].get(
            'com.docker.compose.project.working_dir', '')) == PROJECT]
        if len(candidates) != 1:
            raise RuntimeError('Comic-Container nicht eindeutig. --comic-container NAME angeben.')
        comic = candidates[0]
    for container in (comfy, comic):
        if container['State']['Status'] not in ('running', 'exited', 'created'):
            raise RuntimeError('Container nicht in einem stabilen Zustand: ' + container['Name'])
    for container, service in ((comfy, 'comfyui'), (comic, 'comic-automation')):
        if container['Config'].get('Labels', {}).get('com.docker.compose.service') != service:
            raise RuntimeError('Unerwarteter Compose-Dienst: ' + service)
    return comfy, comic


def mount(container, destination, kind):
    found = [m for m in container['Mounts'] if m['Destination'] == destination and m['Type'] == kind]
    if len(found) != 1:
        raise RuntimeError('Erwarteter Mount fehlt: ' + destination)
    return found[0]


def helper(image, volume):
    return ['docker', 'run', '--rm', '--network', 'none', '--read-only',
            '--cap-drop', 'ALL', '--cap-add', 'DAC_OVERRIDE', '--security-opt', 'no-new-privileges:true',
            '--user', '0:0', '--mount', 'type=volume,src=' + volume + ',dst=/source,readonly',
            '--entrypoint']


def idle(comfy, comic, volume):
    query = ("import sqlite3;from pathlib import Path; p=Path('/data/jobs.sqlite3');"
             "d=sqlite3.connect('file:'+str(p)+'?mode=ro',uri=True) if p.exists() else None;"
             "print(d.execute(\"select count(*) from jobs where status in ('queued','running')\").fetchone()[0] if d else 0)")
    if comic['State']['Running']:
        count = capture(['docker', 'exec', comic['Id'], 'python', '-c', query])
    else:
        count = capture(helper(comic['Image'], volume) + ['python', comic['Image'], '-c', query.replace('/data/', '/source/')])
    if int(count):
        raise RuntimeError('Comic-Aufträge laufen oder warten. Nach ihrem Abschluss erneut aufrufen; nichts angehalten.')
    if comfy['State']['Running']:
        queue = json.loads(capture(['docker', 'exec', comfy['Id'], 'curl', '-fsS',
                                   'http://127.0.0.1:8188/queue']))
        if queue.get('queue_running') or queue.get('queue_pending'):
            raise RuntimeError('ComfyUI ist beschäftigt. Nach Abschluss erneut aufrufen; nichts angehalten.')


def durable_text(path, text):
    with path.open('w') as output:
        output.write(text);output.flush();os.fsync(output.fileno())
    sync_dir(path.parent)


def sync_dir(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:os.fsync(descriptor)
    finally:os.close(descriptor)


def archive(command, target):
    """Nur vollständig geschriebene Archive erhalten eine dauerhafte Prüfsumme."""
    producer = None;compressor = None;digest = hashlib.sha256();started = time.monotonic();reported = started;size = 0
    try:
        with target.open('xb') as output:
            producer = subprocess.Popen(command, stdout=subprocess.PIPE)
            compressor = subprocess.Popen(['zstd', '-T4', '-1', '-q', '-c'], stdin=producer.stdout, stdout=subprocess.PIPE)
            producer.stdout.close()
            while block := compressor.stdout.read(4*1024*1024):
                output.write(block);digest.update(block);size += len(block)
                if time.monotonic()-reported > 45:
                    say(target.name+': %.1f GiB geschrieben'%(size/1024**3));reported=time.monotonic()
            if compressor.wait() or producer.wait():
                raise RuntimeError('Archivierung fehlgeschlagen: '+target.name)
            output.flush();os.fsync(output.fileno())
        durable_text(target.with_name(target.name+'.sha256'), digest.hexdigest()+'  '+target.name+'\n')
        say(target.name+': vollständig geschrieben (%.1f GiB)'%(size/1024**3))
    except BaseException:
        for process in (compressor, producer):
            if process and process.poll() is None:process.terminate()
        for process in (compressor, producer):
            if process:process.wait()
        raise


def tree_size(path):
    size=0;seen=set()
    for directory, dirs, files in os.walk(path, followlinks=False):
        for name in files:
            entry=Path(directory)/name
            if entry.is_symlink():continue
            stat=entry.stat();key=(stat.st_dev,stat.st_ino)
            if key not in seen:size+=stat.st_size;seen.add(key)
    return size


def ollama_paths():
    import pwd,shlex
    values=capture(['systemctl','show','ollama','-p','Environment','--value'])
    override=next((entry.partition('=')[2] for entry in shlex.split(values) if entry.startswith('OLLAMA_MODELS=')),None)
    owner=capture(['systemctl','show','ollama','-p','User','--value']) or 'root'
    root=Path(override) if override else Path(pwd.getpwnam(owner).pw_dir)/'.ollama/models'
    units=[Path('/etc/systemd/system/ollama.service'),*Path('/etc/systemd/system/ollama.service.d').glob('*.conf')]
    return root,owner,units


def tar_options():
    return ['tar', '--numeric-owner', '--acls', '--xattrs', *['--exclude=' + p for p in EXCLUDES], '-cpf', '-']


def write_json(path, value):
    durable_text(path, json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def model_references(comfy, comic):
    mounts = [m for m in comfy['Mounts'] if m['Destination'] in ('/opt/ComfyUI/models', '/data/hf-cache')]
    references = {'hinweis': 'Diese Datei enthält Pfadverweise; die Gewichte werden separat unter data/ gesichert.', 'mounts': [{k: m.get(k) for k in ('Type', 'Source', 'Destination')} for m in mounts],
                  'symlinks': [], 'modellnamen': {}}
    root = Path(mount(comfy, '/opt/ComfyUI/models', 'bind')['Source'])
    if root.is_symlink():
        references['symlinks'].append({'path': str(root), 'target': os.readlink(root)})
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            path = Path(directory) / name
            if path.is_symlink():
                references['symlinks'].append({'path': str(path), 'target': os.readlink(path)})
    for entry in comic['Config'].get('Env', []):
        key, _, value = entry.partition('=')
        if key in ('OLLAMA_URL', 'OLLAMA_TEXT_MODEL', 'OLLAMA_CRITIC_MODEL', 'OLLAMA_VISION_MODEL',
                   'TEXT_MODEL', 'VISION_MODEL', 'LLM_BACKEND'):
            references['modellnamen'][key] = value
    return references


def inventory(container):
    labels = container['Config'].get('Labels', {})
    return {'name': container['Name'].lstrip('/'), 'id': container['Id'], 'image_id': container['Image'],
            'lief_vorher': container['State']['Running'], 'user': container['Config'].get('User'),
            'compose_project': labels.get('com.docker.compose.project'),
            'compose_service': labels.get('com.docker.compose.service'),
            'compose_files': labels.get('com.docker.compose.project.config_files'),
            'mounts': container['Mounts'], 'networks': list(container['NetworkSettings']['Networks'])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, default=Path('/mnt/backup'))
    parser.add_argument('--comfy-container', default='minimax-h3-comfyui')
    parser.add_argument('--comic-container')
    parser.add_argument('--plan', action='store_true', help='Nur Umfang und Bereitschaft anzeigen; keine Sicherung, kein Anhalten.')
    args = parser.parse_args()
    for tool in ('docker', 'tar', 'zstd', 'findmnt'):
        if not shutil.which(tool):
            raise RuntimeError('Benötigtes Werkzeug fehlt: ' + tool)
    destination = args.destination.resolve(strict=True)
    filesystem = capture(['findmnt', '-n', '-T', str(destination), '-o', 'TARGET'])
    if filesystem == '/':
        raise RuntimeError('Das Sicherungsziel liegt auf dem Wurzeldateisystem. Backup-Laufwerk zuerst einhängen.')
    comfy, comic = discover(args.comfy_container, args.comic_container)
    volume = mount(comic, '/data', 'volume')['Name']
    areas = {name: Path(mount(comfy, dest, 'bind')['Source']) for name, dest in AREAS.items()}
    for area in areas.values():
        if not area.is_dir() or not os.access(area, os.R_OK | os.X_OK):
            raise RuntimeError('Datenverzeichnis nicht lesbar: ' + str(area))
    # Nicht aus Versehen einen anderen Stack mit anderen Compose-Dateien restaurieren.
    allowed = {str(PROJECT / name) for name in COMPOSE_FILES}
    for container in (comfy, comic):
        actual = set(container['Config']['Labels'].get('com.docker.compose.project.config_files', '').split(','))
        if not actual or not actual <= allowed:
            raise RuntimeError('Unbekannte Compose-Konfiguration; Sicherungsumfang zuerst prüfen.')
    idle(comfy, comic, volume)
    ollama_root,ollama_user,ollama_units=ollama_paths()
    model_areas={'comfy-modelle':Path(mount(comfy,'/opt/ComfyUI/models','bind')['Source']),
                 'hf-cache':Path(mount(comfy,'/data/hf-cache','bind')['Source']),
                 'ollama-modelle':ollama_root}
    for area in model_areas.values():
        if not area.is_dir() or not os.access(area,os.R_OK|os.X_OK):raise RuntimeError('Modellverzeichnis nicht lesbar: '+str(area))
    model_bytes=sum(tree_size(path) for path in model_areas.values())
    data_bytes=sum(tree_size(path) for path in areas.values())
    volume_size=capture(['docker','exec',comic['Id'],'du','-sb','/data']) if comic['State']['Running'] else capture(helper(comic['Image'],volume)+['du',comic['Image'],'-sb','/source'])
    data_bytes+=int(volume_size.split()[0])
    runtime_paths=[Path('/usr/local/bin/ollama'),Path('/usr/local/lib/ollama'),*ollama_units]
    if not all(path.exists() for path in runtime_paths):raise RuntimeError('Ollama-Laufzeit oder Dienstdateien fehlen.')
    sizes = json.loads(capture(['docker', 'image', 'inspect', comfy['Image'], comic['Image']]))
    image_bytes = sum(item['Size'] for item in sizes)
    reserve = int((image_bytes+model_bytes+data_bytes)*1.15) + 5 * 1024**3
    free = shutil.disk_usage(destination).free
    say('Umfang: nur Comic-Automation und ComfyUI einschließlich zugehöriger Compose-Dateien.')
    say('Daten: Geschichten, SQLite, Bewertungen, Kanal-Einstellungen, Figuren, Bilder, Workflows und Erweiterungen.')
    say('Lokale ComfyUI- und Ollama-Modelle sowie HF-Cache werden mitgesichert. Andere Docker-Stacks bleiben unberührt.')
    say('Modelle und HF-Cache unkomprimiert: %.1f GiB.'%(model_bytes/1024**3))
    say('Docker-Abbilder unkomprimiert: %.1f GiB; frei am Ziel: %.1f GiB.' % (image_bytes / 1024**3, free / 1024**3))
    say('Ziel: ' + str(destination / 'comic-studio'))
    if free < reserve:
        raise RuntimeError('Zu wenig freier Platz für Docker-Abbilder, Modelle und Daten. Mindestens %.1f GiB bereithalten.' % (reserve / 1024**3))
    if args.plan:
        say('Nur Planung: keine Dateien geschrieben, keine Dienste angehalten, kein Recovery-Test.')
        return
    import fcntl
    os.umask(0o077)
    parent = destination / 'comic-studio'
    parent.mkdir(mode=0o700, exist_ok=True)
    with (parent / '.backup.lock').open('a') as lockfile:
        try:
            fcntl.flock(lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Eine andere Comic-Sicherung läuft bereits.') from None
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        final = parent / stamp
        partial = parent / (stamp + '.partial')
        partial.mkdir(mode=0o700)  # Bestehende Sicherungen niemals überschreiben.
        (partial / 'data').mkdir();(partial / 'recovery').mkdir()
        durable_text(partial/'WIEDERHERSTELLUNG.md',(PROJECT/'docs/Comic_Studio_Offline_Backup.md').read_text())
        stopped = []; snapshots = []; restart_errors = []
        write_json(partial/'DIENSTZUSTAND.json',{'containers':[{'name':c['Name'].lstrip('/'),'lief_vorher':c['State']['Running']} for c in (comfy,comic)]})
        sync_dir(parent)
        def resume():
            # Abhängigkeit zuerst; zuvor gestoppte Dienste bleiben gestoppt.
            for container in (comfy, comic):
                if container['Id'] in stopped:
                    try:
                        capture(['docker', 'start', container['Id']]);stopped.remove(container['Id'])
                    except Exception:
                        restart_errors.append(container['Name'])
        try:
            idle(comfy, comic, volume)
            say('Leere Warteschlangen bestätigt. Halte nur die beiden betroffenen Dienste an …')
            for container in (comic, comfy):
                if container['State']['Running']:
                    stopped.append(container['Id']);capture(['docker', 'stop', '--time', '30', container['Id']])
            # Ein Auftrag könnte unmittelbar zwischen Vorprüfung und Anhalten eingegangen sein.
            idle(inspect(comfy['Id']), inspect(comic['Id']), volume)
            write_json(partial / 'modelle-nur-verweise.json', model_references(comfy, comic))
            refs = {'comfyui': inventory(comfy), 'comic-automation': inventory(comic)}
            for key, container in (('comfyui', comfy), ('comic-automation', comic)):
                tag = 'local/comic-studio-backup:' + stamp.lower() + '-' + key
                capture(['docker', 'commit', '--pause=false', container['Id'], tag])
                snapshots.append(tag);refs[key]['backup_image'] = tag
            write_json(partial / 'manifest.json', {'schema_version': 1, 'created_utc': stamp,
                'project_dir': str(PROJECT), 'containers': refs, 'comic_volume': volume,
                'bind_areas': {k: str(v) for k, v in areas.items()}, 'exclusions': list(EXCLUDES),
                'git_commit': capture(['git', '-C', str(PROJECT), 'rev-parse', 'HEAD']) if (PROJECT/'.git').exists() else None,
                'recovery_test': False,'models_included':True,'model_areas':{k:str(v) for k,v in model_areas.items()},'ollama_user':ollama_user,'model_bytes':model_bytes})
            say('Sichere Projekt und Anwendungsdaten …')
            entries = [name for name in PROJECT_PATHS if (PROJECT / name).exists()]
            archive(tar_options() + ['-C', str(PROJECT), *entries], partial / 'projekt.tar.zst')
            for name, area in areas.items():
                archive(tar_options() + ['-C', str(area), '.'], partial / 'data' / ('comfy-' + name + '.tar.zst'))
            archive(helper(comic['Image'], volume) + ['/bin/tar', comic['Image'],
                    '--numeric-owner', '--acls', '--xattrs', *['--exclude=' + p for p in EXCLUDES],
                    '-cpf', '-', '-C', '/source', '.'], partial / 'data' / 'comic-automation.tar.zst')
            say('Sichere Offline-Docker-Abbilder …')
            archive(['docker', 'image', 'save', *snapshots], partial / 'docker-images.tar.zst')
            network = next(iter(comic['NetworkSettings']['Networks']))
            # JSON ist gültiges YAML; absichtlich keine Zugangsdaten in den Overrides.
            write_json(partial / 'recovery' / 'comfyui.offline.yml', {
                'services': {'comfyui': {'image': refs['comfyui']['backup_image']}},
                'networks': {'default': {'name': '${COMIC_RESTORE_NETWORK:-' + network + '}'}}})
            write_json(partial / 'recovery' / 'comic.offline.yml', {
                'services': {'comic-automation': {'image': refs['comic-automation']['backup_image']}},
                'volumes': {'comic-automation-data': {'external': True,
                    'name': '${COMIC_RESTORE_VOLUME:-' + volume + '}'}},
                'networks': {'comfyui': {'external': True,
                    'name': '${COMIC_RESTORE_NETWORK:-' + network + '}'}}})
            say('Sichere Modelle und vorhandene HF-Cache-Struktur. Kein Download …')
            for name,area in model_areas.items():
                archive(tar_options()+['-C',str(area),'.'],partial/'data'/(name+'.tar.zst'))
            # Ollama bleibt für andere Anwendungen verfügbar. Modellblobs sind inhaltsadressiert;
            # während der Sicherung keine Modelle installieren/löschen. Tar meldet Änderungen.
            archive(tar_options()+['-C','/',*[str(path).lstrip('/') for path in runtime_paths]],partial/'ollama-programm.tar.zst')
            say('Erstelle SHA-256-Prüfsummen. Kein Recovery-Test …')
            checks = []
            for path in sorted(partial.rglob('*')):
                if path.is_file():
                    sidecar=path.with_name(path.name+'.sha256')
                    if path.name.endswith('.tar.zst'):
                        if not sidecar.is_file():raise RuntimeError('Archiv ist nicht vollständig: '+path.name)
                        digest=sidecar.read_text().split()[0]
                    else:
                        with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
                    checks.append(digest + '  ' + path.relative_to(partial).as_posix())
            durable_text(partial/'SHA256SUMS','\n'.join(checks)+'\n')
            durable_text(partial/'FERTIG','Sicherung abgeschlossen. Kein Recovery-Test durchgeführt.\n')
            sync_dir(partial);partial.rename(final);sync_dir(parent)
            say('Sicherung vollständig: ' + str(final))
        except BaseException:
            durable_text(partial/'FEHLGESCHLAGEN','Unvollständige Sicherung. Nicht als fertigen Wiederherstellungspunkt verwenden.\n')
            raise
        finally:
            resume()
            for tag in snapshots:
                try:
                    capture(['docker', 'image', 'rm', '--no-prune', tag])
                except Exception:
                    say('Temporäres Sicherungs-Image bleibt lokal erhalten: ' + tag)
            if restart_errors:
                say('Manuell wieder starten: docker start ' + ' '.join(restart_errors))


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    try:
        main()
    except (Exception, KeyboardInterrupt) as exc:
        print('Sicherung abgebrochen: ' + (str(exc) or 'unterbrochen'), file=sys.stderr)
        sys.exit(1)
