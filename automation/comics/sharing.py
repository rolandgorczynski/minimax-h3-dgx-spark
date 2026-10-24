"""Bildpakete zum Teilen aus vorhandenen Comics, ohne Generierung oder externen Versand."""
import io
import json
import re
import struct
import urllib.parse
import zipfile
import zlib


KEY='comic-sharing-settings'


def settings(store):
    return store.integration_get(KEY) or {'substack_url':'','x_url':''}


def save_settings(store,value):
    if not isinstance(value,dict) or set(value)!={'substack_url','x_url'}:raise ValueError('Substack- und X-Adresse als Text senden.')
    result={}
    for name,address in value.items():
        if not isinstance(address,str) or len(address)>2048:raise ValueError('Ungültige Profiladresse.')
        address=address.strip()
        if address:
            parsed=urllib.parse.urlsplit(address)
            if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or any(ord(c)<33 for c in address):
                raise ValueError('Eine vollständige HTTPS-Profiladresse ohne Zugangsdaten eingeben.')
        result[name]=address
    store.integration_set(KEY,result);return result


def clean_png(data):
    """PNG-Bilddaten unverändert lassen, technische Texte und EXIF nicht weitergeben."""
    signature=b'\x89PNG\r\n\x1a\n'
    if not data.startswith(signature):raise ValueError('Ungültige PNG-Datei.')
    allowed={b'IHDR',b'PLTE',b'IDAT',b'IEND',b'tRNS',b'gAMA',b'cHRM',b'sRGB',b'iCCP',b'sBIT',b'bKGD',b'pHYs'}
    result=bytearray(signature);offset=8;seen=[]
    while offset<len(data):
        if offset+12>len(data):raise ValueError('Unvollständige PNG-Datei.')
        length=struct.unpack('>I',data[offset:offset+4])[0];end=offset+12+length
        if end>len(data):raise ValueError('Unvollständiger PNG-Abschnitt.')
        kind=data[offset+4:offset+8];payload=data[offset+8:offset+8+length]
        expected=struct.unpack('>I',data[end-4:end])[0]
        if zlib.crc32(kind+payload)&0xffffffff!=expected:raise ValueError('Beschädigte PNG-Datei.')
        if kind in allowed:result.extend(data[offset:end])
        elif not kind[0]&32:raise ValueError('Nicht unterstützter PNG-Bildabschnitt.')
        seen.append(kind);offset=end
        if kind==b'IEND':break
    if not seen or seen[0]!=b'IHDR' or seen[-1]!=b'IEND' or b'IDAT' not in seen:raise ValueError('PNG-Bilddaten fehlen.')
    return bytes(result)


def image_sources(job,page_template='standard'):
    if job.get('equipment_unresolved'):raise ValueError('Zusätzliche Schwerter erkannt. Bitte die betroffenen Bilder korrigieren, bevor du den Comic teilst.')
    if job.get('lettering_unresolved'):raise ValueError('Entwurf: Zuerst die Beschriftung unter „Sprechblasen positionieren“ korrigieren.')
    names={a['name'] for a in job.get('artifacts',[])}
    pages=sorted((n for n in names if re.fullmatch(r'pages/\d+\.png',n)),key=lambda n:int(n.split('/')[1].split('.')[0]))
    if page_template!='standard' and pages:return pages
    panels=sorted((n for n in names if re.fullmatch(r'panels/\d+_panel\.png',n)),key=lambda n:int(n.split('/')[1].split('_')[0]))
    if panels:return panels
    if 'comic.png' in names:return ['comic.png']
    raise ValueError('Diese Ausgabe hat noch keine fertigen Comic-Bilder.')


def selected_sources(store,job):
    path=store.directory(job['id'])/'editorial-source.json'
    template=json.loads(path.read_text()).get('page_template','standard') if path.exists() else job.get('request',{}).get('page_template','standard')
    return image_sources(job,template)


def compact_post(title,summary,url):
    from source_generator import post_summary
    budget=250-len(title)-len(url)-4
    short=post_summary({'text':summary},budget) if summary and budget>=30 else ''
    return '\n\n'.join(s for s in (title,short,url) if s)


