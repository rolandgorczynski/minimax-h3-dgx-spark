"""Bearbeitbare Geschichten mit Versionsprüfung und getrennten Renderaufträgen."""
import copy
import json
import secrets
import shutil
import threading
import uuid
from functools import wraps

from engine import ID, STYLES, validate_request
from storage import now
from character_profiles import validate as validate_profile


class Conflict(ValueError): pass


def serialized(method):
    @wraps(method)
    def call(self,*args,**kwargs):
        with self.lock:return method(self,*args,**kwargs)
    return call


def validate_definition(value):
    if not isinstance(value,dict) or value.get('mode') not in ('editorial','automatic'):
        raise ValueError('Modus editorial oder automatic wählen.')
    if not isinstance(value.get('name'),str):raise ValueError('Titel als Text eingeben.')
    name=value['name'].strip()
    if not name or len(name)>200:raise ValueError('Titel mit 1–200 Zeichen eingeben.')
    payload=copy.deepcopy(value.get('payload',{}))
    if not isinstance(payload,dict):raise ValueError('Ungültige Definition.')
    if value['mode']=='automatic':payload=validate_request(payload)
    else:
        if payload.get('style') not in STYLES:raise ValueError('Unbekannter Comic-Stil.')
        if not isinstance(payload.get('article',''),str) or len(payload.get('article',''))>16000:raise ValueError('Artikel maximal 16000 Zeichen.')
        scenes=payload.get('scenes',[])
        if not isinstance(scenes,list) or len(scenes)>12:raise ValueError('Maximal zwölf Szenen.')
        for scene in scenes:
            if not isinstance(scene,dict) or not isinstance(scene.get('story'),str) or len(scene['story'])>4000 or not isinstance(scene.get('dialog',''),str) or len(scene.get('dialog',''))>400:
                raise ValueError('Ungültige Szene oder zu langer Text.')
        payload['title']=name;payload['scenes']=scenes
        revisions=payload.get('revisions',{})
        if not isinstance(revisions,dict) or any(not str(k).isdigit() or type(v) is not int or v<0 for k,v in revisions.items()):raise ValueError('Ungültige Kachelrevisionen.')
        payload['revisions']={str(k):v for k,v in revisions.items() if 0<=int(k)<len(scenes)}
        profiles=payload.get('characters',[])
        if not isinstance(profiles,list) or len(profiles)>8:raise ValueError('Maximal acht Figuren pro Geschichte.')
        for profile in profiles:validate_profile(profile)
        payload.setdefault('characters',[]);payload.setdefault('library_ids',[]);payload.setdefault('seed',1984)
        validate_request({'kacheln':len(scenes) or 1,'stil':payload['style'],'seed':payload['seed'],'figuren_ids':payload['library_ids'],'signatur':payload.get('signature','')})
    return {'mode':value['mode'],'name':name,'payload':payload}


