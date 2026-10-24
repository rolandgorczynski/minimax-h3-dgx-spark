"""Belegte Widersprüche und optionale Stilkritik im Experiment getrennt prüfen."""
import copy
import json

BLOCKING={'image_text_conflict','sequence','identity','speaker','continuity','ending','readability'}
ADVICE={'style','redundancy','intensity','missing_annotation','preference'}


def validate_review(value,scenes,start):
    if not isinstance(value,dict) or not isinstance(value.get('issues'),list) or not isinstance(value.get('suggestions',[]),list):raise ValueError('Prüfung mit issues und suggestions als Listen erforderlich.')
    blocking=[];suggestions=[]
    for item in value.get('suggestions',[]):
        if not isinstance(item,str) or not item.strip() or len(item)>2000:raise ValueError('Stilhinweise als kurze Texte angeben.')
        suggestions.append(item)
    for item in value['issues']:
        if not isinstance(item,dict):raise ValueError('Jeder Befund braucht panel, kind, message und konkrete Belege.')
        panel=item.get('panel');kind=item.get('kind');message=item.get('message')
        if type(panel) is not int or not start+1<=panel<=start+len(scenes):raise ValueError('Befund betrifft eine Kachel außerhalb des geprüften Abschnitts.')
        if not isinstance(kind,str) or kind not in BLOCKING|ADVICE or not isinstance(message,str) or not message.strip() or len(message)>2000:raise ValueError('Konkreten Befundtyp und eine kurze Begründung angeben.')
        scene=scenes[panel-start-1]
        if kind in ADVICE:
            suggestions.append(f'Kachel {panel}: {message}');continue
        if kind=='speaker' and not scene.get('bubbles'):
            suggestions.append(f'Kachel {panel}: Kein Sprecherfehler belegbar, da keine Sprechblasen vorhanden sind. {message}');continue
        image_quote=item.get('image_quote');text_quote=item.get('text_quote','')
        if not isinstance(image_quote,str) or not image_quote.strip() or image_quote not in scene['story']:
            suggestions.append(f'Kachel {panel}: Unbelegter Prüfhinweis (Bildzitat fehlt oder stimmt nicht): {message}');continue
        if kind=='image_text_conflict':
            texts=[scene.get('dialog','')]+[b['text'] for b in scene.get('bubbles',[])]
            if not isinstance(text_quote,str) or not text_quote.strip() or not any(text_quote in text for text in texts):
                suggestions.append(f'Kachel {panel}: Unbelegter Prüfhinweis (Textzitat fehlt oder stimmt nicht): {message}');continue
        blocking.append({'panel':panel,'kind':kind,'message':message,'image_quote':image_quote,'text_quote':text_quote})
    return {'approved':not blocking,'issues':blocking,'suggestions':list(dict.fromkeys(suggestions))}


