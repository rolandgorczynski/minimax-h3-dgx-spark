#!/usr/bin/env python3
"""Redaktionell geprüfte Bildregie auf gesicherte Studio-Fassungen anwenden; keine Modellaufrufe."""
import argparse
import copy
import datetime
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'automation/comics'))
from engine import Engine
from lettering_plan import prepare
from source_generator import emit
from stories import validate_definition
PREFIXES=(
 'Erzählerkachel: Der Erzählertext wird nachträglich gesetzt. Weder Sprechblasen noch Kästen oder Schrift zeichnen. Oben eine ruhige freie Fläche reservieren, Köpfe und wichtige Hände darunter. ',
 'Dialogkachel: Die gesprochenen Texte und Blasen werden nachträglich gesetzt. Keinen Erzählerkasten, keine Blasen und keine Schrift zeichnen. Freie Flächen bei den Sprechern vorsehen, Gesichter und Hände frei halten. ')
FRAME='Eine einzige zusammenhängende Illustration im gewählten Bildstil; die Umgebung läuft bis an alle Bildränder durch. Jede zugeordnete Figur erscheint nur einmal, zusätzliche Hintergrundfiguren nur wie ausdrücklich beschrieben. '

def head(story):
    text=story.partition('Verbindliche Zustände:')[0].strip()
    for prefix in PREFIXES:text=text.removeprefix(prefix.strip()).strip()
    # Frühere Raumreservierung nur entfernen, wenn ein vollständiger Satz allein diesen Zweck hat.
    text=re.sub(r'(?:(?<=\.)\s*|^)(?:Freie dunkle Wandfläche über der Katze|Oben (?:eine )?[^.!?]*(?:freihalten|reservieren))\.', '',text).strip()
    return text

def current_clothing(value):
    sentences=[]
    for sentence in re.split(r'(?<=[.!?])\s+',value):
        sentence=re.split(r';\s*(?:später|erst|danach|anschließend)\b',sentence,flags=re.I)[0].strip()
        if sentence and not re.search(r'\b(?:später|erst|zu Beginn|danach|anschließend)\b',sentence,re.I):sentences.append(sentence)
    return ' '.join(sentences).strip()

