"""Experimentelle Regiefassungen aus einer gesicherten Ausgabe; Originale bleiben unverändert."""
import base64
import copy
import hashlib
import io
import json
import os
import secrets
import uuid
from PIL import Image,ImageDraw
from engine import Engine,validate_request,valid_review
from lettering import source as original_source,DESIGN
from stories import Conflict
from narrative_profiles import PROFILES,profile_prompt,beat_slots

DIRECTIONS={'tension':'Spannung','anger':'Wut / emotionale Reibung','action':'Action','blood':'Blut / sichtbare Konsequenzen','dialogue':'Dialoge mit Biss','visuals':'Filmische Bildwirkung'}
DEFAULTS={'tension':2,'anger':1,'action':1,'blood':0,'dialogue':2,'visuals':2}


def options(store,parent):
    if parent['status'] not in ('completed','needs_review'):raise Conflict('Eine fertige Comic-Ausgabe als Basis auswählen.')
    source,version=original_source(store,parent)
    return {'version':version,'title':source['title'],'count':len(source['scenes']),'style':parent['request']['stil'],'directions':DIRECTIONS,'narrative_profiles':PROFILES,'settings':{'mode':'rewrite','narrative_profile':'auto','keep_ending':True,'levels':DEFAULTS.copy(),'notes':''}}


def controls(value):
    if not isinstance(value,dict) or set(value)-{'version','mode','narrative_profile','keep_ending','levels','notes'}:raise ValueError('Unbekannte Experiment-Einstellung.')
    mode=value.get('mode','rewrite');ending=value.get('keep_ending',True);levels=value.get('levels',DEFAULTS);notes=value.get('notes','')
    profile=value.get('narrative_profile','auto')
    if not isinstance(profile,str) or profile not in PROFILES:raise ValueError('Eine bekannte Erzählweise wählen.')
    if mode not in ('staging','rewrite'):raise ValueError('Inszenierung oder freie Dramaturgie wählen.')
    if type(ending) is not bool:raise ValueError('Ende beibehalten als ja/nein senden.')
    if not isinstance(levels,dict) or set(levels)!=set(DIRECTIONS) or any(type(v) is not int or not 0<=v<=3 for v in levels.values()):raise ValueError('Jeden Regler mit 0 bis 3 angeben.')
    if not isinstance(notes,str) or len(notes)>4000:raise ValueError('Eigene Regieanweisung maximal 4000 Zeichen.')
    if not any(levels.values()) and not notes.strip() and profile=='auto':raise ValueError('Mindestens einen Regler oder eine eigene Regieanweisung verwenden.')
    return {'mode':mode,'narrative_profile':profile,'keep_ending':ending or mode=='staging','levels':levels.copy(),'notes':notes.strip()}


def enqueue(store,parent,value):
    settings=controls(value)
    if parent['status'] not in ('completed','needs_review'):raise Conflict('Zuerst eine fertige Comic-Ausgabe auswählen.')
    source,version=original_source(store,parent)
    if value.get('version')!=version:raise Conflict('Die Basis wurde verändert. Experiment neu öffnen.')
    if any(j.get('experiment_mode') and j.get('parent_job')==parent['id'] and j['status'] in ('queued','running') for j in store.list()):raise Conflict('Für diese Ausgabe läuft bereits ein Experiment.')
    needed={c for s in source['scenes'] for c in s.get('characters',[])}|{b['speaker'] for s in source['scenes'] for b in s.get('bubbles',[])}
    if any(c['id'] in needed and not c.get('inline_references') for c in source['characters']):raise ValueError('Private Figurenreferenzen fehlen. Eine vollständige Ausgabe mit gespeicherten Figurenbildern auswählen.')
    if source.get('narrator_badge') and source.get('library_ids'):source['narrator_character_id']=source['library_ids'][0]
    source['library_ids']=[];source['style']=parent['request']['stil']
    seed=secrets.randbelow(2147483648);source['seed']=seed
    request=validate_request({'kacheln':len(source['scenes']),'stil':source['style'],'seed':seed,'max_korrekturrunden':0,'signatur':source.get('signature','')})
    ident=uuid.uuid4().hex;store.create(ident,request,initial_status='editing')
    try:
        hashes=[]
        for i in range(len(source['scenes'])):
            path=store.directory(parent['id'])/f'panels/{i+1:02}_art.png';data=path.read_bytes()
            store.write(ident,f'checkpoints/experiment-originals/{i+1:02}_art.png',data);hashes.append(hashlib.sha256(data).hexdigest())
        store.write(ident,'experiment-input.json',{'source':source,'controls':settings,'parent_job':parent['id'],'parent_version':version,'original_art_sha256':hashes})
        # Keine Zuordnung zur alten Story-ID: Das Experiment ist keine kanonische neue Serienfolge.
        store.update(ident,experiment_mode=True,editorial_mode=True,parent_job=parent['id'],based_on_story_id=parent.get('story_id'),story_title=source['title']+' · Experiment')
        store.stage(ident,'queued',status='queued')
    except Exception:
        store.stage(ident,'failed',status='failed',error='Die Experiment-Basis konnte nicht vollständig gesichert werden.');raise
    return store.get(ident)


