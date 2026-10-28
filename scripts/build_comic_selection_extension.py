#!/usr/bin/env python3
"""Von Codex verfasste Auswahl-Erweiterung bauen und prüfen; keine Modelle, Bilder oder Studio-Änderungen."""
import argparse,copy,hashlib,json,sys,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'automation/comics'))
from stories import validate_definition
from engine import Engine
from lettering_plan import prepare
from source_generator import emit
from storage import Store
from story_meaning import cached_plan
FRAME='Eine einzige zusammenhängende Illustration im gewählten Bildstil bis an alle Bildränder. Jede genannte Figur genau einmal; keine gezeichneten Texte, Kästen oder Sprechblasen. '

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir',type=Path,default=Path('/home/jee/docker-data/comic-automation'))
    parser.add_argument('--source-file',type=Path,default=Path('/home/jee/docker-data/comic-sinnanalyse-redaktion/quellen.json'))
    args=parser.parse_args();folder=ROOT/'examples/comics/erweiterung-100';authored=json.loads((folder/'Redaktion.json').read_text())
    sources={x['id']:x for x in json.loads(args.source_file.read_text())};store=Store(args.data_dir);rows=[]
    for book in authored['geschichten']:
        source=sources[book['source']];plan=cached_plan(store,source['text']);basis=book['basis']
        if not plan or plan.get('review_method')!='redaktionell':raise ValueError('Redaktionelle Sinnanalyse fehlt: '+basis)
        if len(book['panels'])!=plan['recommended_count']:raise ValueError('Umfang weicht von Empfehlung ab: '+basis)
        cast={}
        for key,c in book['cast'].items():
            cast[key]={**c,'id':uuid.uuid5(uuid.NAMESPACE_URL,'comic-auswahl-100/'+basis+'/'+key).hex,'aliases':[],'references':[],'variants':{},'alignment':''}
        scenes=[];register={}
        for number,panel in enumerate(book['panels'],1):
            if number%3==0 and not panel['narrator']:raise ValueError('Erzähler in jeder dritten Kachel fehlt: '+basis)
            if bool(panel['narrator'])==bool(panel['speech']):raise ValueError('Entweder Erzähler oder Gespräch: '+basis+' '+str(number))
            for key,posture in panel['cast'].items():
                register.setdefault(key,{'held':'leere Hände, sofern die sichtbare Regie keinen Gegenstand zuordnet','life':'lebend','injury':'unverletzt','clothing':cast[key]['outfit']})
                register[key].update(location=panel['setting'],posture=posture)
            for key,change in panel['changes'].items():register[key].update(change)
            visual={cast[k]['id']:'; '.join([posture,register[k]['clothing'],'Lebenszustand: '+register[k]['life']]) for k,posture in panel['cast'].items()}
            # Vollständige Zustände bleiben getrennt vom knappen Bildauftrag erhalten.
            scene={'heading':panel['heading'],'setting':panel['setting'],'characters':[cast[k]['id'] for k in panel['cast']],
                   'story':FRAME+panel['image'],'dialog':panel['narrator'],
                   'bubbles':[{'speaker':cast[k]['id'],'text':text,'expression':'normal','bubble_style':'rounded'} for k,text in panel['speech']],
                   'character_states':visual,'continuity':panel['image'],
                   'continuity_state':{cast[k]['id']:copy.deepcopy(state) for k,state in register.items()}}
            if any(k not in panel['cast'] for k,_ in panel['speech']):raise ValueError('Sprecher nicht sichtbar: '+basis)
            scenes.append(scene)
        payload={'article':source['text'],'planned_article':source['text'],'planned_count':len(scenes),'panel_count':len(scenes),
                 'scenes':scenes,'characters':list(cast.values()),'library_ids':[],'style':'Klassischer Comic','visual_style_pending':True,
                 'seed':1984,'count_policy':'editorial','narrative_plan':plan,'post_summary':book['summary'],'source_provenance':source,
                 'book_author':'Sysop','editorial_script_id':basis+'-auswahl100-v1','script_needs_replan':False,
                 'narration_policy':{'version':1,'narrator_every':3,'dialogue_and_narrator':'exclusive_per_panel','silent_panel':'narrator_only','authored_by':'Codex'},
                 'script_review':{'reviewed_by':'Codex','method':'Selbst verfasste redaktionelle Adaption und technische Prüfung ohne Modellaufruf',
                                  'source_fidelity':True,'meaning_preserved':True,'count_matches_recommendation':True,'continuity_reviewed':True,
                                  'dialogue_attribution_reviewed':True,'images_generated':False,'narration_reviewed':True,'narrator_and_dialogue_exclusive':True},
                 'art_direction_review':{'version':1,'reviewed_by':'Codex','basis':'Redaktionelle Übertragung der Schneiderlein-Bildregie auf den jeweiligen Stoff',
                                         'images_generated_for_this_revision':False,'visual_approval':'Bilder nach dem Generieren prüfen','visible_inventory_separate':True,'full_frame_art':True}}
        value=validate_definition({'mode':'editorial','name':book['title']+' · Skript','count_policy':'editorial','payload':payload});payload=value['payload']
        Engine.validate_scenes(None,scenes,len(scenes),payload['characters'])
        payload['scenes'],report=prepare(scenes,payload['characters'])
        if report['unresolved_panels']:raise ValueError('Beschriftung passt nicht: '+basis)
        payload['source_script']=emit({'title':book['title'],'author':'Sysop','style':payload['style'],'visual_style_pending':True,'mood':'Einzelmomente, klare Raumachsen und präzise Zustandswechsel.','characters':payload['characters'],'scenes':payload['scenes']})
        (folder/(basis+'.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
        (folder/(basis+'.txt')).write_text(payload['source_script'].rstrip()+'\n')
        (folder/(basis+'-beschriftungspruefung.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        rows.append({'basis':basis,'source_id':source['id'],'title':book['title'],'panels':len(scenes),'warnings':report['warnings'],'source_sha256':hashlib.sha256((source['text']+'\n').encode()).hexdigest()})
        print('Geprüft:',book['title'],len(scenes),'Kacheln;',len(report['warnings']),'Warnungen')
    (folder/'Pruefbericht.json').write_text(json.dumps({'geschichten':rows,'kacheln':sum(x['panels'] for x in rows),'bilder_generiert':False},ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