def build(before,review):
    value={k:copy.deepcopy(before[k]) for k in ('mode','name','count_policy') if k in before};p=copy.deepcopy(before['payload']);value['payload']=p
    names={c['name']:c['id'] for c in p['characters']}
    for c in p['characters']:
        cleaned=current_clothing(c.get('outfit',''))
        if cleaned and cleaned!=c.get('outfit'):
            c['art_direction_original_outfit']=c['outfit'];c['outfit']=cleaned
    for number,scene in enumerate(p['scenes'],1):
        change=review.get('panels',{}).get(str(number),{})
        if 'visible' in change:scene['characters']=[names[n] for n in change['visible']]
        if 'offscreen' in change:scene['offscreen_speakers']=[names[n] for n in change['offscreen']]
        text=change.get('story',head(scene['story']))
        if change.get('append'):text+=' '+change['append']
        scene['story']=change.get('frame',FRAME)+text
        states={}
        for ident in scene['characters']:
            ledger=scene.get('continuity_state',{}).get(ident,{})
            # Besitz und spätere Ereignisse bleiben im Register, nicht im visuellen Figuren-Zustand.
            clothing=current_clothing(ledger.get('clothing',''))
            parts=[clothing]
            if ledger.get('life') and ledger['life']!='lebend':parts.append('Lebenszustand: '+ledger['life'])
            posture=ledger.get('posture','')
            if posture and not re.search(r'\b(?:Nahaufnahme|Detailansicht|Nahansicht|Nah auf|Ausschnitt|symbolisch|Spiegel|Reflexion)\b',text,re.I):parts.insert(0,posture)
            prior=scene.get('character_states',{}).get(ident,'')
            if prior:parts.append(prior)
            state='; '.join(x for x in parts if x)
            if state:states[ident]=state
        for name,state in change.get('visual_states',{}).items():states[names[name]]=state
        scene['character_states']=states
        if 'continuity' in change:scene['continuity']=change['continuity']
        assert len(scene['story'])<=4000
    assert p['article']==before['payload']['article']
    assert p.get('planned_article')==before['payload'].get('planned_article')
    assert p['narrative_plan']==before['payload']['narrative_plan']
    assert len(p['scenes'])==len(before['payload']['scenes'])
    assert [(s.get('dialog',''),[b['text'] for b in s.get('bubbles',[])]) for s in p['scenes']]==[(s.get('dialog',''),[b['text'] for b in s.get('bubbles',[])]) for s in before['payload']['scenes']]
    assert [c['id'] for c in p['characters']]==[c['id'] for c in before['payload']['characters']]
    for s,old in zip(p['scenes'],before['payload']['scenes']):assert s.get('continuity_state')==old.get('continuity_state')
    Engine.validate_scenes(None,p['scenes'],len(p['scenes']),p['characters'])
    p['scenes'],report=prepare(p['scenes'],p['characters'])
    if report['unresolved_panels']:raise ValueError('Beschriftung passt nicht: '+json.dumps(report['unresolved_panels']))
    p['art_direction_review']={'version':1,'reviewed_by':'Codex','basis':'Lokale Schneiderlein-Vergleiche; redaktionelle Übertragung auf diese Handlung','note':review['note'],'images_generated_for_this_revision':False,'visual_approval':'Bilder nach dem Generieren prüfen','visible_inventory_separate':True,'full_frame_art':True}
    p['script_review']={**p.get('script_review',{}),'art_direction_reviewed':True,'continuity_register_unchanged':True,'images_generated':False}
    p['source_script']=emit({'title':p['title'],'author':p.get('book_author',''),'style':p['style'],'visual_style_pending':p.get('visual_style_pending',False),'mood':'Klare Bildregie mit getrenntem Handlungsregister und sichtbarer Szene.','characters':p['characters'],'scenes':p['scenes']})
    p['script_needs_replan']=before['payload'].get('script_needs_replan',False)
    return validate_definition(value),report

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('basis',nargs='+');parser.add_argument('--apply',action='store_true')
    parser.add_argument('--redo',action='store_true',help='Eigene geprüfte Revision erneut anwenden; fremde Zwischenänderungen bleiben geschützt.')
    parser.add_argument('--state-dir',type=Path,default=Path('/home/jee/docker-data/comic-automation/bildregie-redaktion/20261027'))
    args=parser.parse_args();folder=args.state_dir;state_path=folder/'status.json';state=json.loads(state_path.read_text());rows={r['basis']:r for r in state['geschichten']}
    reviews=json.loads((ROOT/'examples/comics/bildregie/redaktionelle_anpassungen.json').read_text())['geschichten']
    token=None
    if args.apply:token=subprocess.check_output(['docker','exec','comic-automation-comic-automation-1','python','-c','import os;print(os.getenv("API_TOKEN",""))'],text=True).strip()
    def api(path,value=None):
        req=urllib.request.Request('http://192.168.1.224:8090'+path,data=None if value is None else json.dumps(value,ensure_ascii=False).encode(),method=None if value is None else 'PATCH',headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)
    for basis in args.basis:
        row=rows[basis]
        if row['status']=='fertig' and not args.redo:print('Bereits fertig:',basis);continue
        review=reviews[basis];before=json.loads((folder/'vorher'/(basis+'.json')).read_text());value,report=build(before,review)
        if args.apply:
            current=api('/stories/'+row['story_id'])
            expected=row.get('version_nachher',before['version']) if args.redo else before['version']
            if current['version']!=expected:raise ValueError('Geschichte wurde inzwischen geändert; nicht überschrieben: '+basis)
            if args.redo:
                (folder/'nachher').mkdir(exist_ok=True)
                (folder/'nachher'/(basis+'-v'+str(current['version'])+'.json')).write_text(json.dumps(current,ensure_ascii=False,indent=2)+'\n')
            saved=api('/stories/'+row['story_id'],{**value,'version':expected})
            (folder/'nachher').mkdir(exist_ok=True);(folder/'nachher'/(basis+'.json')).write_text(json.dumps(saved,ensure_ascii=False,indent=2)+'\n')
            remote=api('/stories/'+row['story_id']);assert remote['payload']['scenes']==value['payload']['scenes']
            out=ROOT/'examples/comics/erzaehlerfassungen';stem=basis+'-erzaehler'
            # Private Bilder gehören ausschließlich in den lokalen Snapshot.
            portable=copy.deepcopy(value)
            for c in portable['payload']['characters']:c.pop('inline_references',None)
            (out/(stem+'.json')).write_text(json.dumps(portable,ensure_ascii=False,indent=2)+'\n')
            (out/(stem+'.txt')).write_text('\n'.join(line.rstrip() for line in value['payload']['source_script'].splitlines()).rstrip()+'\n')
            (out/(stem+'-beschriftungspruefung.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
            row.update(status='fertig',version_nachher=saved['version'],redaktion=review['note'],gezielte_korrekturen=list(review.get('panels',{})),beschriftungswarnungen=report['warnings'])
            state['stand']=datetime.datetime.now().astimezone().isoformat();state_path.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
        print(('Gespeichert:' if args.apply else 'Geprüft:'),basis,len(value['payload']['scenes']),'Kacheln;',len(review.get('panels',{})),'gezielte Anpassungen;',len(report['warnings']),'Beschriftungswarnungen')
    done=sum(r['status']=='fertig' for r in state['geschichten'])
    progress=['# Fortschritt der Bildregie','',f'**{done} / {len(state["geschichten"])} weitere Geschichten fertig.** Das Schneiderlein bleibt die separat geprüfte Referenz.','',f'Umfang: {sum(r["kacheln"] for r in state["geschichten"])} Kacheln. Vor jeder Änderung liegt ein privater Snapshot vor.','', 'Handlung, Textwortlaut, Figuren-IDs, Kachelanzahl und Kontinuitätsregister bleiben erhalten. Überarbeitet werden sichtbare Bildbeschreibung und visuelle Figuren-Zustände. Zukünftige Angaben werden aus der Standardkleidung entfernt, bleiben aber im gesicherten Original und Handlungsregister erhalten.','', '**Keine neuen Bilder erzeugt.** Diese Prüfung ist redaktionell und technisch; die späteren Bilder müssen weiterhin angesehen werden.','', 'Lokaler Status und private Vorher-/Nachher-Snapshots: `/home/jee/docker-data/comic-automation/bildregie-redaktion/20261027/`.','', '## Auswahl im Studio','', 'In Schritt 1, Schritt 2 und im Vorlagenkatalog sind zunächst diese 89 Geschichten sichtbar. Weitere vorhandene Geschichten und Vorlagen bleiben gespeichert und sind für später ausgeblendet. Eine ausdrücklich neu angelegte Geschichte wird der Auswahl hinzugefügt. Die letzte geöffnete Geschichte und vorhandene Ausgaben bleiben zugänglich.','', 'Die Auswahl wird lokal unter `story-selection-ids` gespeichert, die zurückgestellten Vorlagen unter `source-catalog-deferred`. Die vorherigen Einstellungen liegen im privaten Snapshot `auswahl-einstellungen-vorher.json`; beim späteren Erweitern wird die Auswahl geändert, nicht der Datenbestand gelöscht.','', '## Technische Prüfung','', 'Alle überarbeiteten Szenen wurden nach dem Speichern aus der API zurückgelesen. Textwortlaut und vollständiges Kontinuitätsregister werden gegen die Originale geprüft. Für die 89 Geschichten wurden keine neuen Bilder gestartet. Die technische Beschriftungsprüfung ersetzt keine spätere Sichtprüfung der Bilder.','', 'Explizite Stimmen außerhalb des Bildes (`offscreen_speakers`) erzeugen keine zusätzlichen Körper. Ohne diese optionale Kennzeichnung bleibt das bisherige Verhalten erhalten.','', '| Geschichte | Kacheln | Stand |','|---|---:|---|']
    progress += [f'| {r["titel"]} | {r["kacheln"]} | {r["status"]} |' for r in state['geschichten']]
    (ROOT/'docs/Comic_Bildregie_Fortschritt.md').write_text('\n'.join(progress)+'\n')
    print('Fortschritt:',done,'/',len(state['geschichten']))
if __name__=='__main__':main()