def save_post(store,job,value):
    if not isinstance(value,dict) or set(value)!={'version','title','summary','source_url','short_text'}:raise ValueError('Titel, Zusammenfassung, Quellenlink, X-Text und Version senden.')
    current=manifest(store,job)
    if type(value['version']) is not int or value['version']!=current['post_version']:raise ValueError('Beitragstext wurde inzwischen geändert. Teilen-Dialog neu öffnen.')
    result={}
    for key,limit in [('title',200),('summary',1200),('source_url',2000),('short_text',4000)]:
        if not isinstance(value[key],str) or len(value[key])>limit:raise ValueError(f'{key}: maximal {limit} Zeichen.')
        result[key]=value[key].strip()
    if not result['title']:raise ValueError('Beitragstitel eingeben.')
    if result['source_url']:
        url=urllib.parse.urlsplit(result['source_url'])
        if url.scheme not in ('http','https') or not url.netloc or url.username or url.password:raise ValueError('Quellenlink als HTTP- oder HTTPS-Adresse ohne Zugangsdaten angeben.')
    result['version']=current['post_version']+1;store.integration_set('comic-post-'+job['id'],result)
    return manifest(store,job)


def manifest(store,job):
    if job['status'] not in ('completed','needs_review','editing'):raise ValueError('Zuerst die Erzeugung abschließen.')
    sources=selected_sources(store,job);width=max(2,len(str(len(sources))));title='Comic'
    path=store.directory(job['id'])/'story.json'
    if path.exists():title=json.loads(path.read_text()).get('title',title)
    source=store.directory(job['id'])/'editorial-source.json'
    data=json.loads(source.read_text()) if source.exists() else {}
    provenance=data.get('source_provenance',{})
    from source_generator import post_summary
    summary=data.get('post_summary') or (post_summary(provenance) if isinstance(provenance,dict) else '')
    url=provenance.get('url','') if isinstance(provenance,dict) else ''
    if not isinstance(url,str) or not url.startswith(('https://','http://')):url=''
    saved=store.integration_get('comic-post-'+job['id']) or {}
    title=saved.get('title',title);summary=saved.get('summary',summary);url=saved.get('source_url',url)
    text='\n\n'.join(s for s in (title,summary,url) if isinstance(s,str) and s.strip())
    return {'job_id':job['id'],'title':title,'summary':summary,'source_url':url,'short_text':saved.get('short_text',compact_post(title,summary,url)),'post_version':saved.get('version',0),'targets':settings(store),'text':text,
            'images':[{'name':f'{i+1:0{width}}.png','label':(f'Seite {i+1}' if sources[i].startswith('pages/') else f'Kachel {i+1}') if len(sources)>1 else 'Comic',
                       'url':f'/jobs/{job["id"]}/share/images/{i+1:0{width}}.png'} for i,_ in enumerate(sources)],
            'download_url':f'/jobs/{job["id"]}/share/images.zip','published':False}


def image(store,job,index):
    sources=selected_sources(store,job)
    if not 0<=index<len(sources):raise KeyError(index)
    root=store.directory(job['id']).resolve();path=(root/sources[index]).resolve()
    if not path.is_relative_to(root) or not path.is_file():raise KeyError(index)
    return clean_png(path.read_bytes())


def bundle(store,job):
    info=manifest(store,job);buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as archive:
        for index,item in enumerate(info['images']):archive.writestr(item['name'],image(store,job,index))
        archive.writestr('Beitragstext.txt',info['text']+'\n')
        archive.writestr('Anleitung.txt','Comic als Bilder veröffentlichen\n\nDie nummerierten PNG-Dateien in aufsteigender Reihenfolge in den Substack-Beitrag einfügen.\nTitel und Begleittext aus Beitragstext.txt übernehmen. In Substack prüfen und veröffentlichen.\nFür X: nummerierte PNGs im Beitragseditor anhängen. Längere Comics als Thread, beispielsweise vier Kacheln je Beitrag, veröffentlichen. Konto, Reihenfolge und Lesbarkeit vor dem Absenden prüfen.\nDieses Paket enthält keine PDF, Figurenreferenzen oder Workflow-Dateien.\nDas Vorbereiten dieses Pakets veröffentlicht nichts automatisch.\n')
    return buffer.getvalue()
