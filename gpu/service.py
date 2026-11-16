"""Single-process private GPU job service. Run separately from the Render web app."""
import hmac
import json
import os
import re
import shutil
import sqlite3
import subprocess
import threading
import time
import uuid
from contextlib import asynccontextmanager, contextmanager
from email.parser import BytesParser
from email.policy import default
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse

LIMIT = 40 * 1024 * 1024

class Jobs:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        with self.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, status TEXT, progress INTEGER, created REAL)')
            db.execute('CREATE INDEX IF NOT EXISTS jobs_status_created ON jobs(status, created)')

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.root / 'jobs.sqlite', timeout=15)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def add(self, video, audio, profile="quality"):
        job_id = uuid.uuid4().hex
        folder = self.root / job_id
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute("SELECT count(*) FROM jobs WHERE status IN ('queued','running')").fetchone()[0] >= 3:
                raise HTTPException(429, 'GPU queue is full; try later')
            folder.mkdir()
            try:
                (folder / 'video.mp4').write_bytes(video)
                (folder / 'audio').write_bytes(audio)
                (folder / 'options.json').write_text(json.dumps({'profile': profile}))
                db.execute('INSERT INTO jobs VALUES (?, ?, ?, ?)', (job_id, 'queued', 0, time.time()))
            except Exception:
                shutil.rmtree(folder, ignore_errors=True)
                raise
        return self.get(job_id)

    def get(self, job_id):
        if not re.fullmatch(r'[a-f0-9]{32}', job_id):
            raise HTTPException(404, 'Job not found')
        with self.db() as db:
            row = db.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
        if not row:
            raise HTTPException(404, 'Job not found')
        return {'job_id': row['id'], 'status': row['status'], 'progress': row['progress']}

    def update(self, job_id, status, progress):
        with self.db() as db:
            db.execute('UPDATE jobs SET status=?, progress=? WHERE id=?', (status, progress, job_id))

    def recover(self):
        # Never silently rerender interrupted jobs, which could duplicate GPU usage.
        with self.db() as db:
            db.execute("UPDATE jobs SET status='failed' WHERE status='running'")

    def prune(self):
        with self.db() as db:
            rows = db.execute("SELECT id FROM jobs WHERE created<? AND status NOT IN ('queued','running')", (time.time()-86400,)).fetchall()
            for row in rows:
                shutil.rmtree(self.root / row['id'], ignore_errors=True)
                db.execute('DELETE FROM jobs WHERE id=?', (row['id'],))

    def run_next(self, renderer):
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute("SELECT id FROM jobs WHERE status='queued' ORDER BY created LIMIT 1").fetchone()
            if not row:
                return False
            job_id = row['id']
            db.execute("UPDATE jobs SET status='running', progress=10 WHERE id=?", (job_id,))
        try:
            renderer(self.root / job_id)
            if not (self.root / job_id / 'result.mp4').is_file():
                raise RuntimeError('Renderer did not produce a result')
            self.update(job_id, 'succeeded', 100)
        except Exception:
            self.update(job_id, 'failed', 0)
            (self.root / job_id / 'result.mp4').unlink(missing_ok=True)
        finally:
            # Only final output and state survive; intermediate files can be large.
            folder = self.root / job_id
            for path in folder.iterdir():
                if path.name not in ('result.mp4', 'metrics.json'):
                    if path.is_dir(): shutil.rmtree(path, ignore_errors=True)
                    else: path.unlink(missing_ok=True)
        return True

def command_renderer(folder):
    command = json.loads(os.environ['LIPSYNC_RENDER_COMMAND'])
    if not isinstance(command, list) or not command or not all(isinstance(x, str) for x in command):
        raise ValueError('Render command must be a JSON string array')
    values = {'video': str(folder / 'video.mp4'), 'audio': str(folder / 'audio'), 'output': str(folder / 'result.mp4'), 'profile': json.loads((folder/'options.json').read_text()).get('profile','quality')}
    subprocess.run([part.format(**values) for part in command], check=True, timeout=1800,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def warm_renderer():
    from gpu.latentsync_backend import LatentSyncBackend
    from gpu.render_long import render_long
    backend = LatentSyncBackend()
    def run(folder):
        profile = json.loads((folder/'options.json').read_text())['profile']
        render_long(folder/'video.mp4', folder/'audio', folder/'result.mp4', profile, infer=backend.infer)
    return run

def create_app(root=None, renderer=command_renderer, start_worker=True):
    if renderer is command_renderer and os.getenv('LIPSYNC_WARM_MODEL') == '1':
        renderer = warm_renderer()
    jobs = Jobs(root or os.getenv('LIPSYNC_JOB_DIR', '/data/zemavoice-jobs'))
    stop = threading.Event()

    def loop():
        next_prune = 0.0
        while not stop.is_set():
            if time.monotonic() >= next_prune:
                jobs.prune()
                next_prune = time.monotonic() + 60
            if not jobs.run_next(renderer): stop.wait(1)

    @asynccontextmanager
    async def lifespan(app):
        if start_worker:
            if renderer is command_renderer and not os.getenv('LIPSYNC_RENDER_COMMAND'):
                raise RuntimeError('Set LIPSYNC_RENDER_COMMAND before starting the worker')
            jobs.recover()
            thread = threading.Thread(target=loop, daemon=True)
            thread.start()
        yield
        stop.set()

    app = FastAPI(title='ZemaVoice private GPU worker', lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.jobs = jobs

    def auth(authorization: str = Header(default='')):
        expected = os.getenv('LIPSYNC_ENGINE_KEY', '')
        if len(expected) < 32: raise HTTPException(503, 'Worker authentication is not configured')
        if not hmac.compare_digest(authorization, 'Bearer ' + expected): raise HTTPException(401, 'Unauthorized')

    @app.post('/jobs', dependencies=[Depends(auth)], status_code=202)
    async def submit(request: Request, profile: Literal["fast", "quality"] = "quality"):
        kind = request.headers.get('content-type', '')
        if not kind.lower().startswith('multipart/form-data;'): raise HTTPException(415, 'Multipart upload required')
        data = bytearray()
        async for chunk in request.stream():
            data.extend(chunk)
            if len(data) > LIMIT: raise HTTPException(413, 'Upload too large')
        try:
            message = BytesParser(policy=default).parsebytes(('Content-Type: '+kind+'\r\nMIME-Version: 1.0\r\n\r\n').encode()+data)
            files = {}
            for part in message.iter_parts():
                name = part.get_param('name', header='content-disposition')
                if name in files: raise ValueError('Duplicate field')
                if name not in ('video','audio'): raise ValueError('Unexpected field')
                payload = part.get_payload(decode=True)
                if not payload: raise ValueError('Empty file')
                files[name] = payload
            if set(files) != {'video', 'audio'}: raise ValueError('Missing media')
        except (ValueError, TypeError):
            raise HTTPException(422, 'Provide exactly one video and one audio file')
        return jobs.add(files['video'], files['audio'], profile)

    @app.get('/jobs/{job_id}', dependencies=[Depends(auth)])
    def state(job_id: str): return jobs.get(job_id)

    @app.get('/jobs/{job_id}/result', dependencies=[Depends(auth)])
    def result(job_id: str):
        state = jobs.get(job_id)
        if state['status'] != 'succeeded': raise HTTPException(409, 'Result not ready')
        return FileResponse(jobs.root / job_id / 'result.mp4', media_type='video/mp4', filename='zemavoice-lipsync.mp4', headers={'Cache-Control':'no-store'})

    return app
