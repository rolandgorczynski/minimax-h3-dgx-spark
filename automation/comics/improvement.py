"""Gespeicherte Nutzerbewertung auf denselben Comic anwenden, ohne das Original zu ändern."""
import base64
import copy
import hashlib
import json
import os
import re


def normalized(text):
    return ''.join(c for c in text.casefold() if c.isalnum())


def remove_duplicates(source):
    removed=[]
    for index,scene in enumerate(source['scenes']):
        caption=normalized(scene.get('dialog',''))
        spoken={normalized(b['text']) for b in scene.get('bubbles',[])}
        if caption and caption in spoken:
            scene['dialog']='';removed.append(index+1)
    return removed


def revise(engine,job,snapshot):
    source=copy.deepcopy(snapshot['source']);original=copy.deepcopy(source);cast=source['characters'];count=len(source['scenes'])
    engine.store.stage(job,'feedback_prepare')
    removed=remove_duplicates(source)
    active={ident for scene in source['scenes'] for ident in scene.get('characters',[])}
    references=[c for c in cast if c['id'] in active and c.get('inline_references')][:4]
    identity_notes=[];notes=[]
    if references:
        engine.store.stage(job,'feedback_references')
        def validate_refs(value):
            items=value.get('references',[]) if isinstance(value,dict) else []
            if not isinstance(items,list) or any(not isinstance(x,dict) or x.get('id') not in {c['id'] for c in references} or not isinstance(x.get('appearance'),str) or len(x['appearance'])>500 for x in items):raise ValueError('Ungültige Referenzbeschreibung.')
            return items
        try:
            identity_notes=engine.json_call(job,'feedback-reference',
                'Beschreibe nur die direkt sichtbaren Identitätsmerkmale und Frisuren der Referenzporträts auf Deutsch. '
                'Die Bildreihenfolge entspricht der folgenden Figurenliste. Keine Handlung und keine Änderung erfinden. '
                'Die Frisur einer Figur kann im Artikel ausdrücklich verändert werden; trenne Ausgangszustand und Identität. '
                'Return ONLY JSON {"references":[{"id":"exakte Figuren-ID","appearance":"kurze sichtbare Merkmale"}]}.\nFIGUREN:'+json.dumps([{'id':c['id'],'name':c['name']} for c in references],ensure_ascii=False),
                validate_refs,images=[base64.b64decode(c['inline_references'][0]) for c in references],tokens=800)
        except Exception as exc:notes.append('Zusätzliche Referenzbeschreibung nicht verfügbar; Originalreferenzen bleiben erhalten: '+str(exc)[:180])
    engine.store.stage(job,'feedback_scenes')
    def validate(value):
        if not isinstance(value,dict) or not isinstance(value.get('changes'),list) or len(value['changes'])>count:raise ValueError('Höchstens eine Änderung pro Kachel.')
        seen=set()
        for change in value['changes']:
            if not isinstance(change,dict) or set(change)-{'panel','story','dialog','characters','character_states','reason'}:raise ValueError('Unbekannte Änderungsfelder.')
            index=change.get('panel')
            if type(index) is not int or not 1<=index<=count or index in seen:raise ValueError('Ungültige oder doppelte Kachelnummer.')
            seen.add(index)
            for key,limit in [('story',3000),('dialog',400),('reason',800)]:
                if key in change and (not isinstance(change[key],str) or len(change[key])>limit):raise ValueError('Ungültige Änderung: '+key)
            if 'story' in change and not change['story'].strip():raise ValueError('Bildbeschreibung darf nicht leer werden.')
            candidate={**source['scenes'][index-1],**{k:v for k,v in change.items() if k in ('story','dialog','characters','character_states')}}
            engine.validate_scenes([candidate],1,cast)
        return value['changes']
    prompt=(f'Verbessere dieselbe Comic-Ausgabe mit genau {count} Kacheln anhand der gespeicherten Nutzerbewertung. '
        'Der Ausgangstext ist verbindlich. Keine neue Geschichte, keine neuen Ereignisse, keine neue Pointe, keine neuen Figuren. '
        'Titel, Originaltext, Figuren-IDs, Referenzbilder, gesprochene Zitate und Kachelanzahl bleiben unverändert. '
        'Nur betroffene Bildkompositionen und falls erforderlich Erzählertexte anpassen. Bereits korrekte Szenen nicht umschreiben. '
        'Für Nahaufnahmen characters auf die tatsächlich sichtbaren Figuren-IDs begrenzen; die vorhandenen Sprecher bleiben erhalten. '
        'Erzählerkästen sollen gesprochenen Text nicht wiederholen. Ein Dialog darf daher leer werden. '
        'Visuelle Kritik in positive konkrete Anweisungen übersetzen: Handlung sichtbar, Zustand vor und nach einer Veränderung, '
        'abgeschnittene Teile tatsächlich getrennt darstellen. Jede Veränderung eindeutig der richtigen Figur zuordnen. '
        'Konstante Personen behalten Gesicht und Ausgangsfrisur. Frisuränderungen nur bei der im Original genannten Person und '
        'nur ab dem zutreffenden Handlungsschritt. Bei variierenden Zuständen character_states je Figuren-ID verwenden. '
        'Diese Zustände gelten nur für die betreffende Kachel und dürfen Identität, Alter und Person nicht austauschen. '
        'Bewertungen mit niedrigen Punkten sind Hinweise, keine Erlaubnis, das Originalende neu zu erfinden. '
        'Keine Sprechblasen oder Sprecher ändern. Keine neuen Behauptungen. Alle Texte auf Deutsch. '
        'Return ONLY JSON {"changes":[{"panel":1,"story":"verbesserte Bildkomposition",'
        '"dialog":"optional überarbeiteter Erzählertext","character_states":{"Figuren-ID":"aktueller sichtbarer Zustand"},'
        '"reason":"konkreter Bezug zur Bewertung"}]}. Nicht benötigte Felder weglassen. '
        '\nBEWERTUNG:'+json.dumps(snapshot['feedback'],ensure_ascii=False)+
        '\nAUSGANGSTEXT:'+source['article']+'\nREFERENZBEOBACHTUNGEN (können ungenau sein):'+json.dumps(identity_notes,ensure_ascii=False)+
        '\nFIGUREN:'+json.dumps([{k:c.get(k,'') for k in ('id','name','description','outfit')} for c in cast],ensure_ascii=False)+
        '\nSZENEN:'+json.dumps(source['scenes'],ensure_ascii=False))
    proposals=engine.json_call(job,'feedback-rewrite',prompt,validate,tokens=min(8000,count*500+400))
    reasons={}
    for change in proposals:
        index=change['panel']-1;reasons[index+1]=change.get('reason','Bewertung berücksichtigt.')
        for key in ('story','dialog','characters','character_states'):
            if key in change:source['scenes'][index][key]=change[key]
    removed=sorted(set(removed+remove_duplicates(source)))
    engine.store.stage(job,'feedback_check')
    source['scenes']=engine.validate_scenes(source['scenes'],count,cast)
    fit=engine.preflight({'scenes':source['scenes']},cast)
    if not fit['valid']:
        # Keep the proposed descriptions; retain already validated captions if a new caption doesn't fit.
        for issue in fit['issues']:
            index=issue['panel']-1
            source['scenes'][index]['dialog']=original['scenes'][index].get('dialog','')
        removed=sorted(set(removed+remove_duplicates(source)))
        fit=engine.preflight({'scenes':source['scenes']},cast)
        if not fit['valid']:raise ValueError('Beschriftung der Überarbeitung muss geprüft werden: '+json.dumps(fit['issues'],ensure_ascii=False))
        notes.append('Nicht passende neue Erzählertexte wurden durch die bisherige Beschriftung ersetzt.')
    style_changed=source['style']!=snapshot['original_style']
    mentioned={int(number)-1 for number in re.findall(r'\b(?:bild|kachel|panel)\s*(\d+)\b',snapshot['feedback'].get('kommentar',''),re.I) if 1<=int(number)<=count}
    redrawn=[];retained=[];changes=[]
    revisions=copy.deepcopy(source.get('revisions',{}))
    for index,(before,after) in enumerate(zip(original['scenes'],source['scenes'])):
        art_changed=any(before.get(key,{})!=after.get(key,{}) for key in ('story','characters','character_states'))
        if style_changed or art_changed or index in mentioned:
            redrawn.append(index+1);revisions[str(index)]=revisions.get(str(index),0)+snapshot['attempt']
        else:retained.append(index+1)
        if before!=after:changes.append({'panel':index+1,'reason':reasons.get(index+1,'Doppelten Erzählertext entfernt.'),
                                      'before':before,'after':after})
    source['revisions']=revisions
    report={'parent_job':snapshot['parent_job'],'feedback':snapshot['feedback'],'same_story':True,
            'source_hash':hashlib.sha256(source['article'].encode()).hexdigest(),'old_style':snapshot['original_style'],
            'new_style':source['style'],'style_changed':style_changed,'panel_count':count,
            'duplicate_captions_removed':removed,'retained_art_panels':retained,'rerendered_panels':redrawn,
            'changes':changes,'notes':notes,'quality_status':'Sichtprüfung erforderlich; Modellvorschläge sind keine Erfolgsgarantie.'}
    engine.store.write(job,'editorial-source.json',source);engine.store.write(job,'improvement-report.json',report)
    return source,report


