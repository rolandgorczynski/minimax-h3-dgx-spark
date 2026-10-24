"""Neue Serienfolgen aus unveränderten Geschichten oder fertigen Comic-Ausgaben."""
import copy
import json
from engine import ID,STYLES,validate_request
from stories import Conflict


def bases(stories):
    entries=[]
    for item in stories.list():
        doc=stories.get(item['id']);p=doc['payload']
        if doc['mode']=='editorial' and p.get('characters') and (p.get('article') or p.get('scenes')):
            entries.append({'kind':'story','id':doc['id'],'title':doc['name'],'series':p.get('series')})
    for job in stories.store.list():
        root=stories.store.directory(job['id'])
        if job['status'] in ('completed','needs_review') and not any(job.get(k) for k in ('source_mode','planning_mode','book_mode','character_mode')) and (root/'characters.json').is_file() and ((root/'editorial-source.json').is_file() or (root/'scenes.json').is_file()):
            entries.append({'kind':'job','id':job['id'],'title':job.get('story_title') or job['id'][:8]})
    return entries


def snapshot(stories,kind,ident):
    if kind not in ('story','job') or not isinstance(ident,str) or not ID.fullmatch(ident):raise ValueError('Eine gültige Geschichte oder Comic-Ausgabe als Basis wählen.')
    store=stories.store
    if kind=='story':
        doc=stories.get(ident)
        if doc['mode']!='editorial':raise ValueError('Automatische Definition zuerst über „Ausgewählte Ausgabe übernehmen“ als Geschichte speichern.')
        p=copy.deepcopy(doc['payload']);version=doc['version'];title=doc['name']
        candidates=[j for j in stories.outputs(ident) if j['status'] in ('completed','needs_review') and (store.directory(j['id'])/'characters.json').is_file() and not j.get('book_mode')]
        if candidates:
            previous=max(candidates,key=lambda j:j.get('updated_at',''));saved=json.loads((store.directory(previous['id'])/'characters.json').read_text());known={c['id']:c for c in saved}
            for c in p.get('characters',[]):
                old=known.get(c['id'],{})
                if old.get('inline_references') and not c.get('inline_references') and all(c.get(k)==old.get(k) for k in ('name','description','outfit')):
                    c['inline_references']=old['inline_references'];c['references']=[]
    else:
        job=store.get(ident)
        if not job:raise KeyError(ident)
        if job['status'] not in ('completed','needs_review'):raise Conflict('Als Basis eine fertige Comic-Ausgabe auswählen.')
        root=store.directory(ident)
        if (root/'editorial-source.json').is_file():p=json.loads((root/'editorial-source.json').read_text())
        elif (root/'story.json').is_file() and (root/'scenes.json').is_file():
            story=json.loads((root/'story.json').read_text());plan=json.loads((root/'scenes.json').read_text());p={'title':story['title'],'article':story['story'],'scenes':plan['scenes'],'style':job['request']['stil'],'page_template':job['request'].get('page_template','standard')}
        else:raise ValueError('Diese Ausgabe hat keinen vollständigen Szenenplan.')
        if not (root/'characters.json').is_file():raise ValueError('Figurenprofile dieser Ausgabe fehlen.')
        p['characters']=json.loads((root/'characters.json').read_text());p['library_ids']=[];version=None;title=p.get('title') or job.get('story_title') or 'Comic'
    if not p.get('characters'):raise ValueError('Zuerst die Figuren der Basisgeschichte planen oder einen fertigen Comic wählen.')
    if not isinstance(p.get('series',{}),dict):raise ValueError('Ungültige Serienangaben in der Basis.')
    states=copy.deepcopy(p.get('series',{}).get('initial_states',{}))
    known={c['id'] for c in p['characters']}
    for scene in p.get('scenes',[]):states.update(scene.get('character_states',{}))
    states={k:v for k,v in states.items() if k in known}
    physical=copy.deepcopy(p.get('series',{}).get('initial_continuity_state',{}))
    for scene in p.get('scenes',[]):physical.update(scene.get('continuity_state',{}))
    physical={k:v for k,v in physical.items() if k in known}
    return {'kind':kind,'id':ident,'version':version,'title':title,'payload':p,'states':states,'physical_states':physical,'root_id':ident if kind=='story' else job.get('story_id') or ident}


