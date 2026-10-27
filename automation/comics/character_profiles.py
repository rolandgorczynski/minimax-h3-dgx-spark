"""Bearbeitbare Figurenangaben für Storyboards und die gemeinsame Bibliothek."""
import copy
import json
import secrets
import uuid
ALIGNMENTS = {
    '': 'Nicht festgelegt',
    'lawful_good': 'Rechtschaffen gut', 'neutral_good': 'Neutral gut', 'chaotic_good': 'Chaotisch gut',
    'lawful_neutral': 'Rechtschaffen neutral', 'true_neutral': 'Neutral', 'chaotic_neutral': 'Chaotisch neutral',
    'lawful_evil': 'Rechtschaffen böse', 'neutral_evil': 'Neutral böse', 'chaotic_evil': 'Chaotisch böse',
}
LIMITS = {'name':100, 'description':2500, 'outfit':1000, 'backstory':2500, 'personality':1200, 'motivation':1200}


def validate(profile):
    if not isinstance(profile,dict):raise ValueError('Ungültiges Figurenprofil.')
    for key,limit in LIMITS.items():
        if not isinstance(profile.get(key,''),str):
            raise ValueError(f'{key}: Text erwartet, kein null oder anderer Datentyp.')
        if len(profile.get(key,''))>limit:
            raise ValueError(f'{key}: maximal {limit} Zeichen.')
    alignment=profile.get('alignment','')
    if not isinstance(alignment,str) or alignment not in ALIGNMENTS:raise ValueError('Unbekannte Gesinnung.')
    return profile


def narrative(profile):
    """Nur ausdrücklich festgelegte Angaben an die Szenenplanung weitergeben."""
    result={k:profile.get(k,'') for k in ('id',*LIMITS)}
    if profile.get('alignment'):result['alignment']=ALIGNMENTS[profile['alignment']]
    return result


def enqueue(store,value):
    from engine import ID, validate_request
    if not isinstance(value,dict) or set(value)-{'profile','style','determine_alignment','portrait_only'}:raise ValueError('Ungültige Figurenanfrage.')
    profile=validate(value.get('profile'))
    if not isinstance(profile.get('id'),str) or not ID.fullmatch(profile.get('id','')) or not profile.get('name','').strip():raise ValueError('Figuren-ID und Name erforderlich.')
    portrait_only=value.get('portrait_only',False)
    if type(portrait_only) is not bool:raise ValueError('Porträtmodus muss wahr oder falsch sein.')
    determine=value.get('determine_alignment',True)
    if type(determine) is not bool:raise ValueError('Gesinnungsauswahl muss wahr oder falsch sein.')
    req=validate_request({'kacheln':1,'stil':value.get('style'),'seed':secrets.randbelow(2147483648),'max_korrekturrunden':0})
    ident=uuid.uuid4().hex
    store.create(ident,req,initial_status='editing')
    store.write(ident,'character-source.json',{'profile':profile,'determine_alignment':determine,'portrait_only':portrait_only})
    store.update(ident,character_mode=True)
    store.stage(ident,'queued',status='queued')
    return {'id':ident,'status':'queued'}


def regenerate(engine,ident):
    source=json.loads((engine.store.directory(ident)/'character-source.json').read_text())
    original=source['profile'];determine=source['determine_alignment']
    if source.get('portrait_only'):
        profile=copy.deepcopy(original)
        engine.store.stage(ident,'character_portrait')
        profile['inline_references']=[engine.portrait(ident,profile,0,engine.store.get(ident)['request']['stil'])]
        profile['references']=[]
        engine.store.write(ident,'character-result.json',profile)
        return {'status':'completed','artifacts':[]}
    engine.store.stage(ident,'character_appearance')
    def check(value):
        if not isinstance(value,dict) or not isinstance(value.get('description'),str) or not value['description'].strip() or len(value['description'])>2500:
            raise ValueError('Eine konkrete Beschreibung des Aussehens erforderlich.')
        alignment=value.get('alignment','') if determine else ''
        if not isinstance(alignment,str) or alignment not in ALIGNMENTS or (determine and not alignment):raise ValueError('Eine gültige Gesinnung auswählen.')
        return {'description':value['description'].strip(),'alignment':alignment}
    prompt=('Entwirf ausschließlich ein neues, interessantes Aussehen für diese Comicfigur. '
        'Name, Identität, Vorgeschichte, Persönlichkeit, Motivation und Kleidung bleiben bestehen. '
        'Beachte ausdrücklich festgelegtes Alter und andere biografische Tatsachen. Keine neue Handlung erfinden. '
        'Die Beschreibung muss auf Deutsch sein und Gesicht, Haare, Statur sowie erkennbare Merkmale konkret beschreiben. '
        +('Wähle außerdem genau eine passende RPG-Gesinnung aus '+json.dumps([k for k in ALIGNMENTS if k])+'. ' if determine else 'Die Gesinnung bleibt ausdrücklich nicht festgelegt (leere Zeichenkette). ')
        +'Return ONLY JSON {"description":"Neues Aussehen auf Deutsch","alignment":"Kennung oder leere Zeichenkette"}. '
        +'FIGUR: '+json.dumps(narrative(original),ensure_ascii=False))
    changes=engine.json_call(ident,'character-appearance',prompt,check,tokens=1100)
    profile=copy.deepcopy(original);profile.update(changes)
    engine.store.stage(ident,'character_portrait')
    profile['inline_references']=[engine.portrait(ident,profile,0,engine.store.get(ident)['request']['stil'])]
    profile['references']=[]
    engine.store.write(ident,'character-result.json',profile)
    return {'status':'completed','artifacts':[]}
