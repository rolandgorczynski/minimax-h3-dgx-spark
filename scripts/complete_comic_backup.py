#!/usr/bin/env python3
"""Abgebrochene Ollama-Sicherungsphase ergänzen; vorhandene Archive prüfen und behalten."""
import argparse
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import time
from backup_comic_studio import archive, capture, durable_text, ollama_paths, say, sync_dir, tar_options


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    args = parser.parse_args()
    bundle = args.bundle.resolve(strict=True)
    if not bundle.name.endswith('.partial') or not (bundle/'FEHLGESCHLAGEN').is_file():
        raise RuntimeError('Nur einen fehlgeschlagenen Teillauf fortsetzen.')
    final = bundle.with_name(bundle.name.removesuffix('.partial'))
    if final.exists() or (bundle/'FERTIG').exists():
        raise RuntimeError('Sicherung ist bereits abgeschlossen oder Ziel existiert.')
    os.umask(0o077)
    with (bundle.parent/'.backup.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        manifest = json.loads((bundle/'manifest.json').read_text())
        root, owner, units = ollama_paths()
        if root != Path('/usr/share/ollama/.ollama/models') or manifest['model_areas']['ollama-modelle'] != str(root):
            raise RuntimeError('Ollama-Pfad passt nicht zur eingerichteten Leseberechtigung.')
        capture(['sudo', '-n', '-l', '/usr/local/sbin/comic-backup-ollama'])
        required = ['projekt.tar.zst', 'docker-images.tar.zst', *['data/'+n+'.tar.zst' for n in (
            'comfy-input', 'comfy-output', 'comfy-temp', 'comfy-user', 'comfy-custom_nodes',
            'comic-automation', 'comfy-modelle', 'hf-cache')]]
        for name in required:
            path = bundle/name
            if not path.is_file() or not path.with_name(path.name+'.sha256').is_file():
                raise RuntimeError('Vollständiges Basisarchiv fehlt: '+name)
        for config in ('comfyui.offline.yml', 'comic.offline.yml'):
            if not (bundle/'recovery'/config).is_file():
                raise RuntimeError('Offline-Konfiguration fehlt: '+config)
        say('Prüfe vorhandene Archive; keine erneute Sicherung der Comic-Dienste.')
        for path in sorted(bundle.rglob('*.tar.zst')):
            sidecar = path.with_name(path.name+'.sha256')
            if not sidecar.exists():
                if path.relative_to(bundle).as_posix() not in ('data/ollama-modelle.tar.zst', 'ollama-programm.tar.zst'):
                    raise RuntimeError('Unerwartetes unvollständiges Archiv: '+str(path))
                continue
            expected = sidecar.read_text().split()[0]
            digest = hashlib.sha256()
            count = 0
            last = time.monotonic()
            with path.open('rb') as stream:
                while block := stream.read(8*1024*1024):
                    digest.update(block); count += len(block)
                    if time.monotonic()-last > 45:
                        say(path.name+': %.1f GiB geprüft'%(count/1024**3)); last=time.monotonic()
            if digest.hexdigest() != expected:
                raise RuntimeError('Prüfsumme stimmt nicht: '+str(path))
            say('Vorhandenes Archiv bestätigt: '+path.name)
        for name, command in (
            ('data/ollama-modelle.tar.zst', ['sudo','-n','/usr/local/sbin/comic-backup-ollama']),
            ('ollama-programm.tar.zst', tar_options()+['-C','/',*[str(p).lstrip('/') for p in
                (Path('/usr/local/bin/ollama'),Path('/usr/local/lib/ollama'),*units)]])):
            target = bundle/name
            if target.with_name(target.name+'.sha256').is_file():
                continue
            if target.exists():
                # Fehlgeschlagenes Archiv behalten, aber aus dem Wiederherstellungspaket nehmen.
                retained = bundle.parent/(bundle.name+'-'+target.name+'.unvollstaendig-'+str(time.time_ns()))
                target.rename(retained)
                sync_dir(bundle.parent)
                say('Unvollständiges Archiv separat erhalten: '+retained.name)
            archive(command,target)
        durable_text(bundle/'FORTSETZUNG.md',
            '# Fortsetzung der Sicherung\n\n'+datetime.datetime.now(datetime.timezone.utc).isoformat()+'\n\n'
            'Vorhandene Archive durch SHA-256 bestätigt und unverändert übernommen. '
            'Ollama-Modelle und Programm bei dieser Fortsetzung ergänzt. '
            'Anwendungsdaten stammen weiterhin vom ursprünglichen Offline-Zeitpunkt; '
            'die Comic-Dienste wurden bei der Fortsetzung nicht angehalten. '
            'Kein Recovery-Test durchgeführt.\n')
        checks=[]
        for path in sorted(bundle.rglob('*')):
            if not path.is_file() or path.name in ('SHA256SUMS','FERTIG'):
                continue
            sidecar=path.with_name(path.name+'.sha256')
            if path.name.endswith('.tar.zst'):
                digest=sidecar.read_text().split()[0]
            else:
                with path.open('rb') as stream:
                    digest=hashlib.file_digest(stream,'sha256').hexdigest()
            checks.append(digest+'  '+path.relative_to(bundle).as_posix())
        durable_text(bundle/'SHA256SUMS','\n'.join(checks)+'\n')
        durable_text(bundle/'FERTIG','Sicherung abgeschlossen. Kein Recovery-Test durchgeführt.\n')
        (bundle/'FEHLGESCHLAGEN').unlink()
        sync_dir(bundle); bundle.rename(final); sync_dir(final.parent)
        say('Sicherung vollständig: '+str(final))


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    main()