def settings(stories,base):
    previous=base['payload'].get('series',{});root=previous.get('id') or base['root_id'];episode=previous.get('episode',1)
    for item in stories.list():
        meta=item.get('series') or {}
        if meta.get('id')==root:episode=max(episode,meta['episode'])
    name=previous.get('name') or base['title']
    return {'base_kind':base['kind'],'base_id':base['id'],'base_version':base['version'],'name':name,'episode':episode+1,'title':(name[:175]+' – Folge '+str(episode+1))[:200],'mode':'direct','style':base['payload'].get('style',STYLES[0]),'count':base['payload'].get('panel_count') or len(base['payload'].get('scenes',[])) or 12,'canon':previous.get('canon',''),'open_threads':previous.get('open_threads',''),'article':''}


def clean(value,defaults):
    if not isinstance(value,dict):raise ValueError('Angaben zur neuen Folge als Objekt senden.')
    result={**defaults,**value}
    for key,limit in [('name',200),('title',200),('canon',6000),('open_threads',4000),('article',16000)]:
        if not isinstance(result.get(key),str) or len(result[key])>limit:raise ValueError(f'{key}: Text mit höchstens {limit} Zeichen eingeben.')
        result[key]=result[key].strip()
    if not result['name'] or not result['title']:raise ValueError('Serientitel und Titel der neuen Folge eingeben.')
    if result.get('mode') not in ('direct','universe'):raise ValueError('Direkte Fortsetzung oder gleiches Universum wählen.')
    if type(result.get('episode')) is not int or result['episode']<2:raise ValueError('Folgennummer muss eine ganze Zahl ab 2 sein.')
    validate_request({'kacheln':result.get('count'),'stil':result.get('style')})
    return result


def get_context(stories,value):
    base=snapshot(stories,value.get('base_kind'),value.get('base_id'));default=settings(stories,base)
    if base['kind']=='story' and value.get('base_version') is not None and value['base_version']!=base['version']:raise Conflict('Die Basisgeschichte wurde inzwischen geändert. Basis neu laden.')
    return base,clean(value,default)


def context(p):
    meta=p.get('series',{})
    if not meta:return ''
    return ('SERIENKONTEXT (Hintergrund, nicht als neue Handlung nacherzählen):\n'+json.dumps({
        'serie':meta['name'],'folge':meta['episode'],'anschluss':'Direkte Fortsetzung' if meta['mode']=='direct' else 'Neue Handlung im selben Universum',
        'basierend_auf':meta['based_on']['title'],'feste_fakten':meta['canon'],'offene_faeden':meta['open_threads'],
        'bisherige_folge':meta['previous_article'],'letzte_szenen':meta['previous_ending'],'letzte_figuren_zustaende':meta['initial_states'],'koerperliche_zustaende':meta.get('initial_continuity_state',{})},ensure_ascii=False)+
        '\nIdentitäten, Aussehen und bestehende Referenzen erhalten. Neue Ereignisse stehen nur im NEUEN Ausgangstext. '
        'Abgeschlossene Ereignisse nicht neu beginnen, verstorbene Figuren nicht unbegründet zurückholen. '
        'Explizite Veränderungen im neuen Text haben Vorrang vor dem letzten Zustand.\n')


def prompt(base,value):
    p=base['payload'];meta={'id':p.get('series',{}).get('id') or base['root_id'],'name':value['name'],'episode':value['episode'],'mode':value['mode'],'based_on':{'title':base['title']},'canon':value['canon'],'open_threads':value['open_threads'],'previous_article':p.get('article',''),'previous_ending':p.get('scenes',[])[-3:],'initial_states':base['states']}
    return ('Schreibe eine neue deutsche Comic-Geschichte für '+str(value['count'])+' Kacheln.\n'
        'Titel: '+value['title']+'\nBildstil: '+value['style']+'\n'+context({'series':meta})+
        '\nFIGUREN:\n'+json.dumps([{k:c.get(k,'') for k in ('id','name','description','outfit','backstory','personality','motivation','alignment')} for c in p['characters']],ensure_ascii=False)+
        '\nSchreibe eine neue Folge mit eigenem Anfang, Entwicklung und Abschluss oder bewusstem Cliffhanger. '
        'Wiederhole nicht die bisherige Folge. Dialoge eindeutig mit Figurennamen zuordnen. '
        'Alle Erzählertexte und Dialoge auf Deutsch. Dies ist ein Schreibauftrag, keine Behauptung über eine historische Originalfortsetzung.')