def clean_geometry(scene):
    scene=copy.deepcopy(scene);scene.pop('protected_areas',None)
    for b in scene.get('bubbles',[]):
        for key in ('x','y','w','h','tip_x','tip_y'):b.pop(key,None)
    return scene


def sheet(store,ident,count):
    indices=sorted({0,count//3,(count*2)//3,count-1});canvas=Image.new('RGB',(1024,2*470),'#252525');draw=ImageDraw.Draw(canvas)
    for j,i in enumerate(indices):
        with Image.open(store.directory(ident)/f'checkpoints/experiment-originals/{i+1:02}_art.png') as im:
            im=im.convert('RGB');im.thumbnail((500,438));x=(j%2)*512;y=(j//2)*470;canvas.paste(im,(x,y+26));draw.text((x+8,y+7),'Kachel '+str(i+1),fill='white')
    output=io.BytesIO();canvas.save(output,format='JPEG',quality=86);return output.getvalue()


def direction_text(settings):
    return (profile_prompt(settings.get('narrative_profile','auto'))+'\nREGIE: '+json.dumps({DIRECTIONS[k]:v for k,v in settings['levels'].items()},ensure_ascii=False)+
        '\n0 = keine zusätzliche Verstärkung, 1 = fein, 2 = deutlich, 3 = radikal. '
        'Mehr Wow entsteht aus verständlichen Zielen, Hindernissen, Entscheidungen, Konsequenzen und überraschenden Bildwechseln. '
        'Spannung: Information dosieren, Erwartung aufbauen und auszahlen. Wut: Motivation, Reibung und Subtext zeigen, nicht alle ständig schreien lassen. '
        'Action: klare räumliche Orientierung, unterschiedliche Einstellungen und bewusste Ruhe vor dem Höhepunkt. '
        'Blut: bei 0 keine zusätzlichen Blutspuren oder Verletzungen erfinden; höhere Werte verstärken sichtbare Folgen vorhandener Konflikte. '
        'Blut ersetzt keine Dramaturgie und verlangt keine neuen Opfer. Dialoge: unterschiedliche Stimmen, kurze Aussagen mit Absicht, keine erklärenden Doppelungen. '
        'Bildwirkung: Nahaufnahme und Totale, Perspektive, Licht, Stille und starke Schlussbilder gezielt kontrastieren. '
        '\nEIGENE REGIEANWEISUNG: '+settings['notes'])


def plan(engine,ident):
    store=engine.store;snapshot=json.loads((store.directory(ident)/'experiment-input.json').read_text());source=copy.deepcopy(snapshot['source']);settings=snapshot['controls'];cast=source['characters'];count=len(source['scenes']);original=copy.deepcopy(source['scenes']);notes=[]
    store.stage(ident,'experiment_analysis')
    people=[{k:c.get(k,'') for k in ('id','name','description','outfit','backstory','personality')} for c in cast]
    direction=direction_text(settings)
    premise=('Experimentelle fiktionale Regiefassung einer vorhandenen Comic-Ausgabe. Sie ist eine alternative Adaption, keine faktentreue Berichterstattung. '
        'Die bereitgestellten Szenen und Bilder sind die aktuelle, gegebenenfalls bereits korrigierte Fassung. Figuren-IDs, Gesichter, Alter und Identitäten erhalten. '
        'Keine neuen Figuren anlegen. Keine Wiederholung von Kacheln als Füllmaterial. Alle Texte auf Deutsch. '+
        ('Handlung, Reihenfolge, Erzählertexte und gesprochene Worte exakt erhalten. Nur Bildkomposition, Rhythmus innerhalb des Bildes und visuelle Intensität verändern. ' if settings['mode']=='staging' else
         'Die Handlungskerne erhalten, aber Bildfolge, Dramaturgie, Erzählertext und Dialoge eigenständig zuspitzen. Neue Wendepunkte und Ereignisse sind als freie Variante erlaubt, sofern sie verständlich vorbereitet werden. ')+
        ('Das Ergebnis der letzten Originalszene als Ende beibehalten, ihre Inszenierung darf stärker werden. ' if settings['keep_ending'] or settings['mode']=='staging' else 'Eine neue Schlusswendung ist ausdrücklich erlaubt; sie muss aus der Handlung entstehen. ')+direction)
    excerpt=source.get('article','');excerpt=excerpt if len(excerpt)<=10000 else excerpt[:6500]+'\n[gekürzter Mittelteil]\n'+excerpt[-3500:]
    ending=json.dumps(original[-3:],ensure_ascii=False)
    slots=beat_slots(count)
    direction_keys=('core','emotion','goal','stakes','obstacle','choice','turning_point','visual_rhythm','continuity','ending')
    def diagnosis(v):
        if not isinstance(v,dict):raise ValueError('Regieplan als Objekt erforderlich.')
        for k in direction_keys:
            if not isinstance(v.get(k),str) or not v[k].strip() or len(v[k])>1000:raise ValueError('Kurze konkrete Regievorgabe fehlt: '+k)
        beats=v.get('beats')
        if not isinstance(beats,list) or len(beats)!=len(slots):raise ValueError('Ein konkreter Beatplan für alle vorgegebenen Bereiche ist erforderlich.')
        for beat,slot in zip(beats,slots):
            if not isinstance(beat,dict) or type(beat.get('start')) is not int or type(beat.get('end')) is not int or beat['start']!=slot['start'] or beat['end']!=slot['end']:raise ValueError('Kachelbereiche des Beatplans exakt übernehmen.')
            for key in ('event','change'):
                if not isinstance(beat.get(key),str) or not beat[key].strip() or len(beat[key])>600:raise ValueError('Jeder Beat braucht ein konkretes Ereignis und eine konkrete Veränderung, keine Schlagwörter.')
        return {**{k:v[k] for k in direction_keys},'beats':[{**slot,'event':b['event'],'change':b['change']} for slot,b in zip(slots,beats)]}
    schema={'core':'Handlungskern','emotion':'Konkrete emotionale Entwicklung','goal':'Was will die Figur konkret?',
            'stakes':'Was verliert sie bei einem Scheitern?','obstacle':'Was verhindert das Ziel?',
            'choice':'Welche Entscheidung verändert den Verlauf?','turning_point':'Vorbereitete Wendung',
            'visual_rhythm':'Konkrete Einstellungswechsel und stille Momente',
            'continuity':'Verbindliche Ereignisfolgen: wer ist ab wann besiegt, tot, verletzt; welche Gegenstände oder Kleidung ändern sich?',
            'ending':'Nachwirkung des Endes','beats':[{**slot,'event':'Konkretes Ereignis mit den vorhandenen Figuren','change':'Konkrete Veränderung gegenüber davor'} for slot in slots]}
    analysis_prompt=(premise+'\nAnalysiere den fehlenden dramatischen Sog und entwirf eine konkrete Geschichte, keine allgemeine Motivationsrede. '
        'Die Bildtafel zeigt ausgewählte aktuelle Kacheln, keinen vollständigen visuellen Beweis. '
        'Bei reiner Inszenierung bleiben alle Ereignisse und Worte unverändert: nur deren vorhandene Funktion sichtbar machen. '
        'Return ONLY JSON nach diesem Schema, mit exakt diesen Kachelbereichen: '+json.dumps(schema,ensure_ascii=False)+
        '\nTextfelder maximal 1000 Zeichen. Jeder Beat braucht ein Ereignis und eine Veränderung. '
        '\nFIGUREN:'+json.dumps(people,ensure_ascii=False)+'\nBISHERIGER TEXT:'+excerpt+'\nORIGINALSCHLUSS:'+ending+
        '\nBEATRASTER:\n'+json.dumps(slots,ensure_ascii=False))
    try:guide=engine.json_call(ident,'experiment-direction-vision',analysis_prompt,diagnosis,images=[sheet(store,ident,count)],tokens=3200)
    except Exception as exc:
        notes.append('Bildgestützte Regieanalyse nicht verfügbar; Textanalyse verwendet: '+str(exc)[:300])
        guide=engine.json_call(ident,'experiment-direction-text',analysis_prompt,diagnosis,tokens=3200)
    guide=engine.require_german(ident,'experiment-direction-german',guide,diagnosis,3200)
    scenes=[];reasons=[];states=copy.deepcopy(source.get('series',{}).get('initial_states',{}))
    for start in range(0,count,6):
        size=min(6,count-start);store.stage(ident,'experiment_writing',planned_panels=start,total_panels=count)
        batch=original[start:start+size]
        instruction=premise+'\nREGIEPLAN:'+json.dumps(guide,ensure_ascii=False)+'\nFIGUREN:'+json.dumps(people,ensure_ascii=False)+'\nORIGINALSCHLUSS:'+ending+'\nLETZTE NEUE SZENEN:'+json.dumps(scenes[-2:],ensure_ascii=False)+'\nBISHERIGE FIGURENZUSTÄNDE:'+json.dumps(states,ensure_ascii=False)+'\nAKTUELLE ORIGINALKACHELN:'+json.dumps(batch,ensure_ascii=False)
        instruction+=f'\nErstelle genau {size} Kacheln für Position {start+1} bis {start+size} von insgesamt {count}. Verteile Aufbau und Höhepunkt über die GESAMTE Folge; nur die letzte Kachel endet sie. '
        relevant=[b for b in guide['beats'] if b['start']<=start+size and b['end']>=start+1]
        instruction+='\nVERBINDLICHE AUFGABEN DIESES ABSCHNITTS:'+json.dumps(relevant,ensure_ascii=False)
        instruction+='Jede Kachel muss etwas verändern: Handlung, Wissen, Beziehung, Gefahr oder bewusste emotionale Bedeutung. Keine drei gleichartigen Standbilder. Erzählertext nicht einfach das sichtbare Bild erklären lassen. Eine stille Kachel ist sinnvoll, wenn sie eine neue emotionale Bedeutung schafft. Konsequenzen gelten weiter: ein besiegtes oder totes Wesen greift später nicht ohne ausdrücklich vorbereitete Wendung erneut an. Kleidung, Blutspuren, Gegenstände und Wissen zeitlich korrekt führen. Je Kachel ein klarer Moment. Erste sprechende Figur links, Antwort rechts; freie Textflächen einplanen. Maximal zwei kurze Blasen, je 100 Zeichen, Erzählertext maximal 130 Zeichen. Keine alten Textkoordinaten übernehmen. Return ONLY JSON als Array [{"heading":"Titel","story":"vollständige Bildkomposition bis 1200 Zeichen","dialog":"Erzählertext oder leer","characters":["exakte ID"],"bubbles":[{"speaker":"exakte ID","text":"Wortlaut","expression":"normal oder shout oder whisper","bubble_style":"auto"}],"character_states":{},"dramatic_change":"Was ändert diese Kachel konkret?","visual_device":"sichtbar andere Einstellung oder bewusste stille Betonung","reason":"konkrete dramaturgische Verbesserung"}].'
        def check(value):
            result=Engine.validate_scenes(None,copy.deepcopy(value),size,cast)
            for j,s in enumerate(result):
                if not isinstance(s.get('heading',''),str) or len(s.get('heading',''))>200 or not isinstance(s.get('reason',''),str) or len(s.get('reason',''))>1000:raise ValueError('Szenentitel oder Änderungsgrund ungültig.')
                for key in ('dramatic_change','visual_device'):
                    if not isinstance(s.get(key),str) or not s[key].strip() or len(s[key])>500:raise ValueError('Jede Kachel braucht eine konkrete Aufgabe und sichtbare Inszenierung: '+key)
                if len(s['story'])>1200:raise ValueError('Bildbeschreibung maximal 1200 Zeichen.')
                if settings['mode']=='staging':
                    fixed=clean_geometry(batch[j]);fixed.update({k:s[k] for k in ('story','heading','character_states','dramatic_change','visual_device') if k in s});fixed['reason']=s.get('reason','');result[j]=fixed
                else:
                    if len(s['dialog'])>130 or len(s['bubbles'])>2 or any(len(b['text'])>100 or b.get('expression','normal') not in ('normal','shout','whisper') for b in s['bubbles']):raise ValueError('Erzählertext oder Sprechblasen kürzen; gültige Sprechweise verwenden.')
                result[j]=clean_geometry(result[j]);result[j]['bubbles']=DESIGN.validate_bubbles(result[j].get('bubbles',[]))
            return Engine.validate_scenes(None,result,size,cast)
        chunk=engine.json_call(ident,'experiment-scenes-'+str(start+1),instruction,check,tokens=850*size+400)
        store.stage(ident,'experiment_review',planned_panels=start,total_panels=count)
        review_prompt=premise+'\nPrüfe Motivation, Ursache und Wirkung, Sprecher, Figurenkontinuität, Auflösung und Lesbarkeit. Verlange echte Bewegung im Erzählbogen: Die Felder dramatic_change und visual_device sind Behauptungen und müssen in der konkreten Szene erkennbar werden. Beanstande bloß wiederholtes Stehen, Schauen und bedeutungslose Erklärkästen. Ein ruhiger Moment mit neuer emotionaler Bedeutung ist erlaubt. Prüfe gegen den Beatplan und die bisherigen Ereignisse, insbesondere Tod, Verletzungen, Gegenstände und Blutspuren. Eine freie Variante darf die Vorlage im erlaubten Umfang verändern; neue Dialoge sind keine Zitatfehler. Keine pauschalen Stilurteile. Return ONLY JSON {"approved":true,"issues":[]} oder {"approved":false,"issues":["konkreter Fehler"]}.\nREGIEPLAN:'+json.dumps(guide,ensure_ascii=False)+'\nVORIGE NEUE SZENEN:'+json.dumps(scenes[-2:],ensure_ascii=False)+'\nORIGINALSCHLUSS:'+ending+'\nGEPRÜFTER ABSCHNITT '+str(start+1)+' bis '+str(start+size)+' von '+str(count)+': '
        review=engine.json_call(ident,'experiment-review-'+str(start+1),review_prompt+json.dumps(chunk,ensure_ascii=False),valid_review,tokens=800)
        if not review['approved']:
            chunk=engine.json_call(ident,'experiment-revise-'+str(start+1),instruction+'\nENTWURF:'+json.dumps(chunk,ensure_ascii=False)+'\nZU KORRIGIEREN:'+json.dumps(review['issues'],ensure_ascii=False),check,tokens=850*size+400)
            review=engine.json_call(ident,'experiment-review-final-'+str(start+1),review_prompt+json.dumps(chunk,ensure_ascii=False),valid_review,tokens=800)
            if not review['approved']:raise ValueError('Experiment braucht eine weitere dramaturgische Korrektur: '+'; '.join(review['issues']))
        chunk=engine.require_german(ident,'experiment-german-'+str(start+1),chunk,check,850*size+400)
        for j,s in enumerate(chunk):
            states.update(s.get('character_states',{}));s['character_states']={k:v for k,v in states.items() if k in s['characters']}
            reasons.append({'panel':start+j+1,'reason':s.pop('reason','Neue experimentelle Inszenierung.'),'dramatic_change':s.get('dramatic_change',''),'visual_device':s.get('visual_device','')});scenes.append(s)
    def comparable(scene):
        s=copy.deepcopy(scene);s['bubbles']=DESIGN.validate_bubbles(s.get('bubbles',[]));s=clean_geometry(s)
        return {k:s.get(k,{} if k=='character_states' else '') for k in ('story','dialog','characters','bubbles','character_states')}
    if all(comparable(before)==comparable(after) for before,after in zip(original,scenes)):
        raise ValueError('Das Experiment hat keine Szene verändert. Regieanweisung konkreter formulieren.')
    store.stage(ident,'experiment_check')
    source['scenes']=scenes;source['revisions']={str(i):1 for i in range(count)};source['title']=(source['title'][:185]+' · Experiment')[:200]
    source['based_on_series']=source.pop('series',None)
    for key in ('dialogue_ledger','planned_article','planned_count','reference_overrides'):source.pop(key,None)
    names={c['id']:c['name'] for c in cast}
    article='Experimentelle fiktionale Variante.\n'+'\n\n'.join(s['story']+'\n'+s.get('dialog','')+'\n'+'\n'.join(names[b['speaker']]+': „'+b['text']+'“' for b in s.get('bubbles',[])) for s in scenes)
    source['article']=article if len(article)<=16000 else article[:15880]+'\nVollständige Handlung und Dialoge stehen im Szenenplan.'
    fit=engine.preflight({'scenes':scenes},cast)
    if not fit['valid']:raise ValueError('Experiment-Beschriftung passt nicht: '+json.dumps(fit['issues'],ensure_ascii=False))
    report={'parent_job':snapshot['parent_job'],'parent_version':snapshot['parent_version'],'experimental':True,'fiction':True,'original_unchanged':True,'controls':settings,'narrative_profile':copy.deepcopy(PROFILES[settings.get('narrative_profile','auto')]),'direction':guide,'changes':reasons,'notes':notes,'panel_count':count,'visual_review':'pending','original_art_sha256':snapshot['original_art_sha256']}
    source['experiment']={'parent_job':snapshot['parent_job'],'controls':settings,'fiction':True}
    store.write(ident,'editorial-source.json',source);store.write(ident,'story.json',{'title':source['title'],'story':source['article']});store.write(ident,'experiment-report.json',report)
    return source,report


def run(engine,ident):
    source,report=plan(engine,ident)
    engine.store.stage(ident,'experiment_rendering')
    from editorial import render,export
    render(engine.store,engine.client,os.getenv('WORKFLOW_TEMPLATE','/app/workflow_template.json'),source,ident,worker=True)
    root=engine.store.directory(ident);metadata=json.loads((root/'report.json').read_text());metadata.update(experimental=True,fiction=True,text_rewritten_by_local_llm=report['controls']['mode']=='rewrite',source='Experimentelle Variante der Ausgabe '+report['parent_job']);engine.store.write(ident,'report.json',metadata)
    return {'status':'needs_review','artifacts':export(engine.store,ident),'warnings':['Experimentelle, fiktionale Variante. Das Original und seine gespeicherte Geschichte wurden nicht verändert. Neue Dramaturgie, Bilder und Sprechblasen bitte prüfen.']+report['notes']}
