#!/usr/bin/env python3
"""Stil-Vorschauen seriell mit lokalem ComfyUI erzeugen; keine Workflow-Dateien ändern."""
import argparse,hashlib,io,json,time,urllib.parse,urllib.request,uuid,subprocess,sys
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--url',default='http://192.168.1.224:8188');parser.add_argument('--only',nargs='*');parser.add_argument('--force',action='store_true',help='Vorhandene ausgewählte Vorschauen erneut erzeugen');args=parser.parse_args()
    sys.path.insert(0,str(ROOT/'automation/comics'))
    from local_llm import local_url
    args.url=local_url(args.url)
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def call(path,data=None,method=None):
        req=urllib.request.Request(args.url.rstrip('/')+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'},method=method)
        with opener.open(req,timeout=60) as response:
            raw=response.read(30_000_001)
            if len(raw)>30_000_000:raise ValueError('Zu große lokale Antwort.')
            return json.loads(raw) if 'json' in response.headers.get('Content-Type','') else raw
    catalog=json.loads((ROOT/'extensions/dgx-comics/style_catalog.json').read_text());out=ROOT/'automation/comics/style-previews';out.mkdir(exist_ok=True)
    workflow=json.loads((ROOT/'examples/comics/workflows/04_Comic_Automat_9B.json').read_text());loaders={str(n['id']):{'class_type':n['type'],'inputs':dict(zip({'UNETLoader':['unet_name','weight_dtype'],'CLIPLoader':['clip_name','type','device'],'VAELoader':['vae_name']}[n['type']],n['widgets_values']))} for n in workflow['nodes'] if n['type'] in ('UNETLoader','CLIPLoader','VAELoader')}
    manifest_path=out/'manifest.json';manifest=json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    if args.only and set(args.only)-{s['id'] for s in catalog}:parser.error('Unbekannte Stil-ID in --only.')
    find=lambda kind:next(key for key,v in loaders.items() if v['class_type']==kind)
    state_path=Path('/tmp/comic-style-preview-state.json');state=json.loads(state_path.read_text()) if state_path.exists() else {}
    for i,style in enumerate(catalog):
        if args.only and style['id'] not in args.only:continue
        path=out/(style['id']+'.webp');digest=hashlib.sha256(style['prompt'].encode()).hexdigest()
        if not args.force and path.exists() and (state.get(style['id'],{}).get('digest')==digest or manifest.get(style['id'],{}).get('prompt_sha256')==digest and manifest[style['id']].get('sha256')==hashlib.sha256(path.read_bytes()).hexdigest()):
            print(f'{i+1}/{len(catalog)} vorhanden: {style["name"]}',flush=True);continue
        entry=state.get(style['id'],{})
        if entry.get('digest')!=digest or args.force and not entry.get('prompt_id'):entry={'session':uuid.uuid4().hex,'digest':digest,'seed':uuid.uuid4().int%2147483648 if args.force else 1984}
        state[style['id']]=entry;state_path.write_text(json.dumps(state))
        if entry.get('prompt_id'):
            history=call('/history/'+entry['prompt_id']);queue=call('/queue')
            if entry['prompt_id'] not in history and not any(row[1]==entry['prompt_id'] for row in queue['queue_running']+queue['queue_pending']):entry.pop('prompt_id',None)
        if not entry.get('prompt_id'):
            while True:
                queue=call('/queue')
                if not queue['queue_running'] and not queue['queue_pending']:break
                print('Warte auf freie lokale ComfyUI-Warteschlange.',flush=True);time.sleep(5)
            prompt='Character reference portrait, exactly one original fictional adult traveler, short dark hair, plain cloak, holding a small lantern. Head and upper torso clearly visible, neutral background. No known character, no emblem, no text, no lettering. Art style: '+style['prompt']
            graph=dict(loaders)
            graph.update({
                '90':{'class_type':'CLIPTextEncode','inputs':{'clip':[find('CLIPLoader'),0],'text':prompt}},
                '91':{'class_type':'EmptyFlux2LatentImage','inputs':{'width':512,'height':352,'batch_size':1}},
                '92':{'class_type':'Flux2Scheduler','inputs':{'steps':4,'width':512,'height':352}},
                '93':{'class_type':'BasicGuider','inputs':{'model':[find('UNETLoader'),0],'conditioning':['90',0]}},
                '94':{'class_type':'RandomNoise','inputs':{'noise_seed':entry.get('seed',1984)}},
                '95':{'class_type':'KSamplerSelect','inputs':{'sampler_name':'euler'}},
                '96':{'class_type':'SamplerCustomAdvanced','inputs':{'noise':['94',0],'guider':['93',0],'sampler':['95',0],'sigmas':['92',0],'latent_image':['91',0]}},
                '98':{'class_type':'VAEDecode','inputs':{'samples':['96',0],'vae':[find('VAELoader'),0]}},
                '97':{'class_type':'PreviewImage','inputs':{'images':['98',0]}}})
            reply=call('/prompt',{'prompt':graph,'client_id':'comic-style-previews','extra_data':{'comic_automation_session':entry['session'],'comic_automation_step':'style-preview-'+style['id']}})
            if reply.get('node_errors'):raise ValueError(json.dumps(reply['node_errors']))
            entry['prompt_id']=reply['prompt_id'];state_path.write_text(json.dumps(state))
        print(f'{i+1}/{len(catalog)} erzeuge: {style["name"]}',flush=True);started=time.monotonic()
        while True:
            history=call('/history/'+entry['prompt_id'])
            if entry['prompt_id'] in history:
                record=history[entry['prompt_id']]
                if record.get('status',{}).get('status_str')=='error':raise RuntimeError(json.dumps(record['status']['messages'])[:3000])
                if record.get('status',{}).get('completed'):break
            if time.monotonic()-started>1800:raise TimeoutError('Vorschau wartet zu lange; Auftrag wird nicht abgebrochen. Skript erneut aufrufen.')
            time.sleep(2)
        descriptor=record['outputs']['97']['images'][0]
        if descriptor.get('type')!='temp' or descriptor.get('subfolder') not in ('','comic-automation/'+entry['session']):raise ValueError('Unerwarteter Vorschaupfad.')
        raw=call('/view?'+urllib.parse.urlencode(descriptor))
        with Image.open(io.BytesIO(raw)) as image:
            preview=image.convert('RGB');preview.thumbnail((384,384));preview.save(path,format='WEBP',quality=88)
        # Ausschließlich eigene temporäre Referenzen und den eigenen History-Eintrag aufräumen.
        if descriptor.get('subfolder'):call('/dgx-comics/automation/'+entry['session'],method='DELETE')
        else:
            name=descriptor['filename']
            if '/' in name or '\\' in name or '..' in name:raise ValueError('Ungültiger temporärer Bildname.')
            code="import sys;sys.path.insert(0,'/opt/ComfyUI');from pathlib import Path;import folder_paths;root=Path(folder_paths.get_temp_directory()).resolve();p=(root/sys.argv[1]).resolve();assert p.parent==root;p.unlink(missing_ok=True)"
            subprocess.run(['docker','exec','minimax-h3-comfyui','python','-c',code,name],check=True)
        call('/history',{'delete':[entry['prompt_id']]})
        manifest[style['id']]={'name':style['name'],'prompt_sha256':digest,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'seed':entry.get('seed',1984),'preview_size':list(preview.size),'local_model':True};manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
        entry.pop('prompt_id',None);state_path.write_text(json.dumps(state));print(f'{i+1}/{len(catalog)} fertig: {style["name"]}',flush=True)
    print('Lokale Stil-Vorschauen fertig.',flush=True)

if __name__=='__main__':main()
