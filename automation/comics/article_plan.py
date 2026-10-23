"""Artikel in prüfbare Szenen zerlegen; Original und Titel unverändert erhalten."""
import copy
import json
import uuid
from character_profiles import narrative
import dialogue
from series import context as series_context


def draft_batches(engine,job,prompt,article,cast,ledger,locked,tag='article-scenes',issues=None,existing=None):
    import json
    result=[];states=copy.deepcopy((engine.store.get(job).get('planning_source') or {}).get('payload',{}).get('series',{}).get('initial_states',{}))
    for start in range(0,len(locked),8):
        group=locked[start:start+8];ids={q for section in group for q in section['quote_ids']}
        local_ledger=[q for q in ledger if q['id'] in ids]
        relevant=[issue for issue in issues or [] if start<issue.get('panel',0)<=start+len(group)]
        if existing is not None and not relevant:scenes=copy.deepcopy(existing[start:start+len(group)])
        else:
            engine.store.stage(job,'article_adjust' if issues else 'article_scenes',planned_panels=start,total_panels=len(locked))
            intro=prompt.split('\nDIALOGLISTE:')[0].replace('genau '+str(len(locked)), 'genau '+str(len(group)))
            context=(article if len(article)<=16000 else '\n'.join(x['source_excerpt'] for x in group))
            instruction=intro+'\nErzeuge ausschließlich die folgenden '+str(len(group))+' Quellabschnitte, in dieser Reihenfolge. '+                'Frisur und Kleidung gelten weiter, bis der Ausgangstext eine Änderung nennt. Änderungen in character_states festhalten. '+                'Gesprochene Texte nicht selbst schreiben; das Skript setzt die festgelegten Zitate ein.'+                '\nBISHERIGE FIGURENZUSTÄNDE:'+json.dumps(states,ensure_ascii=False)+                '\nDIALOGLISTE:'+json.dumps(local_ledger,ensure_ascii=False)+                '\nQUELLABSCHNITTE:'+json.dumps(group,ensure_ascii=False)+'\nAUSGANGSTEXT:'+context
            if relevant:instruction+='\nPLATZPROBLEME:'+json.dumps(relevant,ensure_ascii=False)
            def validate(value):return engine.validate_scenes(dialogue.apply_sections(value,local_ledger,cast,group),len(group),cast)
            scenes=engine.json_call(job,tag+'-'+str(start+1).zfill(5),instruction,validate,tokens=len(group)*500+500)
        for scene in scenes:
            states.update(scene.get('character_states',{}))
            scene['character_states']={**{k:v for k,v in states.items() if k in scene.get('characters',[])},**scene.get('character_states',{})}
        result.extend(scenes)
    return result


