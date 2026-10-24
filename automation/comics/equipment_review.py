"""Lokale Bildprüfung: tatsächlich gezeichnete Waffen gegen das feste Inventar zählen."""
import base64
import hashlib
import json
from lettering import core
EQUIPMENT=core('equipment')


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
            for picture in images:fingerprint.update(picture)
            digest=fingerprint.hexdigest()[:16]
            prompt=('Prüfe ausschließlich BILD 1, die erzeugte Comic-Zeichnung. Weitere Bilder zeigen nur Gesichtsidentitäten, keine zusätzliche Szene. '
                'Zähle pro aufgeführter Figur die sichtbar unterscheidbaren physischen Schwerter. Ein gezogenes Schwert UND ein zusätzlicher Griff in der Scheide sind zwei Schwerter. '
                'Eine leere Scheide ohne Griff ist kein weiteres Schwert. Griff und Klinge desselben Schwertes nicht doppelt zählen. '
                'Keine Zählung aus dem Sollzustand abschreiben: Liste stattdessen JEDES tatsächlich sichtbare physische Schwert einzeln mit seinem Ort auf. Python zählt die Liste. Eine Klinge und ihr eigener Griff sind EIN Listeneintrag. Ein weiterer Griff in einer Scheide ist ein SEPARATER Eintrag. '
                'Verdeckte, angeschnittene oder nicht sicher zuzuordnende Gegenstände nicht erfinden; bei unklarer Anzahl swords:null. '
                'Die Quelle verlangt pro Figur insgesamt genau EIN Schwert. Prüfe besonders zusätzliche Waffen am Gürtel, Rücken und in einer zweiten Hand. '
                'Return ONLY JSON {"observations":[{"character":"exakte ID","swords":[{"location":"rechte Hand","evidence":"sichtbare Klinge mit zugehörigem Griff"}],"evidence":"kurze Gesamtbeobachtung auf Deutsch"}]}. Bei unklarer Zuordnung swords:null. '
                '\nFIGUREN:'+json.dumps([{k:c.get(k,'') for k in ('id','name','description','outfit')} for c in expected.values()],ensure_ascii=False)+
                '\nIDENTITÄTSREFERENZEN:'+json.dumps(references,ensure_ascii=False))
            found=engine.json_call(job,'equipment-review-'+digest+'-'+str(i+1),prompt,lambda v:observations(v,expected),images=images,tokens=1000)
            excess={k:v for k,v in found.items() if v['swords'] is not None and v['swords']>1}
            confirmed={}
            if excess:
                # Zweite Betrachtung derselben Originalpixel, keine automatische Neuzeichnung.
                verified=engine.json_call(job,'equipment-review-confirm-'+digest+'-'+str(i+1),prompt+'\nÜberprüfe die Zählung unabhängig erneut. Leere Scheiden, Gürtel und Falten sind keine Schwertgriffe. Ein Fehler darf nur bei klar getrennten physischen Schwertern bestätigt werden.',lambda v:observations(v,expected),images=images,tokens=1000)
                confirmed={k:v for k,v in verified.items() if k in excess and v['swords'] is not None and v['swords']>1}
            for ident,item in confirmed.items():issues.append({'panel':i+1,'character':ident,'expected':1,'observed':item['swords'],'evidence':item['evidence']})
            if any(v['swords'] in (None,0) for v in found.values()) or (excess and not confirmed):notes.append(f'Kachel {i+1}: Schwertanzahl nicht eindeutig; bitte das Bild prüfen.')
            records.append({'panel':i+1,'observations':list(found.values()),'confirmed_errors':list(confirmed.values())})
        except Exception as exc:
            notes.append(f'Kachel {i+1}: Waffenprüfung nicht abgeschlossen; manuell prüfen.')
            records.append({'panel':i+1,'error':str(exc)[:1000]})
    warnings=[f'Kachel {x["panel"]}: {equipment[x["character"]]["name"]} zeigt {x["observed"]} Schwerter statt eines. {x["evidence"]}' for x in issues]+notes
    report={'status':'failed' if issues else 'uncertain' if notes else 'checked' if records else 'not_applicable','issues':issues,'panels':records,'warnings':warnings,'local_only':True}
    store.write(job,'equipment-report.json',report);store.update(job,equipment_unresolved=bool(issues),equipment_warnings=warnings,equipment_review_status=report['status'])
    return report
