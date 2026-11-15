import time
from fastapi.testclient import TestClient
from gpu.service import create_app, Jobs

KEY='x'*32
HEADERS={'Authorization':'Bearer '+KEY}

def test_real_worker_queue_persistence_download_and_failure(tmp_path,monkeypatch):
    monkeypatch.setenv('LIPSYNC_ENGINE_KEY',KEY)
    def render(folder): (folder/'result.mp4').write_bytes(b'worker-output')
    app=create_app(tmp_path,renderer=render,start_worker=False)
    with TestClient(app) as client:
        assert client.post('/jobs').status_code==401
        response=client.post('/jobs',headers=HEADERS,files={'video':('v.mp4',b'video'),'audio':('a.wav',b'audio')})
        assert response.status_code==202
        job=response.json()['job_id']
        assert client.get('/jobs/'+job+'/result',headers=HEADERS).status_code==409
        assert app.state.jobs.run_next(render)
        assert Jobs(tmp_path).get(job)['status']=='succeeded'
        assert client.get('/jobs/'+job+'/result',headers=HEADERS).content==b'worker-output'
        assert not (tmp_path/job/'video.mp4').exists()
        failed=app.state.jobs.add(b'v',b'a')['job_id']
        def fail(folder):raise RuntimeError('Internal details should not leak')
        app.state.jobs.run_next(fail)
        assert app.state.jobs.get(failed)['status']=='failed'
        assert 'Internal details' not in client.get('/jobs/'+failed,headers=HEADERS).text

def test_capacity_recovery_expiry_and_missing_fields(tmp_path,monkeypatch):
    monkeypatch.setenv('LIPSYNC_ENGINE_KEY',KEY)
    app=create_app(tmp_path,start_worker=False)
    with TestClient(app) as client:
        assert client.post('/jobs',headers=HEADERS,files={'video':('v.mp4',b'v')}).status_code==422
        ids=[app.state.jobs.add(b'v',b'a')['job_id'] for _ in range(3)]
        assert client.post('/jobs',headers=HEADERS,files={'video':('v.mp4',b'v'),'audio':('a.wav',b'a')}).status_code==429
        app.state.jobs.update(ids[0],'running',10)
        app.state.jobs.recover()
        assert app.state.jobs.get(ids[0])['status']=='failed'
        with app.state.jobs.db() as db:db.execute('UPDATE jobs SET created=? WHERE id=?',(time.time()-90000,ids[0]))
        app.state.jobs.prune()
        assert client.get('/jobs/'+ids[0],headers=HEADERS).status_code==404

def test_gateway_to_worker_with_real_mp4(tmp_path,monkeypatch):
    """Exercise real upload/store/download; FFmpeg substitutes for AI inference."""
    import subprocess
    import shutil
    import httpx
    import pytest
    from app import app as gateway
    if not shutil.which('ffmpeg'):pytest.skip('FFmpeg is required')
    video=tmp_path/'source.mp4';audio=tmp_path/'narration.wav'
    subprocess.run(['ffmpeg','-y','-v','error','-f','lavfi','-i','color=c=blue:s=160x120:r=25:d=1','-c:v','libx264',str(video)],check=True)
    subprocess.run(['ffmpeg','-y','-v','error','-f','lavfi','-i','sine=frequency=440:duration=1','-ar','16000',str(audio)],check=True)
    def render(folder):
        subprocess.run(['ffmpeg','-y','-v','error','-i',str(folder/'video.mp4'),'-i',str(folder/'audio'),'-map','0:v','-map','1:a','-c:v','copy','-c:a','aac','-shortest',str(folder/'result.mp4')],check=True)
    engine=create_app(tmp_path/'jobs',renderer=render,start_worker=False)
    monkeypatch.setenv('LIPSYNC_ENGINE_KEY',KEY)
    monkeypatch.setenv('LIPSYNC_JOBS_URL','https://gpu.example/jobs')
    monkeypatch.setenv('ZEMAVOICE_API_KEY','test-private-key')
    original=httpx.AsyncClient
    monkeypatch.setattr('lipsync_api.httpx.AsyncClient',lambda **kwargs:original(transport=httpx.ASGITransport(app=engine),**kwargs))
    with TestClient(gateway) as client:
        headers={'x-zemavoice-key':'test-private-key'}
        response=client.post('/v1/lipsync/jobs',headers=headers,files={'video':('v.mp4',video.read_bytes()),'audio':('a.wav',audio.read_bytes())})
        assert response.status_code==202
        job=response.json()['job_id']
        assert engine.state.jobs.run_next(render)
        assert client.get('/v1/lipsync/jobs/'+job,headers=headers).json()['status']=='succeeded'
        result=client.get('/v1/lipsync/jobs/'+job+'/result',headers=headers)
        assert result.status_code==200
        downloaded=tmp_path/'download.mp4';downloaded.write_bytes(result.content)
        import json
        probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(downloaded)]))
        assert {s['codec_type'] for s in probe['streams']}=={'audio','video'}