def prepare(engine,stories,job):
    store=engine.store;entry=store.get(job);snapshot=entry['planning_source'];source=copy.deepcopy(snapshot['payload'])
    article=source['article'];count=entry['request']['kacheln']
    store.stage(job,'article_characters')
    existing=source.get('characters',[])
    def people(value):
        if not isinstance(value,dict) or not isinstance(value.get('characters'),list) or not 1<=len(value['characters'])<=4:raise ValueError('1–4 Figuren erforderlich.')
        names=[]
        for c in value['characters']:
            for key,limit in [('name',80),('description',1000),('outfit',600)]:
                if not isinstance(c.get(key),str) or not c[key].strip() or len(c[key])>limit:raise ValueError('Ungültiges Figurenprofil.')
            names.append(c['name'].casefold())
        if len(set(names))!=len(names):raise ValueError('Figurennamen müssen eindeutig sein.')
        return value['characters']
    continuity=series_context(source)
    profiles_hint=[{k:c.get(k,'') for k in ('name','aliases','description','outfit')} for c in existing]
    result=engine.json_call(job,'article-people',
        'Zerlege den folgenden deutschen Ausgangstext für einen Comic. Plane ausschließlich die darin auftretenden Hauptfiguren. '
        'Erfinde keine Handlung und keine Namen für unbenannte Personen; verwende dann eine neutrale Rollenbezeichnung. '
        'Aussehen ohne Angaben im Text nur als symbolische Gestaltung kennzeichnen. Personen mit konstantem Gesicht beschreiben. '
        'Bei Veränderungen von Frisur oder Kleidung im Verlauf ausdrücklich festhalten, dass diese sich je Szene ändern dürfen. '
        'Return ONLY JSON {"characters":[{"name":"Name oder Rolle","description":"Gesicht und Identitätsmerkmale","outfit":"Kleidung"}]}. '
        '1–4 Figuren, alle Texte auf Deutsch. Bei vorhandenen Figuren deren Namen exakt übernehmen. '
        +'\nVORHANDENE FIGUREN:'+json.dumps(profiles_hint,ensure_ascii=False)+'\n'+continuity+'\nNEUER AUSGANGSTEXT:\n'+article,people,tokens=1100)
    cast=[]
    for c in result:
        old=next((p for p in existing if c['name'].casefold() in [p['name'].casefold(),*[a.casefold() for a in p.get('aliases',[])]]),None)
        cast.append(copy.deepcopy(old) if old else {**c,'id':uuid.uuid5(uuid.UUID(entry['story_id']),c['name'].casefold()).hex,'aliases':[],'variants':{},'references':[]})
    if source.get('series'):
        cast.extend(copy.deepcopy(c) for c in existing if c['id'] not in {p['id'] for p in cast})
        if len(cast)>8:raise ValueError('Die Serie hat mehr als acht Figuren. Nicht benötigte Figuren im Entwurf entfernen.')
    store.stage(job,'article_dialogue')
    ledger=dialogue.collect(engine,job,article,cast)
    store.stage(job,'article_scenes')
    profiles=[narrative(c) for c in cast]
    locked=dialogue.sections(article,ledger,count)
    store.write(job,'source-sections.json',locked)
    prompt=(f'Adaptiere den gelieferten Ausgangstext in genau {count} chronologisch unterschiedliche Comic-Kacheln. '
        'Keine neue Geschichte, keine zusätzlichen Ereignisse, kein erfundenes Ende, keine erfundenen Zitate. '
        'Der vorhandene Schluss darf offen bleiben. Den Anfang und den Schluss abdecken. Das ist eine Vorplanung, die der Nutzer prüft. '
        'Vorgegebene Vorgeschichte, Persönlichkeit, Motivation und Gesinnung beachten, soweit sie dem Ausgangstext nicht widersprechen. Nicht festgelegte Eigenschaften offen lassen. '
        'Szenen konkret und bildlich unterschiedlich beschreiben. Veränderungen von Haarlänge und Kleidung zeitlich korrekt abbilden. '
        'Pro Szene genau die sichtbaren Figuren-IDs angeben. Erzählertext nur für notwendige Handlung, Ort, Zeit oder Übergänge, höchstens 130 Zeichen. '
        'Eine Szene darf ganz ohne Erzählerkasten auskommen. Keine Gespräche im Erzählerkasten wiederholen oder indirekt nacherzählen. '
        'Die QUELLABSCHNITTE legen die Reihenfolge fest: Ergebnis 1 gehört zu Abschnitt 1, Ergebnis 2 zu Abschnitt 2 und so weiter. '
        'Nur die Bildkomposition und einen optionalen Erzählertext für den jeweiligen source_excerpt formulieren. '
        'Die Dialogverteilung ist bereits festgelegt und wird vom Skript eingesetzt. quote_ids und bubbles nicht selbst schreiben. '
        'Möglichst ein Gespräch mit Frage und Antwort gemeinsam zeigen. Meist höchstens zwei kurze Sprechblasen je Kachel planen. '
        'Für Sprechblasen freie Flächen in der Bildkomposition vorsehen; Gesichter, Hände und wichtige Handlungen sichtbar halten. '
        'Bei Gesprächen die erste sprechende Figur links und die antwortende Figur rechts anordnen und im Bildtext ausdrücklich benennen. '
        'Keine Zitate kürzen, zusammenfassen oder weglassen. Keine eigenen bubbles schreiben: Text und Sprecher werden aus der Dialogliste eingesetzt. '
        'Andere Zitatarten (Begriffe, Gedanken, Schrift, unsichere Angaben) nicht als Gespräch einsetzen. '
        'Return ONLY JSON als Array mit genau '+str(count)+' Objekten: '
        '[{"heading":"Kurzer deutscher Titel","story":"Bildkomposition, höchstens 600 Zeichen",'
        '"dialog":"Deutscher Erzählertext","characters":["Figuren-ID"],'
        '"character_states":{}}]. '
        'Alle Texte ausschließlich auf Deutsch.\nFIGUREN:\n'+json.dumps(profiles,ensure_ascii=False)+'\nDIALOGLISTE:\n'+json.dumps(ledger,ensure_ascii=False)+'\nQUELLABSCHNITTE:\n'+json.dumps(locked,ensure_ascii=False)+'\nAUSGANGSTEXT:\n'+article)
    prompt=continuity+prompt
    def validate(value):
        scenes=engine.validate_scenes(dialogue.apply_sections(value,ledger,cast,locked),count,cast)
        for scene in scenes:
            for bubble in scene['bubbles']:
                if bubble.get('expression','normal') not in ('normal','shout','whisper'):bubble['expression']='normal'
        return scenes
    scenes=(draft_batches(engine,job,prompt,article,cast,ledger,locked) if count>12 else engine.json_call(job,'article-scenes',prompt,validate,tokens=min(8000,count*420+500)))
    initial_states=copy.deepcopy(source.get('series',{}).get('initial_states',{}))
    for scene in scenes:
        initial_states.update(scene.get('character_states',{}))
        scene['character_states']={k:v for k,v in initial_states.items() if k in scene.get('characters',[])}
    store.stage(job,'article_check')
    fit=engine.preflight({'scenes':scenes},cast)
    if not fit['valid']:
        store.stage(job,'article_adjust')
        if count>12:scenes=draft_batches(engine,job,prompt,article,cast,ledger,locked,tag='article-scenes-fit',issues=fit['issues'],existing=scenes)
        else:scenes=engine.json_call(job,'article-scenes-fit',prompt+'\nKorrigiere diese Beschriftungsprobleme, ohne die Handlung zu ändern: '+json.dumps(fit['issues'],ensure_ascii=False)+'\nENTWURF:'+json.dumps(scenes,ensure_ascii=False),validate,tokens=min(8000,count*420+500))
        fit=engine.preflight({'scenes':scenes},cast)
    quote_warnings=[f'Kachel {issue.get("panel","?")}: {issue["message"]}' for issue in fit['issues']] if not fit['valid'] else []
    quote_warnings.extend('Zitat '+q['id']+': Sprecher oder Wortlaut offen, bitte prüfen: „'+q['text']+'“' for q in ledger if q['kind']=='uncertain')
    initial_states=copy.deepcopy(source.get('series',{}).get('initial_states',{}))
    for scene in scenes:
        initial_states.update(scene.get('character_states',{}))
        scene['character_states']={k:v for k,v in initial_states.items() if k in scene.get('characters',[])}
    payload={**source,'title':snapshot['name'],'article':article,'characters':cast,'scenes':scenes,'panel_count':count,'planned_article':article,'planned_count':count,'revisions':{},'dialogue_ledger':ledger}
    store.stage(job,'article_save')
    store.write(job,'planned-storyboard.json',payload)
    # A later user edit must never be overwritten by a delayed model response.
    saved=stories.save({'mode':'editorial','name':snapshot['name'],'payload':payload},entry['story_id'],entry['story_version'])
    return {'status':'completed','planned_story_id':saved['id'],'planned_version':saved['version'],
            'planning_issues':fit['issues'],
            'warnings':quote_warnings+['Lokale Vorplanung: Szenen und Texttreue vor der Bilderzeugung prüfen.'],'artifacts':[]}
