"""Quellenbelegte Zustandsführung vor der Bilderzeugung, ausschließlich lokale LLMs."""
import copy
import json
import re

FIELDS={'movement','mount','posture','location','held','injury','life','clothing'}
LABELS={'movement':'Fortbewegung','mount':'Reittier / Fahrzeug','posture':'Körperhaltung','location':'Ort','held':'Mitgeführte Gegenstände','injury':'Verletzungen','life':'Lebenszustand','clothing':'Kleidung'}
MOVEMENT={'beritten','zu Fuß','in einem Fahrzeug','fliegend','schwimmend'}
RULES=('Zustände gelten weiter, auch bei Schweigen oder vorübergehender Abwesenheit. Fehlende Angabe bedeutet KEINE Änderung. '
       'Wer beritten ankommt, bleibt beim Gespräch im Sattel, solange die Quelle kein Absteigen nennt. '
       'Gegenüberstehen ist eine räumliche Beziehung und kein Beleg für Absteigen. Nicht eigenständig Übergangshandlungen erfinden. '
       'Bei Gesprächen zwischen Reiter und Fußgänger den Höhenunterschied nennen. '
       'Waffen, Gegenstände, Verletzungen, Lebenszustand, Kleidung und Ort ebenso zeitlich korrekt fortführen. '
       'Ein bereits besiegter oder toter Gegner greift nicht wieder an. Ein Bild zeigt genau einen Zeitpunkt. ')


def state_text(state):return '; '.join(LABELS[k]+': '+v for k,v in state.items() if k!='mount' or state.get('movement')!='zu Fuß')


def track(value,scenes,cast,start,source,initial,anchors=None):
    if not isinstance(value,dict) or set(value)!={'events'} or not isinstance(value['events'],list):raise ValueError('Nur events als Liste liefern.')
    known={c['id'] for c in cast};events=copy.deepcopy(value['events']);state=copy.deepcopy(initial);per_panel=[];previous=start
    seen=set()
    for event in events:
        if not isinstance(event,dict) or set(event)!={'panel','character','field','value','evidence'}:raise ValueError('Jeder Zustandswechsel braucht panel, character, field, value und evidence.')
        panel=event['panel'];ident=event['character'];field=event['field'];text=event['value'];evidence=event['evidence']
        if type(panel) is not int or not start+1<=panel<=start+len(scenes) or panel<previous:raise ValueError('Zustandsereignisse in aufsteigender Kachelreihenfolge angeben.')
        previous=panel
        if not isinstance(ident,str) or ident not in known or not isinstance(field,str) or field not in FIELDS or not isinstance(text,str) or not text.strip() or len(text)>180:raise ValueError('Bekannte Figuren-ID, gültiges Zustandsfeld und höchstens 180 Zeichen je Wert erforderlich.')
        allowed=anchors[panel-start-1] if anchors is not None else source
        if not isinstance(evidence,str) or not evidence.strip() or evidence not in allowed:raise ValueError('Zustandsänderungen müssen wörtlich in der zugehörigen Textgrundlage belegt sein, nicht nur im Bildentwurf.')
        if field=='movement':
            if text not in MOVEMENT:raise ValueError('Fortbewegung: beritten, zu Fuß, in einem Fahrzeug, fliegend oder schwimmend.')
            if text=='beritten' and not re.search(r'\breit\w*|\bgeritten\b|\bangeritten\b|\bsattel\b|\bpferd\w*|\bro[sß]s\b',evidence,re.I):raise ValueError('Beritten braucht einen eindeutigen Reitbeleg.')
            if text=='zu Fuß' and not re.search(r'absteig\w*|steig\w*[^.!?]{0,55}\bab\b|abgestiegen|stieg[^.!?]{0,55}\bab\b|zu fu[ßs]|\bgeh\w*|\bging\w*|\bläuft\b|\blauf\w*|\bschreit\w*|\bstapf\w*|\bwandert\b',evidence,re.I):raise ValueError('Steht gegenüber oder spricht belegt kein Absteigen. Vorherige Fortbewegung beibehalten.')
        if field=='mount' and not re.search(r'pferd|sattel|ross|roß|wagen|fahrzeug|auto|boot|kutsche|esel|muli|kamel|reit',evidence,re.I):raise ValueError('Reittier oder Fahrzeug braucht einen eindeutigen Quellenbeleg.')
        # Zwei unterschiedliche Werte desselben Felds im selben Bild wären eine zeitliche Montage.
        identity=(panel,ident,field)
        if identity in seen:raise ValueError('Je Kachel und Figur nur ein Wert pro Zustandsfeld.')
        seen.add(identity)
    cursor=0
    for i,scene in enumerate(scenes):
        while cursor<len(events) and events[cursor]['panel']==start+i+1:
            event=events[cursor];facts=state.setdefault(event['character'],{})
            if event['field']=='movement' and facts.get('movement')!=event['value']:facts.pop('posture',None)
            facts[event['field']]=event['value'];cursor+=1
        for ident,facts in state.items():
            if len(state_text(facts))>850:raise ValueError('Figurenzustände auf höchstens 850 Zeichen verdichten.')
        per_panel.append(copy.deepcopy(state))
    return events,per_panel,state