def improve(engine,job):
    store=engine.store;snapshot=json.loads((store.directory(job)/'improvement-input.json').read_text())
    source,report=revise(engine,job,snapshot)
    store.stage(job,'feedback_reuse')
    for panel in report['retained_art_panels']:
        path=store.directory(snapshot['parent_job'])/f'panels/{panel:02}_art.png'
        if not path.is_file():raise ValueError('Originalillustration fehlt. Die Originalausgabe bitte nicht während der Verbesserung löschen.')
        if len(source['scenes'])>12:
            store.write(job,f'checkpoints/retained-panels/{panel:02}_art.png',path.read_bytes());continue
        engine.client.request('POST','/dgx-comics/automation/retain-panel',{'session':job,'panel':panel-1,'png':base64.b64encode(path.read_bytes()).decode()})
    from editorial import render,export
    render(store,engine.client,os.getenv('WORKFLOW_TEMPLATE','/app/workflow_template.json'),source,job,worker=True)
    return {'status':'needs_review','artifacts':export(store,job),'warnings':[
        f'Bewertung auf denselben Comic angewendet: {len(report["rerendered_panels"])} Bilder neu gezeichnet, {len(report["retained_art_panels"])} Originalillustrationen übernommen.',
        f'{len(report["duplicate_captions_removed"])} doppelte Erzählertexte entfernt. Neue Ausgabe bitte prüfen.']}
