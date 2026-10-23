"""Bounded writer → editor → Studio → visual review pipeline."""
from character_profiles import narrative
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import uuid
import zipfile
from learning import evidence,record,validate_lessons

STYLES=['Klassischer Comic', 'Großstadt-Noir (düster)', 'Ligne claire', 'Manga Schwarzweiß', 'Aquarell-Reportage', 'Graphic Novel realistisch', 'Holzschnitt / Linolschnitt', 'Retro-Zeitungscomic', 'Europäischer Abenteuercomic', 'Science-Fiction / Cyberpunk', 'Warme Alltagsillustration']
ID=re.compile(r'^[a-f0-9]{32}$')
TERMINAL=('completed','needs_review','failed')


def validate_request(value):
    if not isinstance(value,dict):raise ValueError('JSON-Objekt erwartet.')
    allowed={'thema','kacheln','stil','sprache','max_korrekturrunden','figuren_ids','seed','signatur'}
    if set(value)-allowed:raise ValueError('Unbekannte Parameter: '+', '.join(sorted(set(value)-allowed)))
    result={'thema':'','kacheln':12,'stil':'Großstadt-Noir (düster)','sprache':'de','max_korrekturrunden':2,'figuren_ids':[],'seed':int.from_bytes(os.urandom(4),'big')%2147483648,'signatur':''}
    result.update(value)
    if result['sprache']!='de':raise ValueError('Alle Geschichten werden ausschließlich auf Deutsch erstellt (sprache: de).')
    for key,limit in [('thema',8000),('sprache',40),('signatur',200)]:
        if not isinstance(result[key],str) or len(result[key])>limit:raise ValueError(f'Ungültiger Parameter {key}.')
    for key,low,high in [('kacheln',1,12),('max_korrekturrunden',0,3),('seed',0,2147483647)]:
        if type(result[key]) is not int or not low<=result[key]<=high:raise ValueError(f'{key}: {low}–{high} wählen.')
    if result['stil'] not in STYLES:raise ValueError('Unbekannter Comic-Stil.')
    ids=result['figuren_ids']
    if not isinstance(ids,list) or len(ids)>4 or len(set(ids))!=len(ids) or any(not isinstance(x,str) or not ID.fullmatch(x) for x in ids):raise ValueError('Maximal vier eindeutige Figuren-IDs.')
    return result


def parse_json(text):
    text=re.sub(r'<think>.*?</think>','',text,flags=re.S)
    positions=[p for p in (text.find('{'),text.find('[')) if p>=0]
    if not positions:raise ValueError('Das Modell hat kein JSON geliefert.')
    return json.JSONDecoder().raw_decode(text[min(positions):])[0]


def valid_review(value):
    if not isinstance(value,dict) or type(value.get('approved')) is not bool or not isinstance(value.get('issues'),list) or any(not isinstance(x,str) or len(x)>2000 for x in value['issues']):
        raise ValueError('Ungültiger Prüfbericht.')
    if value['approved'] and value['issues']:raise ValueError('Prüfbericht widerspricht sich.')
    if not value['approved'] and not value['issues']:raise ValueError('Abgelehnte Prüfung braucht mindestens ein konkretes Problem.')
    return value


