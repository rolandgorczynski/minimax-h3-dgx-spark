"""Originalzitate vor der Szenenplanung sichern und unverändert als Sprechblasen setzen."""
import copy
from bisect import bisect_right
import json
import re

QUOTES=re.compile(r'„([^“”\n]+)[“”]|“([^”\n]+)”|»([^«\n]+)«|«([^»\n]+)»|"([^"\n]+)"')
VERBS=r'(?:sagt(?:e)?|fragt(?:e)?|antwortet(?:e)?|entgegnet(?:e)?|ruft|rief|schreit|schrie|flüstert(?:e)?|erwidert(?:e)?|meint(?:e)?|grinst(?:e)?)'


def quotes(article,cast):
    result=[]
    names={n.casefold():c['id'] for c in cast for n in [c['name'],*c.get('aliases',[])]}
    for index,match in enumerate(QUOTES.finditer(article)):
        text=next(g for g in match.groups() if g is not None).strip()
        before=article[max(0,match.start()-180):match.start()];after=article[match.end():match.end()+180]
        speaker=''
        for name,ident in sorted(names.items(),key=lambda x:-len(x[0])):
            n=re.escape(name)
            direct=re.search(r'(?<!\w)'+n+r'\s*:\s*$',before,re.I)
            prefix=re.search(r'(?<!\w)(?:'+VERBS+r'\s+'+n+r'|'+n+r'\s+'+VERBS+r')[^.!?\n“”„"]{0,60}:\s*$',before,re.I)
            suffix=re.match(r'\s*[,!?]?\s*'+VERBS+r'\s+'+n+r'(?!\w)',after,re.I)
            if direct or prefix or suffix:speaker=ident;break
        uncertain=bool(re.search(r'(?:etwas|so etwas)\s+wie\s*$',before,re.I) or re.search(r'[“”]\s+oder\s*$',before,re.I))
        result.append({'id':f'q{index+1:03}','text':text,'start':match.start(),'end':match.end(),
                       'speaker':speaker,'kind':'uncertain' if uncertain else 'spoken' if speaker else 'unresolved',
                       'context':before[-140:]+match.group()+after[:140]})
    for line in re.finditer(r'(?m)^[ \t]*(?:[-*] )?([^:\n]{1,100}):[ \t]*(.+)$',article):
        speaker=names.get(line.group(1).strip().casefold())
        if speaker and not QUOTES.search(line.group(2)):
            result.append({'text':line.group(2).strip(),'start':line.start(),'end':line.end(),'speaker':speaker,'kind':'spoken','context':line.group()})
    result.sort(key=lambda q:q['start'])
    for index,item in enumerate(result):item['id']=f'q{index+1:03}'
    return result


