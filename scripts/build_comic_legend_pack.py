#!/usr/bin/env python3
"""Historische TextGrid-Sagentexte offline zu einem ergänzenden Quellenpaket bündeln."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import unicodedata
import xml.etree.ElementTree as ET
import zipfile

NS={'t':'http://www.tei-c.org/ns/1.0'}
TEI='{'+NS['t']+'}'
# Bereits vorhandene Stoffe beziehungsweise entsprechende bekannte Varianten.
EXCLUDE=re.compile(r'rattenfänger|rattenfaenger|weinsb[epr]|weinsperg|heinzelmänn|heinzelmaenn|hildebrand|hilderbrand|siegfried|kudrun|gudrun|wieland|beowulf|sigenot|wolfdietrich',re.I)
STYLE=('Alle Erzählertexte und Dialoge neu auf Deutsch formulieren, keine historischen Dialoge ungeprüft übernehmen. '
       'Einen zusammenhängenden Handlungsbogen mit dem überlieferten Ende wählen. Sage als Sage erzählen, nicht als belegtes Ereignis. '
       'Pro Kachel einen klaren Zeitpunkt zeigen. Identität, Kleidung, Reittiere und Gegenstände fortlaufend führen. '
       'Ziehen einer Waffe leert ihre Scheide; Absteigen verändert die Position der Figur. '
       'Verwandlungen und Zeitsprünge ausdrücklich markieren. Keine neue Nebenhandlung zur Streckung kurzer Stoffe erfinden. '
       'Höchstens acht zentrale Figuren individuell planen. Historische Vorurteile nicht als Tatsachen oder Gruppenurteile übernehmen.')

def normalized(value):
    value=unicodedata.normalize('NFKD',value.casefold().replace('ß','ss'))
    return re.sub(r'[^a-z0-9]+','',value)

def plain(element):
    """Text ohne editorische Fußnoten und Seitenmarken, mit Wortgrenzen."""
    if element.tag in {TEI+'note',TEI+'pb',TEI+'fw',TEI+'figure'}:return ''
    chunks=[element.text or '']
    for child in element:
        chunks.append(plain(child));chunks.append(child.tail or '')
    return re.sub(r'\s+',' ',''.join(chunks)).strip()

def sentences(text,limit=600):
    parts=re.split(r'(?<=[.!?])\s+',text)
    out=''
    for part in parts:
        candidate=(out+' '+part).strip()
        if len(candidate)>limit:break
        out=candidate
        if len(out)>180:break
    return out or text[:limit-1].rsplit(' ',1)[0]+'…'

def collect(archive):
    results=[];excluded=[]
    with zipfile.ZipFile(archive) as z:
        for name in sorted(z.namelist()):
            if not name.endswith('.xml'):continue
            payload=z.read(name)
            try:root=ET.fromstring(payload)
            except ET.ParseError:continue
            if root.tag!=TEI+'TEI':continue
            header=root.find('t:teiHeader',NS)
            title=header.find('.//t:titleStmt/t:title',NS) if header is not None else None
            body=root.find('.//t:body',NS)
            if title is None or body is None:continue
            title=plain(title)
            m=re.match(r'^(\d+)\.\s*(.+)$',title)
            if not m:continue
            title=m[2].strip();number=int(m[1])
            # Diese Edition enthält pro nummerierter Sage genau einen Text.
            blocks=[]
            for el in body.iter():
                if el.tag in {TEI+'p',TEI+'l'}:
                    text=plain(el)
                    if text:blocks.append(text)
            text='\n\n'.join(blocks)
            if 'by/3.0/de' not in ET.tostring(header,encoding='unicode'):
                raise ValueError('Ungeprüfte Transkriptionslizenz: '+name)
            ident=root.findtext('.//t:idno[@type="TextGridUri"]','',NS).removeprefix('textgrid:')
            if not ident:raise ValueError('TextGrid-ID fehlt: '+name)
            reason=''
            if EXCLUDE.search(title):reason='bereits vorhandener Stoff oder nahe Variante'
            elif re.search(r'jud|hebrä|hebrae',title+' '+text,re.I):reason='historische Gruppenstereotype; nicht für diesen allgemeinen Import ausgewählt'
            elif not 350<=len(text)<=14000:reason='zu kurz oder oberhalb der vollständigen Textgrenze'
            elif len(title)>200:reason='Titel oberhalb der Feldgrenze'
            entry=dict(number=number,title=title,text=text,textgrid_id=ident,source_sha256=hashlib.sha256(payload).hexdigest())
            if reason:excluded.append(dict(title=title,number=number,reason=reason))
            else:results.append(entry)
    return sorted(results,key=lambda x:x['number']),excluded

def build(archive,existing,target=1000):
    old=[]
    for path in existing:old+=json.loads(Path(path).read_text())['sources']
    # Drei eingebaute Quellen sind bereits im Dashboard, nicht in den Paketen.
    required=target-len(old)-3
    if required<=0:raise ValueError('Ziel ist bereits erreicht.')
    candidates,excluded=collect(archive)
    known={normalized(s['title'].split(' – ')[0]) for s in old}
    known.update(map(normalized,['Der kleine Prinz','Die Bremer Stadtmusikanten','Eine Weihnachtsgeschichte']))
    selected=[];seen_text=set()
    for c in candidates:
        key=normalized(c['title']);digest=hashlib.sha256(normalized(c['text']).encode()).hexdigest()
        if key in known or digest in seen_text:
            excluded.append(dict(title=c['title'],number=c['number'],reason='doppelter Titel oder Text'));continue
        known.add(key);seen_text.add(digest);selected.append(c)
    if len(selected)<required:
        raise ValueError(f'Nur {len(selected)} geeignete vollständige Texte für {required} neue Einträge; Ziel wird nicht mit Platzhaltern aufgefüllt.')
    eligible_count=len(selected)
    selected=selected[:required]
    sources=[]
    for c in selected:
        edition=f'Ludwig Bechstein: Deutsches Sagenbuch, zuerst 1853; TextGrid-Ausgabe nach dem historischen Druck Meersburg und Leipzig 1930, Sage {c["number"]}.'
        sources.append(dict(id='bechstein-sagen-'+c['textgrid_id'].replace('.','-'),title=c['title'],kind='Buch',creator='Ludwig Bechstein (1801–1860).',edition=edition,url='https://textgridrep.org/browse/'+c['textgrid_id'],territories='Deutschland; historischer Originaltext, keine moderne Filmfassung oder Übersetzung.',rights='Gemeinfreier historischer Originaltext von Ludwig Bechstein (gestorben 1860), § 64 UrhG. Transkriptionsnachweis: TextGrid und www.editura.de, Digitale Bibliothek, CC BY 3.0 DE; editorische Annotationen und Bilder nicht übernommen. Änderungen: XML entfernt, Fußnoten und Seitenmarken ausgelassen, Leerraum normalisiert. Lizenz: https://creativecommons.org/licenses/by/3.0/de/ .',post_summary=sentences(c['text']),text=f'STOFF UND HERKUNFT: {c["title"]}. Historische Sage, kein historischer Tatsachenbericht.\nÜBERLIEFERUNG: {edition}\nTEXTBEARBEITUNG: Vollständiger Erzähltext als Grundlage; keine eigens geschriebene Inhaltszusammenfassung. Typographisch normalisiert, editorische Fußnoten und Seitenmarken ausgelassen.\n\nHANDLUNGSGRUNDLAGE – HISTORISCHER ORIGINALTEXT:\n{c["text"]}\n\nSCHWERPUNKT DER COMIC-ADAPTION: Den konkreten Konflikt und die Wendung dieses Textes visuell erzählen. Länge und Zahl der Handlungsschritte am Stoff ausrichten.\nABGRENZUNG: Nur diese nummerierte Sage verwenden; benachbarte Kapitel und andere Fassungen nicht vermischen. Das überlieferte Ende erhalten. Historische Wertungen nicht als heutige Sachbehauptungen übernehmen.\n\nGESTALTUNG: {STYLE}'))
    pack=dict(schema_version=1,id='bechstein-sagen-bis-1000',title=f'{required} historische Sagen – Katalog auf {target} Vorlagen ergänzen',scope='Vollständige historische deutsche Erzähltexte mit Quellenbeleg; maschinell extrahiert und strukturell geprüft, nicht einzeln dramaturgisch redigiert.',rights_basis='Ludwig Bechstein starb 1860; historischer Originaltext gemeinfrei in Deutschland. Transkription: TextGrid/www.editura.de, CC BY 3.0 DE. Keine Bilder oder Annotationen übernommen.',rights_sources=['https://www.gesetze-im-internet.de/urhg/__64.html','https://creativecommons.org/licenses/by/3.0/de/'],sources=sources)
    report=dict(target=target,existing=len(old)+3,added=len(sources),archive_sha256=hashlib.sha256(Path(archive).read_bytes()).hexdigest(),archive_url='https://textgridlab.org/1.0/aggregator/zip2/textgrid:kf14.0?only=text%2Fxml&meta=true&filenames=%7Buri%7D.%7Bext%7D&dirnames=%7Buri%7D',selected=[{k:v for k,v in c.items() if k!='text'} for c in selected],excluded=excluded,remaining_candidates=eligible_count-required)
    return pack,report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('archive',type=Path);p.add_argument('--target',type=int,default=1000)
    p.add_argument('--output',type=Path,default=Path('examples/comics/sources/bechstein-sagen-bis-1000.json'))
    p.add_argument('--report',type=Path,default=Path('docs/comic-quellen-bechstein-nachweis.json'))
    args=p.parse_args();existing=sorted(x for x in args.output.parent.glob('*.json') if x!=args.output and not x.name.endswith('.nachweis.json'))
    pack,report=build(args.archive,existing,args.target)
    args.output.write_text(json.dumps(pack,ensure_ascii=False,indent=2)+'\n')
    args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('target','existing','added')},ensure_ascii=False))
if __name__=='__main__':main()