def preview(stories,value):
    base,values=get_context(stories,value)
    return {'settings':values,'based_on_title':base['title'],'characters':[{'id':c['id'],'name':c['name']} for c in base['payload']['characters']],'previous_article':base['payload'].get('article',''),'writing_prompt':prompt(base,values)}


def create(stories,value):
    base,values=get_context(stories,value);p=base['payload'];previous=p.get('series',{});root=previous.get('id') or base['root_id']
    if base['kind']=='story' and values.get('base_version')!=base['version']:raise Conflict('Basisversion fehlt oder wurde geändert. Basis neu laden.')
    for item in stories.list():
        meta=item.get('series') or {}
        if meta.get('id')==root and meta['episode']==values['episode']:raise Conflict('Diese Folgennummer existiert bereits. Basis neu laden oder eine andere Nummer wählen.')
    meta={'id':root,'name':values['name'],'episode':values['episode'],'mode':values['mode'],
          'based_on':{k:base[k] for k in ('kind','id','version','title')},'canon':values['canon'],'open_threads':values['open_threads'],
          'previous_article':p.get('article',''),'previous_ending':copy.deepcopy(p.get('scenes',[])[-3:]),'initial_states':base['states']}
    if values['mode']=='direct':meta['initial_continuity_state']=copy.deepcopy(base.get('physical_states',{}))
    inherited={k:copy.deepcopy(p[k]) for k in ('page_template','characters','library_ids','signature','narrator_badge','narrator_character_id','book_author','source_provenance') if k in p}
    payload={**inherited,'style':values['style'],'seed':p.get('seed',1984),'article':values['article'],'scenes':[],'panel_count':values['count'],'planned_article':'','planned_count':0,'revisions':{},'series':meta}
    return stories.save({'mode':'editorial','name':values['title'],'payload':payload})


def validate(meta):
    if not isinstance(meta,dict):raise ValueError('Ungültige Serienangaben.')
    if not meta:return
    if not isinstance(meta.get('id'),str) or not ID.fullmatch(meta['id']):raise ValueError('Ungültige Serien-ID.')
    for key,limit in [('name',200),('canon',6000),('open_threads',4000),('previous_article',16000)]:
        if not isinstance(meta.get(key),str) or len(meta[key])>limit:raise ValueError('Ungültiges Serienfeld: '+key)
    if not meta['name'].strip() or type(meta.get('episode')) is not int or meta['episode']<2 or meta.get('mode') not in ('direct','universe'):raise ValueError('Ungültige Serienfolge.')
    based=meta.get('based_on')
    if not isinstance(based,dict) or based.get('kind') not in ('story','job') or not isinstance(based.get('id'),str) or not ID.fullmatch(based['id']) or not isinstance(based.get('title'),str):raise ValueError('Ungültige Basis der Serienfolge.')
    states=meta.get('initial_states',{})
    if not isinstance(states,dict) or any(not isinstance(k,str) or not ID.fullmatch(k) or not isinstance(v,str) or len(v)>1000 for k,v in states.items()):raise ValueError('Ungültige Figuren-Zustände der Serie.')
    if not isinstance(meta.get('initial_continuity_state',{}),dict) or any(not isinstance(k,str) or not ID.fullmatch(k) for k in meta.get('initial_continuity_state',{})):raise ValueError('Ungültige Figuren-ID in physischen Anfangszuständen.')
    from continuity import check_initial
    check_initial(meta.get('initial_continuity_state',{}),[{'id':i} for i in set(states)|set(meta.get('initial_continuity_state',{}))])
    ending=meta.get('previous_ending',[])
    if not isinstance(ending,list) or len(ending)>3 or any(not isinstance(s,dict) for s in ending):raise ValueError('Ungültiger Schluss der vorigen Folge.')