def assess(engine,ident,step,scenes,start,total,settings,guide,previous,originals,cast):
    scope=('MODUS NUR BILDKOMPOSITION: Handlung, Erzählertexte, Wortlaut und Sprecher sind unveränderlich. '
        'Ein erklärender oder redundanter Originaltext ist KEIN Abbruchgrund. Intensitätsregler, Vorbild und Beatplan sind nachrangig. '
        'Bei Konflikt muss die neue Bildbeschreibung an den festen Text und dessen Zeitpunkt angepasst werden, nicht umgekehrt. '
        if settings['mode']=='staging' else
        'MODUS FREIE DRAMATURGIE: Neue Dialoge und vorbereitete Wendungen sind erlaubt. Stilhinweise sind keine logischen Widersprüche. ')
    keys=('story','dialog','characters','bubbles','character_states')
    checked=[{'panel':start+i+1,**{k:s.get(k) for k in keys}} for i,s in enumerate(scenes)]
    if settings['mode']=='staging':
        for current,original in zip(checked,originals):current['original_action']=original['story']
    context='' if settings['mode']=='staging' else '\nREGIEPLAN (nachrangig):'+json.dumps(guide,ensure_ascii=False)+'\nORIGINALSZENEN:'+json.dumps(originals,ensure_ascii=False)
    prompt=(scope+'\nUnterscheide belegbare Fehler von optionalen Verbesserungen. Das Feld dialog ist ein Erzählerkasten, keine gesprochene Äußerung. '
        'characters nennt sichtbare Figuren, bubbles nennt gesprochene Worte. Eine Figur darf sichtbar sein und schweigen. '
        'Leere character_states sind kein Fehler; unverändertes Aussehen und Kleidung folgen den Figurenprofilen. '
        'Beanstande nur explizite Widersprüche, keine bloß fehlenden Annotationen. '
        'Jede Kachel trägt ihre verbindliche globale panel-Nummer. Ordne keine Texte einer anderen Kachel zu. '
        'original_action ist die Handlungsvorlage, KEIN Erzählertext. Nur dialog und bubbles sind feste sichtbare Texte. '
        'Eine Abfolge Kampf in Kachel 3/4 und Sieg in Kachel 5 ist logisch und kein Widerspruch. '
        'Untersuche Zeitpunkt und Ursache/Wirkung: Bei einem Text über einen bereits beendeten Kampf muss das Bild den beendeten Kampf zeigen. '
        'Prüfe Identitäten, Sprecher und die Kontinuität tatsächlicher Ereignisse. Stilurteile wie mehr Subtext, stärkere Spannung, '
        'mehr Intensität oder redundanter Erzählertext kommen nur in suggestions. '
        'Return ONLY JSON {"issues":[{"panel":1,"kind":"image_text_conflict oder sequence oder identity oder speaker oder continuity oder ending oder readability",'
        '"message":"konkreter Widerspruch","image_quote":"wörtliches Fragment aus story dieser Kachel","text_quote":"bei Bild-Text-Konflikt wörtliches Fragment aus dialog oder bubbles"}],'
        '"suggestions":["optionaler Stilhinweis"]}. Ohne belegte Fehler issues leer lassen. '
        '\nFIGUREN:'+json.dumps([{k:c.get(k,'') for k in ('id','name','description','outfit')} for c in cast],ensure_ascii=False)+
        context+
        '\nBISHERIGE NEUE SZENEN:'+json.dumps([{k:s.get(k) for k in keys} for s in previous[-2:]],ensure_ascii=False)+
        '\nGEPRÜFTER ABSCHNITT '+str(start+1)+' bis '+str(start+len(scenes))+' von '+str(total)+': '+json.dumps(checked,ensure_ascii=False))
    return engine.json_call(ident,step,prompt,lambda v:validate_review(v,scenes,start),tokens=1800)


def repair_staging(engine,ident,scenes,start,issues,cast):
    result=copy.deepcopy(scenes)
    for panel in sorted({i['panel'] for i in issues}):
        index=panel-start-1;before=result[index];findings=[i for i in issues if i['panel']==panel]
        def check(value):
            if not isinstance(value,dict) or set(value)-{'story','character_states'} or not isinstance(value.get('story'),str) or not value['story'].strip() or len(value['story'])>1200:raise ValueError('Nur die vollständige Bildbeschreibung und gegebenenfalls Figurenzustände korrigieren.')
            candidate={**before,'story':value['story']};engine.validate_scenes([candidate],1,cast);return {'story':value['story']}
        fixed=engine.json_call(ident,'experiment-locked-image-repair-'+str(panel),
            'Korrigiere ausschließlich das Bild dieser Comic-Kachel. Die festen Texte, Sprecher und Handlung sind verbindlich. '
            'Der visuelle Zeitpunkt muss zu den festen Texten passen: Nach dem Sieg keinen noch laufenden Kampf zeigen. '
            'Unpassende Regieideen und Action-Vorgaben verwerfen. Keine neue Handlung oder Dialoge erfinden. '
            'Zeige alle in characters genannten Figuren; ein besiegtes Wesen bleibt entsprechend reglos. '
            'Bestehende Figurenzustände erhalten, solange kein belegter Widerspruch vorliegt. '
            'Return ONLY JSON {"story":"vollständige, eindeutige Bildbeschreibung auf Deutsch"}. '
            '\nKACHEL:'+str(panel)+'\nFESTER ERZÄHLERTEXT:'+before.get('dialog','')+
            '\nFESTE SPRECHBLASEN:'+json.dumps(before.get('bubbles',[]),ensure_ascii=False)+
            '\nAKTUELLE SZENE:'+json.dumps(before,ensure_ascii=False)+'\nBELEGTE FEHLER:'+json.dumps(findings,ensure_ascii=False)+
            '\nFIGUREN:'+json.dumps([{k:c.get(k,'') for k in ('id','name','description','outfit')} for c in cast],ensure_ascii=False),check,tokens=1300)
        result[index]['story']=fixed['story']
        # Figuren-Zustände bleiben unverändert; die gezielte Korrektur betrifft nur das Bild.
    return result