def check_initial(initial,cast):
    if not isinstance(initial,dict) or set(initial)-{c['id'] for c in cast}:raise ValueError('Ungültige Anfangszustände der Kontinuität.')
    for facts in initial.values():
        if not isinstance(facts,dict) or set(facts)-FIELDS or any(not isinstance(v,str) or not v.strip() or len(v)>180 for v in facts.values()):raise ValueError('Ungültige physische Anfangszustände.')
    return copy.deepcopy(initial)


def enforce(engine,job,scenes,cast,source,initial=None,anchors=None,tag='script'):
    """Originaldialoge erhalten; nur Bildanweisungen korrigieren und Zustände sichtbar festschreiben."""
    state=check_initial(initial or {},cast);result=[];reports=[];discarded=[]
    for start in range(0,len(scenes),6):
        chunk=copy.deepcopy(scenes[start:start+6]);local_anchors=anchors[start:start+len(chunk)] if anchors is not None else None
        engine.store.stage(job,'script_continuity',planned_panels=start,total_panels=len(scenes))
        scope=[{'panel':start+i+1,'source':local_anchors[i],'characters':s['characters']} if local_anchors is not None else {'panel':start+i+1,'fallible_moment_hint':s['story'],'characters':s['characters']} for i,s in enumerate(chunk)]
        prompt=(RULES+'\nErmittle ausschließlich ausdrücklich in der Textgrundlage belegte körperliche Zustände und Änderungen. '
            'Ausschließlich source bzw. TEXTGRUNDLAGE sind Belege. fallible_moment_hint darf nur zur zeitlichen Zuordnung dienen, NIE als Beleg. Bildentwürfe können falsch sein. Erfinde keine Fakten, um sie zu rechtfertigen. Erfasse nur relevante Angaben; unbekannte Felder weglassen. '
            'posture nur für eindeutige Körperhaltung verwenden, nicht für räumliches Gegenüber. Besitz bedeutet nicht automatisch, dass ein Gegenstand in der Hand gehalten wird. '
            'Bei erstmaligem Auftreten einen Zustand setzen, danach nur ausdrücklich geänderte Felder. Zeitpunkte müssen zur jeweiligen Kachel passen. '
            'Wenn der Zustand unverändert ist, kein Ereignis. Kein erneutes Reiten aus einem späteren Satz vorziehen. '
            'Feldnamen: movement, mount, posture, location, held, injury, life, clothing. Werte knapp auf Deutsch, maximal 180 Zeichen. '
            'Bei einer Änderung den neuen vollständigen Feldinhalt angeben, etwa alle weiterhin gehaltenen Gegenstände. '
            'movement nur beritten, zu Fuß, in einem Fahrzeug, fliegend oder schwimmend. evidence ist ein kurzes wörtliches Zitat der Textgrundlage dieser Kachel. '
            'Return ONLY JSON {"events":[{"panel":1,"character":"exakte ID","field":"movement","value":"beritten","evidence":"exaktes zusammenhängendes Zitat aus der Textgrundlage"}]}. '
            'Ereignisse in chronologischer Reihenfolge; bei keinen belegten Angaben events leer lassen. '
            '\nFIGUREN:'+json.dumps([{k:c.get(k,'') for k in ('id','name','aliases')} for c in cast],ensure_ascii=False)+
            ('\nTEXTGRUNDLAGE:'+source if local_anchors is None else '')+'\nANFANGSZUSTÄNDE:'+json.dumps(state,ensure_ascii=False)+'\nNUMMERIERTE KACHELN:'+json.dumps(scope,ensure_ascii=False))
        ignored=[]
        def validate(value):
            if not isinstance(value,dict) or set(value)!={'events'} or not isinstance(value['events'],list):raise ValueError('Nur events als Liste liefern.')
            accepted=[];ignored.clear()
            for event in value['events']:
                try:track({'events':accepted+[event]},chunk,cast,start,source,state,local_anchors)
                except ValueError as exc:
                    if any(text in str(exc) for text in ('wörtlich','kein Absteigen','eindeutigen Reitbeleg','eindeutigen Quellenbeleg')):
                        ignored.append({'event':copy.deepcopy(event),'reason':str(exc)});continue
                    raise
                accepted.append(event)
            return track({'events':accepted},chunk,cast,start,source,state,local_anchors)

        events,expected,following=engine.json_call(job,tag+'-continuity-events-'+str(start+1),prompt,validate,tokens=1800)
        discarded.extend(ignored)
        active=any(any(ident in scene['characters'] for ident in facts) for scene,facts in zip(chunk,expected))
        if active:
            def validate_rewrite(value):
                if not isinstance(value,list) or len(value)!=len(chunk):raise ValueError('Je Kachel genau eine Bildbeschreibung liefern.')
                fixed=copy.deepcopy(chunk)
                for i,item in enumerate(value):
                    if not isinstance(item,dict) or set(item)!={'panel','story'} or item['panel']!=start+i+1 or not isinstance(item['story'],str) or not item['story'].strip() or len(item['story'])>2400:raise ValueError('Kachelnummern erhalten; nur vollständige Bildbeschreibung bis 2400 Zeichen ändern.')
                    fixed[i]['story']=item['story']
                return engine.validate_scenes(fixed,len(fixed),cast)
            rewrite=(RULES+'\nPräzisiere nur die Bildbeschreibungen anhand der verbindlichen Zustände. Keine neuen Ereignisse, keine Änderung von Handlung, Figurenliste, Erzählertext oder Gesprächen. '
                'Jeden relevanten sichtbaren Zustand ausdrücklich in der Bildbeschreibung nennen. Bestehende Widersprüche entfernen, nicht zusätzlich stehen lassen. '
                'Return ONLY JSON [{"panel":1,"story":"vollständige präzise Bildbeschreibung auf Deutsch"}]. '
                '\nFIGUREN:'+json.dumps([{k:c.get(k,'') for k in ('id','name','description','outfit')} for c in cast],ensure_ascii=False)+
                '\nKACHELN:'+json.dumps([{'panel':start+i+1,'scene':s,'required_states':{k:v for k,v in expected[i].items() if k in s['characters']}} for i,s in enumerate(chunk)],ensure_ascii=False))
            chunk=engine.json_call(job,tag+'-continuity-images-'+str(start+1),rewrite,validate_rewrite,tokens=650*len(chunk)+200)
            def validate_review(value):
                if not isinstance(value,dict) or not isinstance(value.get('issues'),list):raise ValueError('Kontinuitätsprüfung mit issues als Liste erforderlich.')
                issues=[]
                for item in value['issues']:
                    if not isinstance(item,dict) or type(item.get('panel')) is not int or not start+1<=item['panel']<=start+len(chunk):raise ValueError('Konkrete Kachel des Kontinuitätsfehlers angeben.')
                    i=item['panel']-start-1;ident=item.get('character');field=item.get('field');quote=item.get('quote');message=item.get('message')
                    if ident not in expected[i] or field not in expected[i][ident]:raise ValueError('Befund muss einen tatsächlich festgeschriebenen Zustand betreffen.')
                    if not isinstance(quote,str) or not quote.strip() or quote not in chunk[i]['story'] or not isinstance(message,str) or not message.strip() or len(message)>1000:raise ValueError('Widerspruch mit wörtlichem Bildbeleg und kurzer Begründung angeben.')
                    issues.append(item)
                return issues
            review_prompt=(RULES+'\nPrüfe die Bildbeschreibungen gegen die erforderlichen Zustände. Nur tatsächliche Widersprüche beanstanden; keine Stilwünsche. '
                'Eine fehlende Erwähnung ist noch kein gegenteiliger Zustand. characters bezeichnet Sichtbarkeit, nicht Sprechen. '
                'Return ONLY JSON {"issues":[{"panel":1,"character":"ID","field":"movement","quote":"wörtlicher widersprüchlicher Teil aus story","message":"konkreter Fehler"}]}. Ohne Widerspruch issues leer. '
                '\nKACHELN:'+json.dumps([{'panel':start+i+1,'story':s['story'],'required_states':{k:v for k,v in expected[i].items() if k in s['characters']}} for i,s in enumerate(chunk)],ensure_ascii=False))
            issues=engine.json_call(job,tag+'-continuity-review-'+str(start+1),review_prompt,validate_review,tokens=1100)
            if issues:
                chunk=engine.json_call(job,tag+'-continuity-repair-'+str(start+1),rewrite+'\nBELEGTE FEHLER:'+json.dumps(issues,ensure_ascii=False),validate_rewrite,tokens=650*len(chunk)+200)
                # Der Kritiker erhält ausschließlich die korrigierten Beschreibungen.
                review_prompt=review_prompt.split('\nKACHELN:')[0]+'\nKACHELN:'+json.dumps([{'panel':start+i+1,'story':s['story'],'required_states':{k:v for k,v in expected[i].items() if k in s['characters']}} for i,s in enumerate(chunk)],ensure_ascii=False)
                issues=engine.json_call(job,tag+'-continuity-review-final-'+str(start+1),review_prompt,validate_review,tokens=1100)
                if issues:
                    engine.store.write(job,'continuity-report.json',{'status':'failed','events':events,'issues':issues})
                    raise ValueError('Skript-Kontinuität widersprüchlich: '+'; '.join('Kachel '+str(x['panel'])+': '+x['message'] for x in issues))
        for i,scene in enumerate(chunk):
            names={c['id']:c['name'] for c in cast}
            visible=[names[k]+': '+state_text(v) for k,v in expected[i].items() if k in scene['characters'] and v]
            if visible:
                suffix='\nVerbindliche Bildzustände: '+' | '.join(visible)
                if len(scene['story'])+len(suffix)>4000:raise ValueError('Kontinuitätsangaben und Bildbeschreibung sind zusammen zu lang; Zustände oder Bildbeschreibung kürzen.')
                scene['story']+=suffix
            scene['continuity_state']=copy.deepcopy(expected[i]);saved=copy.deepcopy(scene.get('character_states',{}))
            for ident,facts in expected[i].items():
                if ident not in scene['characters']:continue
                physical=state_text(facts);base=saved.get(ident,'')
                # Die Bildbeschreibung ist das maßgebliche Bildprompt; Zustand zusätzlich in die Figurenanweisung aufnehmen.
                saved[ident]=('Verbindlicher Zustand: '+physical+'. Weitere Angaben nur soweit damit vereinbar: '+base if base and physical not in base else physical or base)
                if len(saved[ident])>1000:saved[ident]=physical
            scene['character_states']=saved
        result.extend(chunk);state=following;reports.extend(events)
        engine.store.write(job,'continuity-report.json',{'status':'checked','events':reports,'final_state':state,'discarded_unproven_events':discarded,'checked_panels':len(result),'total_panels':len(scenes)})
    return result,{'events':reports,'final_state':state,'discarded_unproven_events':discarded,'checked_panels':len(result)}
