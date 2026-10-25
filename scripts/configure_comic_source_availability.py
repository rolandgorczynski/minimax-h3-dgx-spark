#!/usr/bin/env python3
"""Quellen aus der Auswahl zurückstellen oder wieder freigeben, ohne Inhalte zu löschen."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'automation/comics'))
from storage import Store
from source_generator import catalog,set_deferred


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir',type=Path,default=Path('/home/jee/docker-data/comic-automation'))
    parser.add_argument('--manifest',type=Path,default=ROOT/'examples/comics/source-availability.json')
    parser.add_argument('--restore',action='store_true',help='Alle zurückgestellten Quellen wieder in der Auswahl freigeben.')
    parser.add_argument('--apply',action='store_true',help='Auswahländerung speichern; keine Modelle oder Comic-Aufträge starten.')
    args=parser.parse_args()
    if not (args.data_dir/'jobs.sqlite3').is_file():raise ValueError('Vorhandenes Studio-Datenverzeichnis erforderlich.')
    store=Store(args.data_dir)
    ids=[] if args.restore else json.loads(args.manifest.read_text())['deferred_ids']
    if args.apply:
        result=set_deferred(store,ids)
        print(f"Gespeichert: {result['active']} Quellen aktiv, {result['deferred']} zurückgestellt. Keine Quellen, Geschichten oder Auswertungen gelöscht.")
    else:
        entries=catalog(store,with_meaning=False)
        print(f'Nur Planung: {len(entries)-len(ids)} Quellen aktiv, {len(ids)} zurückgestellt. Mit --apply speichern.')


if __name__=='__main__':main()