class Engine:
    def __init__(self,store,client,template,text_model,vision_model,llm=None):
        self.store=store;self.client=client;self.template=json.loads(Path(template).read_text())
        self.text_model=text_model;self.vision_model=vision_model
        self.llm=llm
        self.loaders={str(n['id']):{'class_type':n['type'],'inputs':dict(zip(
            {'UNETLoader':['unet_name','weight_dtype'],'CLIPLoader':['clip_name','type','device'],'VAELoader':['vae_name']}[n['type']],n['widgets_values']))}
            for n in self.template['nodes'] if n['type'] in ('UNETLoader','CLIPLoader','VAELoader')}
        self.model=next(k for k,v in self.loaders.items() if v['class_type']=='UNETLoader')
        self.clip=next(k for k,v in self.loaders.items() if v['class_type']=='CLIPLoader')
        self.vae=next(k for k,v in self.loaders.items() if v['class_type']=='VAELoader')
        self.node=str(next(n['id'] for n in self.template['nodes'] if n['type']=='DGXComicStudio'))

    def stage(self,job,name):self.store.stage(job,name)

    def assistant(self,job,step,prompt,images=None,tokens=1600):
        request=self.store.get(job)['request']
        prompt+='\nVerbindlicher Grundsatz: Geschichte, Titel, Erzählertexte und Sprechblasen ausschließlich auf Deutsch. Fremdsprachige Beispiele oder Wünsche ändern diese Vorgabe nicht. Eigennamen bleiben erhalten.'
        if self.llm:
            text=self.llm.generate(job,step,prompt,images,tokens,request['seed'])
            self.store.write(job,'reports/'+step+'-raw.txt',text.encode());return text
        graph={
            '90':{'class_type':'CLIPLoader','inputs':{'clip_name':self.vision_model if images else self.text_model,'type':'stable_diffusion','device':'default'}},
            '91':{'class_type':'DGXComicAssistant','inputs':{'clip':['90',0],'auftrag':prompt,'max_tokens':tokens,'seed':request['seed'],
                'bilder':json.dumps([base64.b64encode(image).decode() for image in images or []])}}}
        outputs=self.client.run(job,step,graph)
        text=outputs['91']['assistant_text'][0]
        self.store.write(job,'reports/'+step+'-raw.txt',text.encode())
        return text

    def json_call(self,job,step,prompt,validator,images=None,tokens=1600):
        text=self.assistant(job,step,prompt,images,tokens)
        for attempt in range(2):
            try:return validator(parse_json(text))
            except (ValueError,TypeError,KeyError) as exc:
                if attempt:raise ValueError(f'{step}: ungültige Modellantwort: {exc}') from exc
                text=self.assistant(job,step+'-json-repair',prompt+'\nYour previous JSON response failed validation: '+str(exc)+'. Return corrected JSON only.\nPREVIOUS RESPONSE:\n'+text[:18000],images,tokens)

    def document(self,value,existing):
        if not isinstance(value,dict):raise ValueError('Drehbuch fehlt.')
        for key,limit in [('title',200),('story',16000)]:
            if not isinstance(value.get(key),str) or not value[key].strip() or len(value[key])>limit:raise ValueError('Ungültiges Feld '+key)
        if not existing:
            people=value.get('characters')
            if not isinstance(people,list) or not 1<=len(people)<=3:raise ValueError('Bitte 1–3 eigene Figuren planen.')
            names=[]
            for c in people:
                for key,limit in [('name',80),('description',1500),('outfit',600)]:
                    if not isinstance(c.get(key),str) or not c[key].strip() or len(c[key])>limit:raise ValueError('Ungültiges Figurenfeld '+key)
                names.append(c['name'].casefold())
            if len(names)!=len(set(names)):raise ValueError('Figurennamen müssen eindeutig sein.')
        return value

    def review(self,job,step,subject,extra=''):
        language=self.store.get(job)['request']['sprache']
        return self.json_call(job,step,'You are a strict comic editor. Review this fictional draft for coherent cause and effect, a clear ending, stable characters, exact speaker attribution and concise readable text. Check story, captions and dialogue use the requested language: '+language+'. '+extra+
            '\nReturn ONLY JSON {"approved":true or false,"issues":["specific actionable issue"]}. At most three concrete issues, each under 180 characters. Be critical about actual plot or attribution errors, but do not invent defects or demand unnecessary detail.\nDRAFT:\n'+json.dumps(subject,ensure_ascii=False),valid_review,tokens=500)

    def require_german(self,job,step,value,validator,tokens):
        """Mandatory language gate; one translation attempt, then stop before rendering."""
        def check(candidate,iteration):
            return self.json_call(job,step+'-review-'+str(iteration),
                'Prüfe ausschließlich die Sprache ALLER Texte dieses JSON-Dokuments. Vollständige Sätze müssen auf Deutsch sein. Englische oder andere fremdsprachige Erzähltexte sind nicht zulässig. Eigennamen und übliche kurze Ausrufe wie Okay sind erlaubt. Kein Stilurteil. Return ONLY JSON {"approved":true,"issues":[]} oder {"approved":false,"issues":["konkreter fremdsprachiger Text"]}.\nTEXTE:\n'+json.dumps(candidate,ensure_ascii=False),valid_review,tokens=400)
        review=check(value,0)
        if review['approved']:return value
        fixed=self.json_call(job,step+'-translation',
            'Übersetze ALLE Texte ins Deutsche. Erhalte die genaue JSON-Struktur, Datentypen, Eigennamen, Handlung und Bedeutung. Strings bleiben Strings; keine Aufteilung in Kacheln oder neue Objekte. Keine zusätzlichen Inhalte. Return ONLY JSON matching the same structure.\nTEXTE:\n'+json.dumps(value,ensure_ascii=False),validator,tokens=tokens)
        if not check(fixed,1)['approved']:
            raise ValueError('Deutschpflicht nicht erfüllt: Nach der Übersetzung bleiben fremdsprachige Texte. Bilderzeugung angehalten.')
        return fixed

    def workflow(self,request,doc,cast,plan,revisions):
        workflow=copy.deepcopy(self.template)
        values=[doc['story'],request['stil'],request['kacheln'],'Comic generieren',doc['title'],min(3,request['kacheln']),request['signatur'],request['seed'],json.dumps(plan,ensure_ascii=False),json.dumps(revisions),json.dumps(cast,ensure_ascii=False)]
        for node in workflow['nodes']:
            if node['type']=='DGXComicStudio':
                node['widgets_values']=values;node['properties']['cast_initialized']=True
        return workflow

    def studio(self,job,step,doc,cast,plan=None,revisions=None):
        req=self.store.get(job)['request'];graph=copy.deepcopy(self.loaders)
        fields=dict(zip(['artikel','comic_art','anzahl_kacheln','aktion','titel','spalten','signatur','seed','bearbeiteter_plan','kachel_revisionen','figuren'],
            [doc['story'],req['stil'],req['kacheln'],'Comic generieren' if plan else 'Szenen planen',doc['title'],min(3,req['kacheln']),req['signatur'],req['seed'],json.dumps(plan,ensure_ascii=False) if plan else '',json.dumps(revisions or {}),json.dumps(cast,ensure_ascii=False)]))
        fields.update(model=[self.model,0],clip=[self.clip,0],vae=[self.vae,0],automation_session=job)
        graph[self.node]={'class_type':'DGXComicStudio','inputs':fields}
        workflow=self.workflow(req,doc,cast,plan or {},revisions or {})
        return self.client.run(job,step,graph,workflow)[self.node]

    def validate_scenes(self,value,count,cast):
        if not isinstance(value,list) or len(value)!=count:raise ValueError(f'Genau {count} Szenen erforderlich.')
        known={c['id'] for c in cast};names={name.casefold():c['id'] for c in cast for name in [c['name'],*c.get('aliases',[])]}
        result=[]
        for scene in value:
            if not isinstance(scene,dict) or not isinstance(scene.get('story'),str) or not scene['story'].strip() or len(scene['story'])>4000:raise ValueError('Ungültige Szene.')
            dialog=scene.get('dialog','')
            if not isinstance(dialog,str) or len(dialog)>400:raise ValueError('Erzählertext maximal 400 Zeichen.')
            bubbles=scene.get('bubbles',[])
            if not isinstance(bubbles,list) or len(bubbles)>6:raise ValueError('Maximal sechs Sprechblasen.')
            for bubble in bubbles:
                if not isinstance(bubble,dict) or not isinstance(bubble.get('speaker'),str) or not isinstance(bubble.get('text'),str) or len(bubble['text'])>400:raise ValueError('Ungültige Sprechblase.')
                bubble['speaker']=names.get(bubble['speaker'].casefold(),bubble['speaker'])
                if bubble['speaker'] not in known:raise ValueError('Sprechblase braucht eine eindeutige Figuren-ID: '+bubble['speaker'])
            ids=scene.get('characters')
            if ids is None:
                ids=[c['id'] for c in cast if any(re.search(r'(?<!\w)'+re.escape(name)+r'(?!\w)',scene['story']+' '+dialog,re.I) for name in [c['name'],*c.get('aliases',[])])]
            if not isinstance(ids,list) or any(x not in known for x in ids):raise ValueError('Unbekannte Figuren-Zuordnung.')
            states=scene.get('character_states',{})
            if not isinstance(states,dict) or len(states)>8 or any(key not in known or not isinstance(v,str) or not v.strip() or len(v)>1000 for key,v in states.items()):raise ValueError('Ungültiger Figuren-Zustand je Kachel.')
            result.append({**scene,'dialog':dialog,'bubbles':bubbles,'characters':ids})
        return result

    def preflight(self,plan,cast):
        result=self.client.request('POST','/dgx-comics/automation/check-plan',{'scenes':plan['scenes'],'cast':cast})
        known={c['id'] for c in cast}
        for i,scene in enumerate(plan['scenes']):
            for bubble in scene.get('bubbles',[]):
                if bubble['speaker'] not in known:
                    result['issues'].append({'panel':i+1,'message':'Sprechblase ohne eindeutige Figur: '+bubble['speaker']})
                    result['valid']=False
        return result

    def portrait(self,job,character,index,style):
        graph=copy.deepcopy(self.loaders);req=self.store.get(job)['request']
        graph['80']={'class_type':'DGXComicPortrait','inputs':{'model':[self.model,0],'clip':[self.clip,0],'vae':[self.vae,0],
            'beschreibung':character['description']+' Clothing: '+character['outfit'],'stil':style,'session':job,'figur_id':character['id'],'seed':(req['seed']+index*103)%2147483648}}
        output=self.client.run(job,'portrait-'+str(index),graph)['80']
        image=self.client.download(job,output['images'][0])
        self.store.write(job,'characters/'+character['id']+'.png',image)
        return base64.b64encode(image).decode()

    def existing_cast(self,ids):
        if not ids:return []
        library=self.client.request('GET','/dgx-comics/characters')['characters']
        selected=[]
        for ident in ids:
            original=next((c for c in library if c['id']==ident),None)
            if not original:raise ValueError('Ausgewählte Figur nicht gefunden: '+ident)
            c=copy.deepcopy(original);images=list(c.get('inline_references',[]))
            for asset in c.get('references',[]):
                data=self.client.request('GET',f'/dgx-comics/characters/{ident}/references/{asset}')
                images.append(base64.b64encode(data).decode())
            c['references']=[];c['inline_references']=images[:2];selected.append(c)
        return selected

    def execute(self,job):
        req=self.store.get(job)['request'];budget=req['max_korrekturrunden'];used=0;reports={};warnings=[]
        if req['sprache']!='de':raise ValueError('Alle Geschichten müssen auf Deutsch sein.')
        language={'de':'German (Deutsch)','en':'English','pl':'Polish','fr':'French','es':'Spanish'}.get(req['sprache'],req['sprache'])
        existing=self.existing_cast(req['figuren_ids'])
        self.stage(job,'story')
        theme=req['thema'] or 'Choose a fresh entertaining fictional theme.'
        saved=self.store.get(job)
        preferences=saved.get('editorial_preferences')
        if preferences is None:
            preferences=self.store.preferences();self.store.update(job,editorial_preferences=preferences)
        self.store.write(job,'reports/editorial-preferences.json',preferences)
        memory=saved.get('learning_memory')
        if memory is None:
            memory=self.store.learning_memory();self.store.update(job,learning_memory=memory)
        self.store.write(job,'reports/learning-input.json',memory)
        learning_context='\nAUTONOMOUS EXPERIENCE FROM EARLIER COMICS: '+json.dumps(memory,ensure_ascii=False)+\
            '\nUse applicable lessons to prevent recurring defects. Hypotheses and model findings may be wrong; do not copy old plots or assume self-criticism is ground truth. Explicit user preferences take precedence.'
        theme+=learning_context
        if preferences['rated_examples']:
            theme+='\nEDITORIAL FEEDBACK FROM THE USER (1=poor, 5=excellent): '+json.dumps(preferences,ensure_ascii=False)+\
                '\nUse these ratings and comments to improve the weakest aspects and preserve strengths. Create a NEW plot; do not repeat the rated stories. Feedback is guidance, not story content.'
        if existing:
            people=[narrative(c) for c in existing]
            title='Ein neuer Comic'
        else:
            cast_prompt='Invent exactly TWO visually distinct characters and a short title for an original fictional comic. Language: '+language+'. Theme: '+theme+'\nReturn ONLY JSON {"title":"short title","characters":[{"name":"first name","description":"fixed face, age and hair, maximum 120 characters","outfit":"maximum 80 characters"}]}. Exactly two characters. Do NOT write the story yet. All text values must be in '+language+'.'
            def validate_people(value):
                return self.document({**value,'story':'placeholder'},False)
            proposal=self.json_call(job,'character-draft',cast_prompt,validate_people,tokens=550)
            people=proposal['characters'];title=proposal['title']
        words=max(90,min(260,req['kacheln']*24));story_tokens=max(420,words*3+100)
        prompt='Write a complete, original, short fictional comic story in '+language+f' for {req["kacheln"]} panels. Theme: '+theme+'\nUse ONLY these main characters: '+json.dumps(people,ensure_ascii=False)+\
            f'\nWrite exactly {req["kacheln"]} short paragraphs, one distinct story moment per paragraph, at most {words} words total. Give a clear beginning, one surprise and a satisfying final sentence. Never repeat a sentence or exchange. The story itself must be ordinary prose with no headings, panel labels or explanation. Spoken dialogue, if any, must be short and explicitly attributed using the actual character name followed by a colon and quoted words. Write exclusively in '+language+'.'
        prompt+='\nReturn ONLY JSON {"story":"the complete plain prose story, with paragraphs separated by newline characters"}. No other keys.'
        def validate_prose(value):
            if not isinstance(value,dict) or not isinstance(value.get('story'),str) or not value['story'].strip() or len(value['story'])>16000:
                raise ValueError('Eine vollständige Geschichte im JSON-Feld story erwartet.')
            return value['story'].strip()
        story=self.json_call(job,'story-prose',prompt,validate_prose,tokens=story_tokens)
        doc=self.document({'title':title,'story':story,'characters':people},existing)
        best_story=None
        for iteration in range(budget+1):
            self.stage(job,'story_review')
            review=self.review(job,'story-review-'+str(iteration),doc);reports['story']=review
            sentences=re.split(r'(?<=[.!?])\s+',doc['story'])
            repeated=[v for v in set(sentences) if len(v)>20 and sentences.count(v)>1]
            if repeated:
                review['approved']=False;review['issues'].append('Repeated sentences: '+'; '.join(repeated[:2]))
            record(reports,'story',iteration,review)
            grade=(not review['approved'],len(review['issues']))
            if best_story and grade>best_story[0]:
                _,doc,review=best_story;reports['story']=review
                reports.setdefault('discarded_revisions',[]).append({'area':'story','round':iteration,'reason':'More findings than the previous version.'})
                warnings.extend(review['issues']);break
            best_story=(grade,copy.deepcopy(doc),copy.deepcopy(review))
            if review['approved']:break
            if used>=budget or iteration>=1:warnings.extend(review['issues']);break
            revised=self.json_call(job,'story-revision-'+str(iteration),prompt+f'\nImprove this draft to resolve the editor issues. Keep the same people and write at most {words} words.\nDRAFT:'+doc['story']+'\nISSUES:'+json.dumps(review['issues']),validate_prose,tokens=story_tokens)
            doc=self.document({**doc,'story':revised},existing)
            used+=1
        self.stage(job,'german_story_check')
        def validate_story_text(value):
            return {key:self.document({**doc,**value},existing)[key] for key in ('title','story')}
        doc.update(self.require_german(job,'german-story',{'title':doc['title'],'story':doc['story']},validate_story_text,story_tokens+200))
        self.store.write(job,'story.json',doc)
        cast=existing or [{'id':uuid.uuid5(uuid.UUID(job),'character-'+str(i)).hex,'name':c['name'],'description':c['description'],'outfit':c['outfit'],'aliases':[], 'variants':{},'references':[]} for i,c in enumerate(doc['characters'])]
        self.stage(job,'character_references')
        for i,c in enumerate(cast):
            if not c.get('inline_references'):c['inline_references']=[self.portrait(job,c,i,req['stil'])]
            else:
                for j,encoded in enumerate(c['inline_references']):self.store.write(job,f'characters/{c["id"]}-{j}.png',base64.b64decode(encoded))
        self.store.write(job,'characters.json',cast)
        self.stage(job,'scene_planning')
        profiles=[narrative(c) for c in cast]
        instructions=f'Adapt this fictional story into exactly {req["kacheln"]} distinct comic panels in {req["sprache"]}. Cover the beginning and ending in order. Return ONLY a JSON array. Each object has story (concrete camera composition under 300 characters), dialog (NARRATOR caption under 120 characters), characters (list of cast IDs visible), bubbles (at most two, each with speaker as an exact cast ID, text under 60 characters, expression normal). Only use the given people and story. Keep faces below the top third of the image to leave space for bubbles. Do not add text inside the illustration. Spoken lines must belong to the correct person; narration goes in dialog.\nCAST:'+json.dumps(profiles,ensure_ascii=False)+'\nSTORY:'+doc['story']
        instructions=learning_context+'\n'+instructions+'\nAll story, dialog and bubble text must be in '+language+'.'
        scenes=self.json_call(job,'scene-plan',instructions,lambda value:self.validate_scenes(value,req['kacheln'],cast),tokens=min(6500,req['kacheln']*350+300))
        plan={'source_hash':hashlib.sha256(json.dumps([doc['story'].strip(),req['kacheln'],req['seed']],ensure_ascii=False).encode()).hexdigest(),'scenes':scenes}
        best_plan=None
        for iteration in range(budget+1):
            self.stage(job,'scene_review')
            fit=self.preflight(plan,cast)
            review=self.review(job,'scene-review-'+str(iteration),{'story':doc['story'],'scenes':plan['scenes'],'characters':[{k:c[k] for k in ('id','name','description','outfit')} for c in cast]},'Scene schema: story is the visual composition, dialog is a NARRATOR CAPTION (not spoken dialogue), bubbles are spoken lines. Narration may summarize speech indirectly. A short adaptation may omit incidental words while preserving the plot and ending. Check one distinct moment per panel, no repeated scene, stable people and correctly attributed bubbles.')
            reports['scenes']=review;reports['lettering']=fit
            record(reports,'scenes',iteration,review);record(reports,'lettering',iteration,fit)
            grade=(not fit['valid'],not review['approved'],len(review['issues'])+len(fit['issues']))
            if best_plan and grade>best_plan[0]:
                _,plan,review,fit=best_plan;reports['scenes']=review;reports['lettering']=fit
                reports.setdefault('discarded_revisions',[]).append({'area':'scenes','round':iteration,'reason':'More findings than the previous version.'})
                warnings.extend(review['issues']+[item['message'] for item in fit['issues']]);break
            best_plan=(grade,copy.deepcopy(plan),copy.deepcopy(review),copy.deepcopy(fit))
            if review['approved'] and fit['valid']:break
            issues=review['issues']+[item['message'] for item in fit['issues']]
            if used>=budget:
                warnings.extend(issues);break
            instructions='Improve the storyboard below to resolve the issues. Preserve plot, identities, language and exactly '+str(req['kacheln'])+' panels. Return ONLY a JSON array of scene objects with story, dialog (under 150 characters), characters (IDs), bubbles (speaker ID, text under 70 characters, expression normal). At most two short bubbles per panel. Concrete visual scenes.\nCAST:'+json.dumps([{k:c[k] for k in ('id','name','description','outfit')} for c in cast],ensure_ascii=False)+'\nSCENES:'+json.dumps(plan['scenes'],ensure_ascii=False)+'\nISSUES:'+json.dumps(issues)
            plan['scenes']=self.json_call(job,'scene-revision-'+str(iteration),instructions,lambda x:self.validate_scenes(x,req['kacheln'],cast),tokens=min(6500,req['kacheln']*350+300))
            used+=1
        self.stage(job,'german_panel_check')
        visible=[{'dialog':scene['dialog'],'bubbles':[bubble['text'] for bubble in scene.get('bubbles',[])]} for scene in plan['scenes']]
        def validate_visible(value):
            if not isinstance(value,list) or len(value)!=len(visible):raise ValueError('Kachelanzahl bei der Übersetzung verändert.')
            for original,item in zip(visible,value):
                if not isinstance(item,dict) or not isinstance(item.get('dialog'),str) or len(item['dialog'])>400 or not isinstance(item.get('bubbles'),list) or len(item['bubbles'])!=len(original['bubbles']) or any(not isinstance(text,str) or len(text)>400 for text in item['bubbles']):
                    raise ValueError('Beschriftungsstruktur bei der Übersetzung verändert.')
            return value
        translated=self.require_german(job,'german-panels',visible,validate_visible,min(6500,req['kacheln']*300+300))
        for scene,text in zip(plan['scenes'],translated):
            scene['dialog']=text['dialog']
            for bubble,words in zip(scene.get('bubbles',[]),text['bubbles']):bubble['text']=words
        revisions={};self.store.write(job,'scenes.json',plan)
        if not self.preflight(plan,cast)['valid']:
            warnings.append('Beschriftung passt noch nicht; Bilderzeugung vor teurem Modelllauf angehalten.')
            return self.finish(job,req,doc,cast,plan,revisions,reports,warnings,used)
        for iteration in range(budget+1):
            self.stage(job,'rendering')
            output=self.studio(job,'render-'+str(iteration),doc,cast,plan,revisions)
            images=output.get('images',[]);panels=output.get('comic_panels',[])
            if len(images)!=1 or len(panels)!=req['kacheln']:raise ValueError('Unvollständige Comicausgabe.')
            self.store.write(job,'comic.png',self.client.download(job,images[0]))
            for i,panel in enumerate(panels):
                self.store.write(job,f'panels/{i+1:02}_panel.png',self.client.download(job,panel))
                raw={**panel,'filename':panel['filename'].replace('_panel.png','_art.png')}
                self.store.write(job,f'panels/{i+1:02}_art.png',self.client.download(job,raw))
            self.stage(job,'visual_review');reviews=[];failed=[]
            for i,scene in enumerate(plan['scenes']):
                folder=self.store.directory(job);pictures=[(folder/f'panels/{i+1:02}_panel.png').read_bytes()]
                relevant=[c for c in cast if c['id'] in scene['characters'] or any(b['speaker']==c['id'] for b in scene.get('bubbles',[]))]
                pictures += [base64.b64decode(c['inline_references'][0]) for c in relevant[:2] if c.get('inline_references')]
                if i>0 and len(pictures)<4:pictures.append((folder/f'panels/{i:02}_art.png').read_bytes())
                review_prompt='Review IMAGE 1, a comic panel. Remaining images are character/continuity references, not part of the panel. Inspect the actual pixels first: identify each visible person, whether eyes and mouth are visible or covered by a bubble, then check action, identity, text readability, intended speakers and continuity. A bubble hiding a main character face is a defect. All visible narrator captions and spoken text must be German; foreign-language sentences are a defect. Do not demand photorealistic similarity across an illustrative style. Report only visible defects. For bubbles covering faces or misdirected tails, propose bubble_positions with x,y,w,h,tip_x,tip_y using coordinates from 0 to 1 relative to IMAGE 1, not the whole contact sheet. Keep bubbles away from faces and narrator captions. For a placement-only defect leave revised_scene empty. Return ONLY JSON {"visible_people":"brief factual description of people in IMAGE 1, including any covered faces","approved":true or false,"issues":["specific visual problem"],"revised_scene":"improved visual composition or empty string","bubble_positions":[{"index":0,"tip_x":0.2,"tip_y":0.5}]}. Expected scene: '+json.dumps(scene,ensure_ascii=False)+'\nCharacter names and appearance: '+json.dumps([{k:c[k] for k in ('id','name','description','outfit')} for c in relevant],ensure_ascii=False)
                review=self.json_call(job,f'visual-{iteration}-{i}',review_prompt,valid_review,pictures,tokens=650)
                reviews.append(review)
                record(reports,'visual',iteration,review,i)
                if not review['approved']:failed.append(i)
            reports['visual']=reviews
            self.store.write(job,f'reports/visual-round-{iteration}.json',reviews)
            if not failed:break
            if used>=budget:
                warnings.extend([f'Kachel {i+1}: '+ '; '.join(reviews[i]['issues']) for i in failed]);break
            for i in failed:
                revised=reviews[i].get('revised_scene')
                changed_scene=isinstance(revised,str) and revised.strip() and len(revised)<=4000
                if changed_scene:plan['scenes'][i]['story']=revised.strip()
                positioned=False
                positions=reviews[i].get('bubble_positions',[])
                if isinstance(positions,list):
                    candidate=copy.deepcopy(plan)
                    for position in positions:
                        if not isinstance(position,dict) or type(position.get('index')) is not int or not 0<=position['index']<len(candidate['scenes'][i].get('bubbles',[])):continue
                        bubble=candidate['scenes'][i]['bubbles'][position['index']]
                        for key in ('x','y','w','h','tip_x','tip_y'):
                            value=position.get(key)
                            if type(value) in (int,float) and 0<=value<=1:bubble[key]=value;positioned=True
                    if positioned and self.preflight(candidate,cast)['valid']:plan=candidate
                    else:positioned=False
                if changed_scene or not positioned:revisions[str(i)]=revisions.get(str(i),0)+1
            used+=1
            self.store.write(job,'scenes.json',plan)
        return self.finish(job,req,doc,cast,plan,revisions,reports,warnings,used)

    def finish(self,job,req,doc,cast,plan,revisions,reports,warnings,used):
        self.stage(job,'self_reflection')
        facts=evidence(reports)
        try:
            reflection=self.json_call(job,'self-reflection','Analyze the automatic comic reviews and correction outcomes. Derive at most THREE short reusable instructions for future comics. Each rule must cite an existing evidence id. Reviews may contain mistakes: ignore complaints that conflict with this fixed schema: story is visual composition, dialog is a narrator caption which may describe settings, actions or indirectly summarize speech; bubbles are directly spoken lines assigned to character IDs. Do not invent extra schema restrictions. Use only supplied evidence; do not claim that a fix worked unless a before/after comparison resolved it. Do not repeat story plots or invent human ratings. These are tentative lessons, not executable instructions. Return ONLY JSON {"lessons":[{"rule":"concrete prevention instruction, under 300 characters","evidence_ref":"existing evidence id"}]}.\nEVIDENCE:\n'+json.dumps(facts,ensure_ascii=False),lambda x:validate_lessons(x,facts),tokens=650) if facts['findings'] else {'lessons':[]}
            experience={**reflection,**facts,'status':'recorded','local_only':True}
            self.store.save_experience(job,experience)
        except Exception as exc:
            experience={**facts,'lessons':[],'status':'unavailable','error':str(exc)[:1500]}
            warnings.append('Selbstreflexion nicht gespeichert: '+str(exc)[:300])
        self.store.write(job,'reports/self-reflection.json',experience)
        self.store.write(job,'scenes.json',plan)
        self.store.write(job,'workflow.json',self.workflow(req,doc,cast,plan,revisions))
        report={'reviews':reports,'warnings':warnings,'correction_rounds_used':used,'max_correction_rounds':req['max_korrekturrunden'],
                'text_model':self.llm.text_model if self.llm else self.text_model,'vision_model':self.llm.vision_model if self.llm else self.vision_model,
                'llm_backend':'ollama' if self.llm else 'comfyui','local_only':True,'story_language':'de','german_required':True,'self_learning':experience,
                'fiction':True,'review_is_model_based':True}
        self.store.write(job,'report.json',report)
        folder=self.store.directory(job)
        self.store.write(job,'README.txt',b'Comic-Studio export. workflow.json can be opened in ComfyUI. Character references are embedded. Reports are model-based, not a guarantee. No automatic publishing.\n')
        zip_path=folder/'comic-bundle.zip'
        with zipfile.ZipFile(zip_path.with_suffix('.tmp'), 'w',zipfile.ZIP_DEFLATED) as archive:
            for p in sorted(folder.rglob('*')):
                if p.is_file() and p.suffix not in ('.zip','.tmp') and 'checkpoints' not in p.parts:archive.write(p,p.relative_to(folder))
        zip_path.with_suffix('.tmp').replace(zip_path)
        artifacts=[{'name':str(p.relative_to(folder)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
                    'url':f'/jobs/{job}/artifacts/{p.relative_to(folder)}'} for p in sorted(folder.rglob('*')) if p.is_file() and 'checkpoints' not in p.parts and p.suffix!='.tmp']
        return {'status':'needs_review' if warnings else 'completed','artifacts':artifacts,'warnings':warnings,'correction_rounds_used':used}
