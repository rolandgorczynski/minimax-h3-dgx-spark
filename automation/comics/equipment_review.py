"""Lokale Bildprüfung: tatsächlich gezeichnete Waffen gegen das feste Inventar zählen."""
import base64
import hashlib
import json
import re
from lettering import core
EQUIPMENT=core('equipment')


REVIEW_NOTE='Die automatische Waffenprüfung ist nicht verlässlich abgeschlossen. Einzelbefunde stehen im Prüfbericht.'
LEGACY_NOTE=re.compile(r'^Kachel \d+: (?:Schwertanzahl nicht eindeutig|Waffenprüfung nicht abgeschlossen)')


def presentation(job):
    """Alte Berichte unverändert erhalten, wiederholte Prüferunsicherheit verständlich anzeigen."""
    def uncertain(text):return isinstance(text,str) and (LEGACY_NOTE.match(text) or text==REVIEW_NOTE)
    equipment=job.get('equipment_warnings') or [];warnings=job.get('warnings') or []
    has_note=job.get('equipment_review_status')=='uncertain' or any(uncertain(t) for t in [*equipment,*warnings])
    return {'equipment_warnings':[t for t in equipment if not uncertain(t)],
            'equipment_review_note':REVIEW_NOTE if has_note else '',
            'warnings':[t for t in warnings if not uncertain(t)]+([REVIEW_NOTE] if has_note else [])}


def observations(value,expected):
    if isinstance(value,list) and len(value)==1:value=value[0]
    if not isinstance(value,dict) or set(value)!={'observations'} or not isinstance(value['observations'],list):raise ValueError('Waffenbeobachtungen als Liste erforderlich.')
    result={}
    for item in value['observations']:
        if not isinstance(item,dict) or set(item)!={'character','swords','evidence'}:raise ValueError('Figuren-ID, sichtbare Schwertanzahl und Bildbeleg erforderlich.')
        ident=item['character'];count=item['swords'];evidence=item['evidence']
        if ident not in expected:
            matches=[key for key,c in expected.items() if isinstance(ident,str) and c.get('name','').casefold()==ident.casefold()]
            if len(matches)==1:ident=matches[0];item={**item,'character':ident}
        if isinstance(count,list):
            locations=set()
            for weapon in count:
                if not isinstance(weapon,dict) or set(weapon)!={'location','evidence'} or any(not isinstance(weapon[k],str) or not weapon[k].strip() or len(weapon[k])>500 for k in weapon):raise ValueError('Jedes sichtbare Schwert braucht einen eindeutigen Ort und konkreten Bildbeleg.')
                location=weapon['location'].strip().casefold()
                if location in locations:raise ValueError('Dasselbe Schwert nicht zweimal am selben Ort zählen.')
                locations.add(location)
            item={**item,'items':count,'swords':len(count)};count=len(count)
        if ident not in expected or ident in result or (count is not None and (type(count) is not int or not 0<=count<=12)):raise ValueError('Eindeutige bekannte Figur und Schwertanzahl 0–12 oder null erforderlich.')
        if not isinstance(evidence,str) or not evidence.strip() or len(evidence)>1000:raise ValueError('Kurzer konkreter Bildbeleg erforderlich.')
        if count==0 and re.search(r'\b(?:die|eine|seine) Klinge ist (?:deutlich )?sichtbar\b',evidence,re.I):raise ValueError('Widersprüchlicher Prüfbericht: Sichtbare Klinge kann nicht als null Schwerter gezählt werden.')
        explicit=re.search(r'\binsgesamt\s+(ein(?:e[nmrs]?)?|zwei|drei|vier|\d+)\s+(?:(?:physisch(?:e[nmrs]?)?|unterscheidbare[nmrs]?|sichtbare[nmrs]?)\s+){0,3}Schwert(?:er[n]?)?\b',evidence,re.I)
        if explicit:
            number=explicit[1].lower();stated={'zwei':2,'drei':3,'vier':4}.get(number,int(number) if number.isdigit() else 1)
            if count!=stated:raise ValueError('Widersprüchlicher Prüfbericht: Zählwert passt nicht zur ausdrücklich genannten Gesamtzahl im Bildbeleg.')
        result[ident]=item
    if set(result)!=set(expected):raise ValueError('Jede zu prüfende Figur genau einmal zählen.')
    return result


