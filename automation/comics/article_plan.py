"""Artikel in prüfbare Szenen zerlegen; Original und Titel unverändert erhalten."""
import copy
import uuid
from character_profiles import narrative
import dialogue


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
    result=engine.json_call(job,'article-people',
        'Zerlege den folgenden deutschen Ausgangstext für einen Comic. Plane ausschließlich die darin auftretenden Hauptfiguren. '
        'Erfinde keine Handlung und keine Namen für unbenannte Personen; verwende dann eine neutrale Rollenbezeichnung. '
        'Aussehen ohne Angaben im Text nur als symbolische Gestaltung kennzeichnen. Personen mit konstantem Gesicht beschreiben. '
        'Bei Veränderungen von Frisur oder Kleidung im Verlauf ausdrücklich festhalten, dass diese sich je Szene ändern dürfen. '
        'Return ONLY JSON {"characters":[{"name":"Name oder Rolle","description":"Gesicht und Identitätsmerkmale","outfit":"Kleidung"}]}. '
        '1–4 Figuren, alle Texte auf Deutsch.\nAUSGANGSTEXT:\n'+article,people,tokens=1100)
    cast=[]
    for c in result:
        old=next((p for p in existing if c['name'].casefold() in [p['name'].casefold(),*[a.casefold() for a in p.get('aliases',[])]]),None)
        cast.append(copy.deepcopy(old) if old else {**c,'id':uuid.uuid5(uuid.UUID(entry['story_id']),c['name'].casefold()).hex,'aliases':[],'variants':{},'references':[]})
    store.stage(job,'article_dialogue')
    ledger=dialogue.collect(engine,job,article,cast)
    store.stage(job,'article_scenes')
    import json
    profiles=[narrative(c) for c in cast]
    prompt=(f'Adaptiere den gelieferten Ausgangstext in genau {count} chronologisch unterschiedliche Comic-Kacheln. '
        'Keine neue Geschichte, keine zusätzlichen Ereignisse, kein erfundenes Ende, keine erfundenen Zitate. '
        'Der vorhandene Schluss darf offen bleiben. Den Anfang und den Schluss abdecken. Das ist eine Vorplanung, die der Nutzer prüft. '
        'Vorgegebene Vorgeschichte, Persönlichkeit, Motivation und Gesinnung beachten, soweit sie dem Ausgangstext nicht widersprechen. Nicht festgelegte Eigenschaften offen lassen. '
        'Szenen konkret und bildlich unterschiedlich beschreiben. Veränderungen von Haarlänge und Kleidung zeitlich korrekt abbilden. '
        'Pro Szene genau die sichtbaren Figuren-IDs angeben. Erzählertext nur für notwendige Handlung, Ort, Zeit oder Übergänge, höchstens 130 Zeichen. '
        'Eine Szene darf ganz ohne Erzählerkasten auskommen. Keine Gespräche im Erzählerkasten wiederholen oder indirekt nacherzählen. '
        'Alle als spoken markierten Originalzitate aus der Dialogliste chronologisch auf die Kacheln verteilen: Jedes genau einmal in quote_ids angeben. '
        'Möglichst ein Gespräch mit Frage und Antwort gemeinsam zeigen. Meist höchstens zwei kurze Sprechblasen je Kachel planen. '
        'Für Sprechblasen freie Flächen in der Bildkomposition vorsehen; Gesichter, Hände und wichtige Handlungen sichtbar halten. '
        'Bei Gesprächen die erste sprechende Figur links und die antwortende Figur rechts anordnen und im Bildtext ausdrücklich benennen. '
        'Keine Zitate kürzen, zusammenfassen oder weglassen. Keine eigenen bubbles schreiben: Text und Sprecher werden aus der Dialogliste eingesetzt. '
        'Andere Zitatarten (Begriffe, Gedanken, Schrift, unsichere Angaben) nicht als Gespräch einsetzen. '
        'Return ONLY JSON als Array mit genau '+str(count)+' Objekten: '
        '[{"heading":"Kurzer deutscher Titel","story":"Bildkomposition, höchstens 600 Zeichen",'
        '"dialog":"Deutscher Erzählertext","characters":["Figuren-ID"],'
        '"quote_ids":["q001","q002"]}]. '
        'Alle Texte ausschließlich auf Deutsch.\nFIGUREN:\n'+json.dumps(profiles,ensure_ascii=False)+'\nDIALOGLISTE:\n'+json.dumps(ledger,ensure_ascii=False)+'\nAUSGANGSTEXT:\n'+article)
    def validate(value):
        scenes=engine.validate_scenes(dialogue.apply(value,ledger,cast),count,cast)
        for scene in scenes:
            for bubble in scene['bubbles']:
                if bubble.get('expression','normal') not in ('normal','shout','whisper'):bubble['expression']='normal'
        return scenes
    scenes=engine.json_call(job,'article-scenes',prompt,validate,tokens=min(8000,count*420+500))
    store.stage(job,'article_check')
    fit=engine.preflight({'scenes':scenes},cast)
    if not fit['valid']:
        store.stage(job,'article_adjust')
        scenes=engine.json_call(job,'article-scenes-fit',prompt+'\nKorrigiere diese Beschriftungsprobleme, ohne die Handlung zu ändern: '+json.dumps(fit['issues'],ensure_ascii=False)+'\nENTWURF:'+json.dumps(scenes,ensure_ascii=False),validate,tokens=min(8000,count*420+500))
        fit=engine.preflight({'scenes':scenes},cast)
    quote_warnings=[f'Kachel {issue.get("panel","?")}: {issue["message"]}' for issue in fit['issues']] if not fit['valid'] else []
    quote_warnings.extend('Zitat '+q['id']+': Sprecher oder Wortlaut offen, bitte prüfen: „'+q['text']+'“' for q in ledger if q['kind']=='uncertain')
    payload={**source,'title':snapshot['name'],'article':article,'characters':cast,'scenes':scenes,'panel_count':count,'planned_article':article,'planned_count':count,'revisions':{},'dialogue_ledger':ledger}
    store.stage(job,'article_save')
    store.write(job,'planned-storyboard.json',payload)
    # A later user edit must never be overwritten by a delayed model response.
    saved=stories.save({'mode':'editorial','name':snapshot['name'],'payload':payload},entry['story_id'],entry['story_version'])
    return {'status':'completed','planned_story_id':saved['id'],'planned_version':saved['version'],
            'planning_issues':fit['issues'],
            'warnings':quote_warnings+['Lokale Vorplanung: Szenen und Texttreue vor der Bilderzeugung prüfen.'],'artifacts':[]}