class Stories:
    def __init__(self,store):
        self.store=store;self.lock=threading.RLock()
        with store.connect() as db:db.execute('CREATE TABLE IF NOT EXISTS stories (id TEXT PRIMARY KEY, doc TEXT NOT NULL)')

    def list(self):
        with self.store.connect() as db:rows=db.execute('SELECT doc FROM stories ORDER BY rowid DESC').fetchall()
        return [{k:v for k,v in json.loads(r['doc']).items() if k!='payload'} for r in rows]

    def outputs(self,ident):
        with self.store.connect() as db:rows=db.execute('SELECT doc FROM jobs').fetchall()
        return [j for row in rows if (j:=json.loads(row['doc'])).get('story_id')==ident]

    def get(self,ident):
        with self.store.connect() as db:row=db.execute('SELECT doc FROM stories WHERE id=?',(ident,)).fetchone()
        if not row:raise KeyError(ident)
        return json.loads(row['doc'])

    @serialized
    def save(self,value,ident=None,version=None):
        clean=validate_definition(value)
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            old=None
            if ident:
                row=db.execute('SELECT doc FROM stories WHERE id=?',(ident,)).fetchone()
                if not row:raise KeyError(ident)
                old=json.loads(row['doc'])
                if type(version) is not int or version!=old['version']:raise Conflict('Die Geschichte wurde inzwischen geändert. Bitte neu laden.')
            ident=ident or uuid.uuid4().hex
            doc={**clean,'id':ident,'version':old['version']+1 if old else 1,'created_at':old['created_at'] if old else now(),'updated_at':now()}
            db.execute('INSERT INTO stories VALUES (?,?) ON CONFLICT(id) DO UPDATE SET doc=excluded.doc',(ident,json.dumps(doc)))
        return doc

    @serialized
    def import_job(self,ident):
        job=self.store.get(ident)
        if not job:raise KeyError(ident)
        root=self.store.directory(ident)
        if (root/'editorial-source.json').exists():payload=json.loads((root/'editorial-source.json').read_text())
        elif all((root/name).exists() for name in ('story.json','scenes.json','characters.json')):
            story=json.loads((root/'story.json').read_text());plan=json.loads((root/'scenes.json').read_text())
            payload={'title':story['title'],'article':story['story'],'scenes':plan['scenes'],'characters':[],
                     'style':job['request']['stil'],'seed':job['request']['seed'],'signature':job['request']['signatur']}
        else:return self.save({'mode':'automatic','name':job.get('story_title') or 'Kopie des Auftrags','payload':job['request']})
        if (root/'characters.json').exists():
            # Retain the job's private reference snapshots, even if library figures were later removed.
            if payload.get('narrator_badge') and payload.get('library_ids'):
                payload['narrator_character_id']=payload['library_ids'][0]
            payload['characters']=json.loads((root/'characters.json').read_text());payload['library_ids']=[]
        return self.save({'mode':'editorial','name':payload['title'],'payload':payload})

    @serialized
    def plan(self,ident,version):
        story=self.get(ident)
        if type(version) is not int or version!=story['version']:raise Conflict('Geschichte wurde geändert. Bitte neu laden.')
        if story['mode']!='editorial':raise ValueError('Szenenplanung benötigt einen Artikel.')
        if any(j.get('planning_mode') and j['status'] in ('queued','running') for j in self.outputs(ident)):
            raise Conflict('Die Szenen für diese Geschichte werden bereits erstellt.')
        source=story['payload']
        if not source.get('article','').strip():raise ValueError('Zuerst den Artikel einfügen.')
        count=source.get('panel_count',len(source['scenes']) or 12)
        request=validate_request({'kacheln':count,'stil':source['style'],'seed':source['seed'],'max_korrekturrunden':0})
        ident_job=uuid.uuid4().hex;self.store.create(ident_job,request,initial_status='editing')
        self.store.update(ident_job,planning_mode=True,planning_source=story,story_id=ident,story_version=version)
        self.store.stage(ident_job,'queued',status='queued')
        return self.store.get(ident_job)

    @serialized
    def enqueue(self,ident,version):
        story=self.get(ident)
        if type(version) is not int or version!=story['version']:raise Conflict('Die Geschichte wurde geändert. Bitte neu laden.')
        source=copy.deepcopy(story['payload']);job_id=uuid.uuid4().hex
        seed=secrets.randbelow(2147483648)
        if story['mode']=='automatic':request={**source,'seed':seed}
        else:
            from engine import Engine
            if not source['article'].strip() or not source['scenes']:raise ValueError('Zuerst Geschichte und Szenenplan ausfüllen oder ein Storyboard importieren.')
            cast=source.get('characters',[])
            if not cast and not source.get('library_ids'):raise ValueError('Figurenprofile fehlen. Ein vollständiges Storyboard importieren.')
            if len(cast)>8 or any(not isinstance(c,dict) or not ID.fullmatch(c.get('id','')) for c in cast):raise ValueError('Ungültige Figurenprofile.')
            known=cast+[{'id':i,'name':i} for i in source.get('library_ids',[]) if i not in {c['id'] for c in cast}]
            Engine.validate_scenes(None,copy.deepcopy(source['scenes']),len(source['scenes']),known)
            source['seed']=seed
            request=validate_request({'kacheln':len(source['scenes']),'stil':source['style'],'seed':seed,'max_korrekturrunden':0,
                                      'figuren_ids':source.get('library_ids',[]),'signatur':source.get('signature','')})
            # Reuse private identities for rerenders; only new or changed profiles need new portraits.
            with self.store.connect() as db:
                rows=db.execute('SELECT doc FROM jobs ORDER BY rowid DESC').fetchall()
            previous=next((json.loads(r['doc']) for r in rows if json.loads(r['doc']).get('story_id')==ident),None)
            if previous:
                path=self.store.directory(previous['id'])/'characters.json'
                saved={c['id']:c for c in json.loads(path.read_text())} if path.exists() else {}
                for c in cast:
                    old=saved.get(c['id'],{})
                    if not c.get('inline_references') and old.get('inline_references') and all(c.get(k)==old.get(k) for k in ('description','outfit')):
                        c['inline_references']=old['inline_references'];c['references']=[]
        # Keep it unclaimable until its complete snapshot has been stored.
        self.store.create(job_id,request,initial_status='editing')
        try:
            if story['mode']=='editorial':self.store.write(job_id,'editorial-source.json',source)
            self.store.update(job_id,story_id=ident,story_version=version,editorial_mode=story['mode']=='editorial')
            self.store.stage(job_id,'queued',status='queued')
        except Exception:
            self.store.stage(job_id,'failed',status='failed');raise
        return self.store.get(job_id)

    @serialized
    def improve(self,ident,style=None):
        parent=self.store.get(ident)
        if not parent:raise KeyError(ident)
        if parent['status'] not in ('completed','needs_review'):raise Conflict('Zuerst eine fertige Ausgabe auswählen.')
        if not parent.get('feedback'):raise ValueError('Zuerst eine Bewertung zu dieser Ausgabe speichern.')
        style=style or parent['request']['stil']
        if style not in STYLES:raise ValueError('Unbekannter Comic-Stil.')
        with self.store.connect() as db:all_jobs=[json.loads(r['doc']) for r in db.execute('SELECT doc FROM jobs').fetchall()]
        previous=[j for j in all_jobs if j.get('improvement_mode') and j.get('parent_job')==ident]
        if any(j['status'] in ('queued','running') for j in previous):raise Conflict('Diese Ausgabe wird bereits verbessert.')
        root=self.store.directory(ident)
        if (root/'editorial-source.json').exists():source=json.loads((root/'editorial-source.json').read_text())
        else:
            story=json.loads((root/'story.json').read_text());plan=json.loads((root/'scenes.json').read_text())
            source={'title':story['title'],'article':story['story'],'scenes':plan['scenes'],'seed':parent['request']['seed'],'signature':parent['request']['signatur']}
        if not (root/'characters.json').exists():raise ValueError('Figurenreferenzen fehlen in dieser Ausgabe.')
        source['characters']=json.loads((root/'characters.json').read_text())
        if source.get('narrator_badge') and source.get('library_ids'):source['narrator_character_id']=source['library_ids'][0]
        source['library_ids']=[];source['style']=style
        # Panel count is derived only from the rated output, never from current dashboard controls.
        count=len(source['scenes'])
        request=validate_request({'kacheln':count,'stil':style,'seed':source.get('seed',parent['request']['seed']),
                                  'max_korrekturrunden':0,'signatur':source.get('signature','')})
        job_id=uuid.uuid4().hex;self.store.create(job_id,request,initial_status='editing')
        self.store.write(job_id,'improvement-input.json',{'source':source,'feedback':parent['feedback'],
            'parent_job':ident,'original_style':parent['request']['stil'],'attempt':len(previous)+1})
        self.store.update(job_id,improvement_mode=True,editorial_mode=True,parent_job=ident,
                          story_id=parent.get('story_id'),story_version=parent.get('story_version'),
                          feedback_at=parent.get('feedback_at'),improvement_title=source['title'])
        self.store.stage(job_id,'queued',status='queued')
        return self.store.get(job_id)

    @serialized
    def delete(self,ident,version):
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT doc FROM stories WHERE id=?',(ident,)).fetchone()
            if not row:raise KeyError(ident)
            if type(version) is not int or json.loads(row['doc'])['version']!=version:raise Conflict('Die Geschichte wurde inzwischen geändert. Bitte neu laden.')
            jobs=[json.loads(r['doc']) for r in db.execute('SELECT doc FROM jobs').fetchall()]
            owned=[j for j in jobs if j.get('story_id')==ident]
            if any(j['status'] in ('queued','running') for j in owned):raise Conflict('Eine Ausgabe wird noch erzeugt. Danach kann die Geschichte gelöscht werden.')
            for job in owned:self._delete_row(db,job['id'])
            db.execute('DELETE FROM stories WHERE id=?',(ident,))
        for job in owned:shutil.rmtree(self.store.root/'jobs'/job['id'],ignore_errors=True)
        return len(owned)

    @serialized
    def delete_job(self,ident):
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');row=db.execute('SELECT doc FROM jobs WHERE id=?',(ident,)).fetchone()
            if not row:raise KeyError(ident)
            if json.loads(row['doc'])['status'] in ('queued','running'):raise Conflict('Laufende oder wartende Ausgaben können nicht gelöscht werden.')
            dependents=[json.loads(r['doc']) for r in db.execute('SELECT doc FROM jobs').fetchall()]
            if any(j.get('parent_job')==ident and j.get('improvement_mode') and j['status'] in ('queued','running') for j in dependents):
                raise Conflict('Die Ausgabe wird gerade als Grundlage einer Verbesserung verwendet.')
            self._delete_row(db,ident)
        shutil.rmtree(self.store.root/'jobs'/ident,ignore_errors=True)

    @staticmethod
    def _delete_row(db,ident):
        db.execute('DELETE FROM feedback WHERE job_id=?',(ident,));db.execute('DELETE FROM experiences WHERE job_id=?',(ident,))
        db.execute('DELETE FROM telegram_jobs WHERE job_id=?',(ident,))
        db.execute('DELETE FROM jobs WHERE id=?',(ident,))