def align_locked_texts(engine,ident,scenes,start,cast,original_scenes=None):
    """Festen Wortlaut vor Regiestil priorisieren, ohne auf ein negatives Kritikerurteil zu warten."""
    originals=copy.deepcopy(scenes)
    anchors=[{k:s.get(k,{} if k=='character_states' else [] if k in ('characters','bubbles') else '') for k in ('setting','dialog','characters','bubbles','character_states')} for s in scenes]
    if original_scenes is not None:
        if len(original_scenes)!=len(scenes):raise ValueError('Originalabschnitt und neue Kacheln müssen gleich lang sein.')
        for anchor,original in zip(anchors,original_scenes):anchor['original_action']=original['story']
    def check(value):
        if not isinstance(value,list) or len(value)!=len(scenes):raise ValueError('Für jede Kachel genau eine Bildbeschreibung liefern.')
        fixed=copy.deepcopy(originals)
        for i,item in enumerate(value):
            if not isinstance(item,dict) or set(item)-{'panel','story','character_states'} or type(item.get('panel')) is not int or item['panel']!=start+i+1:raise ValueError('Alle Kachelnummern in derselben Reihenfolge übernehmen.')
            if not isinstance(item.get('story'),str) or not item['story'].strip() or len(item['story'])>1200:raise ValueError('Vollständige Bildbeschreibung mit maximal 1200 Zeichen erforderlich.')
            fixed[i]['story']=item['story']
            # Unangeforderte Modellmetadaten werden nicht auf die gesicherten Zustände angewendet.
        return engine.validate_scenes(fixed,len(fixed),cast)
    return engine.json_call(ident,'experiment-locked-text-alignment-'+str(start+1),
        'Du führst einen eigenständigen Bild-Text-Abgleich für ein Comic-Experiment mit unveränderlichem Text durch. '
        'Die Felder dialog (Erzählerkasten) und bubbles (gesprochene Worte) bestimmen den gezeigten Inhalt und Zeitpunkt. '
        'Entwirf JEDE Bildbeschreibung von Grund auf aus diesen festen Texten. Zeige genau EINEN gleichzeitigen Moment pro Bild. '
        'Keine zeitliche Montage, keine Folge mehrerer Aktionen und kein Angriff mit anschließendem Sieg im selben Bild. '
        'Das Ortsfeld setting kann einen falschen Zeitpunkt enthalten: Übernimm daraus nur den Ort, der feste Text bestimmt den Zeitpunkt. Ein bereits bezwungener Gegner '
        'liegt besiegt oder reglos; er greift nicht im selben Moment weiter an. Ein Satz über die Stille NACH dem Kampf '
        'verlangt ein Bild nach dem Kampf. Steht eine Figur laut Text vor einem Wesen, muss dessen Anwesenheit sichtbar sein. '
        'Eine sichtbare Figur darf schweigen. Das Fehlen einer Sprechblase oder einer erneuten Kleidungsbeschreibung ist kein Fehler. '
        'Konkrete feste Texte haben Vorrang vor Action, Vorbild und Regieplan. Keine neuen Ereignisse oder Fähigkeiten. '
        'original_action enthält die verbindliche ORIGINALHANDLUNG vor dem Experiment: Erhalte deren Ereignisse, Gegenstände und Ortswechsel. '
        'Figuren, Anzahl und Reihenfolge erhalten. Neue Kamera, Licht und Bildwirkung entwerfen, keine fehlerhafte Experimentkomposition übernehmen. '
        'Erhalte eine passende starke Kamera- und Lichtgestaltung, aber entferne unpassende Aktionen. '
        'Return ONLY JSON als Array [{"panel":1,"story":"vollständiges zum festen Text passendes Bild auf Deutsch, höchstens 600 Zeichen"}]. '
        'Nur die Bildbeschreibung liefern, keine neuen Texte und keine neuen Figuren-Zustandsfelder. Gesicherte Identitäten und vorhandene Zustände bleiben erhalten. '
        '\nFESTE KACHELNUMMERN:'+json.dumps(list(range(start+1,start+len(scenes)+1)))+
        '\nKACHELN MIT FESTEN TEXTEN:'+json.dumps(anchors,ensure_ascii=False)+
        '\nFIGUREN:'+json.dumps([{k:c.get(k,'') for k in ('id','name','description','outfit')} for c in cast],ensure_ascii=False),check,tokens=450*len(scenes)+300)