def collect(engine,job,article,cast):
    ledger=quotes(article,cast);unresolved=[q for q in ledger if q['kind']=='unresolved']
    if unresolved:
        known={c['id'] for c in cast};wanted={q['id'] for q in unresolved}
        def validate(value):
            items=value.get('quotes') if isinstance(value,dict) else None
            if not isinstance(items,list) or len(items)!=len(wanted):raise ValueError('Jedes offene Zitat genau einmal zuordnen.')
            seen=set()
            for item in items:
                if not isinstance(item,dict) or item.get('id') not in wanted or item['id'] in seen:raise ValueError('Ungültige oder doppelte Zitat-ID.')
                seen.add(item['id'])
                if item.get('kind') not in ('spoken','term','thought','written','uncertain'):raise ValueError('Zitatart fehlt.')
                if item['kind']=='spoken' and item.get('speaker') not in known:raise ValueError('Gesprochenes Zitat benötigt eine bekannte Sprecher-ID.')
                if not isinstance(item.get('reason'),str) or not item['reason'].strip() or len(item['reason'])>400:raise ValueError('Kurze Begründung der Sprecherzuordnung erforderlich.')
            return items
        assignments=engine.json_call(job,'article-dialogue',
            'Analysiere ausschließlich die wörtlichen Zitate des deutschen Ausgangstextes. Keine Geschichte schreiben und keine Zitate ändern. '
            'Für jede offene Zitat-ID entscheiden: spoken = tatsächlich gesprochene Worte, term = zitierter Begriff, '
            'thought = nur Gedanke, written = geschriebener Text, uncertain = Sprecher oder Wortlaut nicht sicher. '
            'Direkte Rede in Gesprächen ist spoken, auch wenn der Sprecher im benachbarten Satz genannt wird. '
            'Die Ich-Erzählperson kann selbst sprechen; Ich-Erzählung außerhalb der Anführungszeichen ist keine Sprechblase. '
            'Antworten anhand des Gesprächskontexts zuordnen. Nicht einfach jedes Zitat der zuletzt genannten Person zuschreiben. '
            'Bei unbelegtem Sprecher uncertain wählen, keine Figur erfinden. Zitate wie „abgelehnt“ sind nicht automatisch Gespräche. '
            'Vorgegebene eindeutige Zuordnungen bleiben erhalten. '
            'Return ONLY JSON {"quotes":[{"id":"offene Zitat-ID","kind":"spoken","speaker":"Figuren-ID oder leer","reason":"kurze Begründung auf Deutsch"}]}. '
            '\nFIGUREN:'+json.dumps([{'id':c['id'],'name':c['name'],'aliases':c.get('aliases',[])} for c in cast],ensure_ascii=False)+
            '\nOFFENE ZITATE:'+json.dumps(unresolved,ensure_ascii=False)+
            '\nBEREITS ZUGEORDNET:'+json.dumps([q for q in ledger if q not in unresolved],ensure_ascii=False)+
            '\nAUSGANGSTEXT:'+article,validate,tokens=min(8000,200+len(unresolved)*110))
        by_id={q['id']:q for q in ledger}
        for item in assignments:
            q=by_id[item['id']];q['kind']=item['kind'];q['speaker']=item.get('speaker','') if item['kind']=='spoken' else '';q['reason']=item['reason']
    engine.store.write(job,'dialogue-ledger.json',ledger)
    return ledger


def fragments(text,limit=64):
    """An Wortgrenzen teilen; keine Auslassung, Umformulierung oder Ellipse ergänzen."""
    result=[];rest=text.strip()
    while len(rest)>limit:
        cut=rest.rfind(' ',0,limit+1)
        if cut<1:cut=rest.find(' ',limit)
        if cut<1:cut=len(rest)
        result.append(rest[:cut]);rest=rest[cut:].lstrip()
    if rest:result.append(rest)
    return result


def clean_caption(caption,bubbles,cast):
    normalize=lambda s:''.join(c for c in s.casefold() if c.isalnum())
    texts={normalize(b['text']) for b in bubbles}
    prefixes=[normalize(name) for c in cast for name in [c['name'],*c.get('aliases',[])]]
    if normalize(caption) in {name+text for name in prefixes for text in texts}:return ''
    if normalize(caption) in texts or (bubbles and normalize(caption)==normalize(' '.join(b['text'] for b in bubbles))):return ''
    changed=False
    for bubble in bubbles:
        text=bubble['text']
        if len(text)>=4 and text in caption:
            caption=re.sub(r'[„“«»"]?'+re.escape(text)+r'[“”«»"]?', '',caption)
            changed=True
    if not changed:return caption
    caption=caption.strip().lstrip('.,:;!?–—- ').strip()
    names='|'.join(re.escape(name) for c in cast for name in [c['name'],*c.get('aliases',[])])
    if names and re.fullmatch(r'(?:'+names+r')(?:\s+'+VERBS+r')?[:.,!?\s]*',caption,re.I):return ''
    return caption



