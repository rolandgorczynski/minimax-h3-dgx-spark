"""Durable job state; no connection to ComfyUI's files or database."""
import hashlib
import json
from pathlib import Path
import sqlite3
import uuid
from datetime import datetime, timezone


def now():return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self,root):
        self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True)
        self.db=self.root/'jobs.sqlite3'
        with self.connect() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, request_hash TEXT NOT NULL, status TEXT NOT NULL, doc TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS feedback (job_id TEXT PRIMARY KEY, payload TEXT NOT NULL, created_at TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS experiences (job_id TEXT PRIMARY KEY, payload TEXT NOT NULL, created_at TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS integration_state (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS telegram_jobs (job_id TEXT PRIMARY KEY, bot_id INTEGER NOT NULL, chat_id INTEGER NOT NULL, ack_sent INTEGER NOT NULL DEFAULT 0, result_sent INTEGER NOT NULL DEFAULT 0, retry_at REAL NOT NULL DEFAULT 0)')

    def connect(self):
        db=sqlite3.connect(self.db,timeout=30);db.row_factory=sqlite3.Row;return db

    def get(self,ident):
        with self.connect() as db:row=db.execute('SELECT doc FROM jobs WHERE id=?',(ident,)).fetchone()
        return json.loads(row['doc']) if row else None

    def integration_get(self,key):
        with self.connect() as db:row=db.execute('SELECT value FROM integration_state WHERE key=?',(key,)).fetchone()
        return json.loads(row['value']) if row else None

    def integration_set(self,key,value):
        with self.connect() as db:db.execute('INSERT INTO integration_state VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,json.dumps(value)))

    def telegram_attach(self,bot,chat,ident):
        with self.connect() as db:db.execute('INSERT INTO telegram_jobs (job_id,bot_id,chat_id) VALUES (?,?,?) ON CONFLICT(job_id) DO NOTHING',(ident,bot,chat))

    def telegram_pending(self,bot):
        with self.connect() as db:return [dict(row) for row in db.execute('SELECT * FROM telegram_jobs WHERE bot_id=? AND result_sent=0',(bot,)).fetchall()]

    def telegram_update(self,ident,**values):
        if set(values)-{'ack_sent','result_sent','retry_at'}:raise ValueError('Ungültiges Zustellungsfeld.')
        with self.connect() as db:db.execute('UPDATE telegram_jobs SET '+','.join(key+'=?' for key in values)+' WHERE job_id=?',(*values.values(),ident))

    def telegram_latest(self,bot,chat):
        with self.connect() as db:row=db.execute('SELECT job_id FROM telegram_jobs WHERE bot_id=? AND chat_id=? ORDER BY rowid DESC LIMIT 1',(bot,chat)).fetchone()
        return self.get(row['job_id']) if row else None

    def list(self):
        with self.connect() as db:rows=db.execute('SELECT doc FROM jobs ORDER BY rowid DESC LIMIT 100').fetchall()
        return [json.loads(row['doc']) for row in rows]

    def create(self,ident,request,initial_status='queued'):
        if initial_status not in ('queued','editing'):raise ValueError('Ungültiger Startzustand.')
        fingerprint=hashlib.sha256(json.dumps(request,sort_keys=True).encode()).hexdigest()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT * FROM jobs WHERE id=?',(ident,)).fetchone()
            if row:
                if row['request_hash']!=fingerprint:raise ValueError('Diese Auftrags-ID gehört zu anderen Parametern.')
                return json.loads(row['doc']),False
            if db.execute("SELECT COUNT(*) FROM jobs WHERE status IN ('queued','running')").fetchone()[0]>=32:
                raise OverflowError('Die Auftragswarteschlange ist voll.')
            doc={'id':ident,'request':request,'status':initial_status,'stage':initial_status,'created_at':now(),'updated_at':now(),
                 'steps':{},'events':[],'artifacts':[],'cleanup_pending':False}
            db.execute('INSERT INTO jobs VALUES (?,?,?,?)',(ident,fingerprint,initial_status,json.dumps(doc)))
            return doc,True

    def update(self,ident,**changes):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT doc FROM jobs WHERE id=?',(ident,)).fetchone()
            if not row:raise KeyError(ident)
            doc=json.loads(row['doc']);doc.update(changes);doc['updated_at']=now()
            db.execute('UPDATE jobs SET status=?,doc=? WHERE id=?',(doc['status'],json.dumps(doc),ident))
            return doc

    def stage(self,ident,name,**changes):
        doc=self.get(ident);events=doc['events']+[{'at':now(),'stage':name}]
        return self.update(ident,stage=name,events=events[-200:],**changes)

    def claim(self):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute("SELECT id,doc FROM jobs WHERE status='queued' ORDER BY rowid LIMIT 1").fetchone()
            if not row:return None
            doc=json.loads(row['doc']);doc['status']='running';doc['updated_at']=now()
            db.execute('UPDATE jobs SET status=?,doc=? WHERE id=?',('running',json.dumps(doc),row['id']))
            return doc

    def recover(self):
        with self.connect() as db:
            rows=db.execute("SELECT id,doc FROM jobs WHERE status='running'").fetchall()
            for row in rows:
                doc=json.loads(row['doc']);doc['status']='queued';doc['stage']='resuming';doc['recovering']=True
                db.execute('UPDATE jobs SET status=?,doc=? WHERE id=?',('queued',json.dumps(doc),row['id']))

    def save_feedback(self,ident,value):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT doc FROM jobs WHERE id=?',(ident,)).fetchone()
            if not row:raise KeyError(ident)
            doc=json.loads(row['doc'])
            if doc['status'] not in ('completed','needs_review'):raise ValueError('Erst einen fertigen Entwurf bewerten.')
            if not (self.directory(ident)/'story.json').is_file():raise ValueError('Keine Geschichte zum Bewerten vorhanden.')
            db.execute('INSERT INTO feedback VALUES (?,?,?) ON CONFLICT(job_id) DO UPDATE SET payload=excluded.payload,created_at=excluded.created_at',
                       (ident,json.dumps(value),now()))
            doc.update(feedback=value,feedback_at=now(),updated_at=now())
            db.execute('UPDATE jobs SET doc=? WHERE id=?',(json.dumps(doc),ident))
        return doc

    def preferences(self):
        from feedback import CRITERIA
        with self.connect() as db:
            rows=db.execute('SELECT job_id,payload FROM feedback ORDER BY created_at DESC').fetchall()
        values=[json.loads(row['payload']) for row in rows]
        averages={}
        for key in CRITERIA:
            scores=[value.get('bewertungen',{})[key] for value in values if key in value.get('bewertungen',{})]
            if scores:averages[key]=round(sum(scores)/len(scores),2)
        examples=[]
        for row in rows[:10]:
            story_path=self.directory(row['job_id'])/'story.json'
            if not story_path.is_file():continue
            story=json.loads(story_path.read_text());value=json.loads(row['payload'])
            examples.append({'job_id':row['job_id'],'title':story.get('title',''),'story_excerpt':story.get('story','')[:800],**value})
        return {'criteria':CRITERIA,'rated_story_count':len(rows),'average_ratings':averages,'rated_examples':examples}

    def next_story(self,ident):
        parent=self.get(ident)
        if not parent:raise KeyError(ident)
        if parent['status'] not in ('completed','needs_review','failed'):raise ValueError('Der vorherige Auftrag läuft noch.')
        # Deterministic ID makes retries safe; a chain progresses from each new job.
        next_id=uuid.uuid5(uuid.UUID(ident),'next-story').hex
        request={**parent['request'],'thema':'','seed':(parent['request']['seed']+104729)%2147483648}
        job,created=self.create(next_id,request)
        if created:job=self.update(next_id,parent_job=ident)
        self.update(ident,next_job_id=next_id)
        return job,created

    def save_experience(self,ident,value):
        with self.connect() as db:
            db.execute('INSERT INTO experiences VALUES (?,?,?) ON CONFLICT(job_id) DO UPDATE SET payload=excluded.payload',
                       (ident,json.dumps(value),now()))

    def learning_memory(self):
        from learning import evidence
        with self.connect() as db:
            count=db.execute('SELECT COUNT(*) FROM experiences').fetchone()[0]
            rows=db.execute('SELECT job_id,payload FROM experiences ORDER BY created_at DESC LIMIT 30').fetchall()
        rules=[];seen=set()
        for row in rows:
            for rule in json.loads(row['payload']).get('lessons',[]):
                key=rule['rule'].casefold()
                if key not in seen and len(rules)<12:
                    rules.append({**rule,'source_job':row['job_id']});seen.add(key)
        # Existing comics provide observations too, even before the first reflection.
        observations=[]
        for job in self.list():
            if job['status'] not in ('completed','needs_review'):continue
            path=self.directory(job['id'])/'report.json'
            if path.is_file():
                facts=evidence(json.loads(path.read_text()).get('reviews',{}))
                observations.append({'source_job':job['id'],'findings':facts['findings'][-4:],'comparisons':facts['comparisons'][:6]})
            if len(observations)>=3:break
        return {'analyzed_runs':count,'rules':rules,'recent_observations':observations,'model_based':True}

    def directory(self,ident):
        folder=self.root/'jobs'/ident;folder.mkdir(parents=True,exist_ok=True);return folder

    def write(self,ident,name,value):
        path=self.directory(ident)/name;path.parent.mkdir(parents=True,exist_ok=True)
        data=value if isinstance(value,bytes) else (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode()
        tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_bytes(data);tmp.replace(path)
        return path