def audit(engine,job,cast,scenes):
    store=engine.store;root=store.directory(job);records=[];issues=[];notes=[]
    equipment={c['id']:c for c in cast if EQUIPMENT.single_sword(c)}
    for i,scene in enumerate(scenes):
        expected={ident:equipment[ident] for ident in scene.get('characters',[]) if ident in equipment}
        if not expected:continue
        store.stage(job,'equipment_review',checked_panels=i,total_panels=len(scenes))
        try:
            images=[(root/f'panels/{i+1:02}_art.png').read_bytes()];references=[]
            for ident,c in expected.items():
                if c.get('inline_references'):
                    images.append(base64.b64decode(c['inline_references'][0]));references.append({'image':len(images),'character':ident,'name':c['name']})
            fingerprint=hashlib.sha256(json.dumps([{k:c.get(k,'') for k in ('id','name','description','outfit')} for c in expected.values()],sort_keys=True).encode())
            fingerprint.update(b'equipment-numeric-visible-v2')
            for picture in images:fingerprint.update(picture)
            digest=fingerprint.hexdigest()[:16]
            prompt=('Prüfe ausschließlich BILD 1, die erzeugte Comic-Zeichnung. Weitere Bilder zeigen nur Gesichtsidentitäten, KEINE zusätzlichen Waffen. '
                'Zähle pro Figur die tatsächlich unterscheidbaren physischen Schwerter und gib eine GANZE ZAHL zurück. '
                'Eine erkennbare Klinge in einer Hand zählt als ein Schwert, auch wenn ein Teil des Griffes verdeckt ist. '
                'Ein zusätzlicher Griff in einer Scheide zählt als ein weiteres Schwert, auch wenn seine Klinge verdeckt ist. '
                'Klinge und Griff desselben Schwertes zusammen nur einmal zählen. Eine LEERE Scheide ohne Griff zählt nicht. '
                'Wenn kein Schwert sichtbar ist, swords:0. Das bedeutet nicht, dass die Figur keines besitzt. '
                'swords:null nur wenn die Figur oder die Waffe im Bild wirklich nicht erkennbar oder zuordenbar ist; nicht bloß wegen einer teilweise verdeckten Klinge. '
                'Die Anzahl muss zur Beschreibung in evidence passen: Nicht null oder 0 schreiben und zugleich ein deutlich sichtbares Schwert beschreiben. '
                'Die Sollanzahl wird erst anschließend im Code verglichen. Nicht aus der Figurenbeschreibung oder den Referenzen abschreiben. '
                'Return ONLY JSON {"observations":[{"character":"exakte ID","swords":1,"evidence":"konkrete sichtbare Klingen und Griffe mit ihrer Position auf Deutsch"}]}. '
                '\nFIGURENIDENTITÄTEN:'+json.dumps([{k:c.get(k,'') for k in ('id','name','description')} for c in expected.values()],ensure_ascii=False)+
                '\nIDENTITÄTSREFERENZEN:'+json.dumps(references,ensure_ascii=False))
            found=engine.json_call(job,'equipment-review-'+digest+'-'+str(i+1),prompt,lambda v:observations(v,expected),images=images,tokens=1000)
            excess={k:v for k,v in found.items() if v['swords'] is not None and v['swords']>1}
            confirmed={}
            if excess:
                # Zweite Betrachtung derselben Originalpixel, keine automatische Neuzeichnung.
                verified=engine.json_call(job,'equipment-review-confirm-'+digest+'-'+str(i+1),prompt+'\nÜberprüfe die Zählung unabhängig erneut. Leere Scheiden, Gürtel und Falten sind keine Schwertgriffe. Ein Fehler darf nur bei klar getrennten physischen Schwertern bestätigt werden.',lambda v:observations(v,expected),images=images,tokens=1000)
                confirmed={k:v for k,v in verified.items() if k in excess and v['swords'] is not None and v['swords']>1}
            for ident,item in confirmed.items():issues.append({'panel':i+1,'character':ident,'expected':1,'observed':item['swords'],'evidence':item['evidence']})
            if any(v['swords'] is None for v in found.values()) or (excess and not confirmed):notes.append(f'Kachel {i+1}: Schwertanzahl nicht eindeutig; bitte das Bild prüfen.')
            records.append({'panel':i+1,'observations':list(found.values()),'confirmed_errors':list(confirmed.values())})
        except Exception as exc:
            notes.append(f'Kachel {i+1}: Waffenprüfung nicht abgeschlossen; manuell prüfen.')
            records.append({'panel':i+1,'error':str(exc)[:1000]})
    warnings=[f'Kachel {x["panel"]}: {equipment[x["character"]]["name"]} zeigt {x["observed"]} Schwerter statt eines. {x["evidence"]}' for x in issues]+([REVIEW_NOTE] if notes else [])
    report={'status':'failed' if issues else 'uncertain' if notes else 'checked' if records else 'not_applicable','issues':issues,'notes':notes,'panels':records,'warnings':warnings,'local_only':True}
    store.write(job,'equipment-report.json',report);store.update(job,equipment_unresolved=bool(issues),equipment_warnings=warnings,equipment_review_status=report['status'])
    return report