def sections(article,ledger,count):
    """Chronologische Quellabschnitte festlegen, ohne Anführungszeichen aufzutrennen."""
    spoken=[q for q in ledger if q['kind']=='spoken']
    candidates=[0]+[m.end() for m in re.finditer(r'\s+',article) if not any(q['start']<m.end()<q['end'] for q in ledger)]+[len(article)]
    candidates=sorted(set(candidates))
    if len(candidates)<count+1:raise ValueError('Zu wenig Textabschnitte für diese Kachelanzahl. Bitte weniger Kacheln wählen.')
    weight=lambda pos:pos+sum(250*len(fragments(q['text'])) for q in spoken if q['end']<=pos)
    weights={p:weight(p) for p in candidates}
    penalty=lambda p:0 if article[:p].endswith('\n\n') else 40 if article[:p].rstrip().endswith(('.', '!', '?', '“', '”', '«', '»')) else 140
    total=weights[len(article)];cuts=[0]
    for index in range(1,count):
        remaining=count-index
        available=candidates[bisect_right(candidates,cuts[-1]):len(candidates)-remaining]
        cuts.append(min(available,key=lambda p:(abs(weights[p]-total*index/count)+penalty(p),-p)))
    cuts.append(len(article))
    return [{'panel':i+1,'start':a,'end':b,'source_excerpt':article[a:b].strip(),
             'quote_ids':[q['id'] for q in spoken if a<=q['start']<b]} for i,(a,b) in enumerate(zip(cuts,cuts[1:]))]


def apply_sections(value,ledger,cast,locked):
    if not isinstance(value,list) or len(value)!=len(locked):raise ValueError('Für jeden Quellabschnitt genau eine Szene liefern.')
    prepared=copy.deepcopy(value)
    for scene,section in zip(prepared,locked):
        if not isinstance(scene,dict):raise ValueError('Ungültige Szene.')
        # Das Modell besitzt keine Schreibhoheit über Zitate oder ihre Reihenfolge.
        scene['quote_ids']=section['quote_ids'][:]
        scene['source_start']=section['start'];scene['source_end']=section['end']
        scene['dialog']=clean_caption(scene.get('dialog',''),
            [{'text':q['text']} for q in ledger],cast)
    return apply(prepared,ledger,cast)


def apply(value,ledger,cast):
    """Das Modell ordnet Zitat-IDs Kacheln zu; Text und Sprecher kommen aus der Liste."""
    if not isinstance(value,list):raise ValueError('Szenen als Liste senden.')
    spoken={q['id']:q for q in ledger if q['kind']=='spoken'};expected=list(spoken);seen=[];result=copy.deepcopy(value)
    for scene in result:
        if not isinstance(scene,dict):raise ValueError('Ungültige Szene.')
        ids=scene.get('quote_ids',[])
        if not isinstance(ids,list) or any(not isinstance(q,str) or q not in spoken for q in ids):raise ValueError('Nur gesprochene Zitat-IDs als Sprechblasen verwenden.')
        bubbles=[]
        for ident in ids:
            if ident in seen:raise ValueError('Zitat '+ident+' wird mehrfach verwendet.')
            seen.append(ident);q=spoken[ident]
            bubbles.extend({'speaker':q['speaker'],'text':part,'expression':'normal','source_quote_id':ident} for part in fragments(q['text']))
        if len(bubbles)>6:raise ValueError('Zu viele Gesprächsteile in einer Kachel. Auf mehrere Kacheln verteilen.')
        speakers=list(dict.fromkeys(b['speaker'] for b in bubbles));rows=[0,0]
        for bubble in bubbles:
            column=speakers.index(bubble['speaker'])%2;row=rows[column];rows[column]+=1
            if row>=3:raise ValueError('Mehr als drei Sprechblasen einer Bildseite: Gespräch auf mehrere Kacheln verteilen.')
            bubble.update(x=.04+column*.49,y=.25+row*.24,w=.43,h=.22,tip_x=.25+column*.5,tip_y=min(.97,.50+row*.22))
        scene['bubbles']=bubbles
        visible=scene.get('characters',[])
        if not isinstance(visible,list):raise ValueError('Sichtbare Figuren als Liste senden.')
        scene['characters']=list(dict.fromkeys(visible+[b['speaker'] for b in bubbles]))
        scene['dialog']=clean_caption(scene.get('dialog',''),bubbles,cast)
    missing=[q for q in expected if q not in seen]
    if missing:raise ValueError('Originalgespräche fehlen in den Sprechblasen: '+', '.join(missing)+'. Jedes gesprochene Zitat genau einmal verteilen.')
    if seen!=expected:raise ValueError('Originalgespräche müssen in der Reihenfolge des Ausgangstextes bleiben.')
    return result
