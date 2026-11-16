import httpx
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)
HEADERS = {'x-zemavoice-key': 'test-private-key'}

def test_auth_and_unconfigured_engine(monkeypatch):
    monkeypatch.setenv('ZEMAVOICE_API_KEY', 'test-private-key')
    monkeypatch.delenv('LIPSYNC_ENGINE_URL', raising=False)
    assert client.get('/v1/lipsync/status').status_code == 401
    assert client.get('/v1/lipsync/status', headers=HEADERS).json()['configured'] is False
    assert client.post('/v1/lipsync/render', headers=HEADERS).status_code == 503

def test_gateway_contract_and_secrets(monkeypatch):
    monkeypatch.setenv('ZEMAVOICE_API_KEY', 'test-private-key')
    monkeypatch.setenv('LIPSYNC_ENGINE_URL', 'https://gpu.example/render')
    monkeypatch.setenv('LIPSYNC_ENGINE_KEY', 'worker-secret')
    original = httpx.AsyncClient
    def upstream(request):
        assert request.headers['authorization'] == 'Bearer worker-secret'
        assert b'name="video"' in request.content
        assert b'name="audio"' in request.content
        return httpx.Response(200, content=b'mp4-test', headers={'content-type':'video/mp4'})
    monkeypatch.setattr('lipsync_api.httpx.AsyncClient', lambda **kwargs: original(transport=httpx.MockTransport(upstream), **kwargs))
    response=client.post('/v1/lipsync/render', headers=HEADERS, files={'video':('v.mp4',b'v'), 'audio':('a.wav',b'a')})
    assert response.status_code == 200
    assert response.content == b'mp4-test'
    assert 'worker-secret' not in client.get('/v1/lipsync/status', headers=HEADERS).text

def test_invalid_endpoint_and_content(monkeypatch):
    monkeypatch.setenv('ZEMAVOICE_API_KEY', 'test-private-key')
    monkeypatch.setenv('LIPSYNC_ENGINE_KEY', 'worker-secret')
    monkeypatch.setenv('LIPSYNC_ENGINE_URL', 'http://gpu.example/render')
    assert client.post('/v1/lipsync/render',headers=HEADERS).status_code==503
    monkeypatch.setenv('LIPSYNC_ENGINE_URL', 'https://gpu.example/render')
    assert client.post('/v1/lipsync/render',headers=HEADERS,json={}).status_code==415

def test_app_files_and_blob_playback():
    assert client.get('/video').status_code==200
    assert client.get('/manifest.webmanifest').json()['display']=='standalone'
    assert client.get('/app-icon.svg').status_code==200
    assert "media-src 'self' blob:" in client.get('/video').headers['content-security-policy']

def test_async_job_lifecycle_and_result(monkeypatch):
    monkeypatch.setenv('ZEMAVOICE_API_KEY','test-private-key')
    monkeypatch.setenv('LIPSYNC_JOBS_URL','https://gpu.example/jobs')
    monkeypatch.setenv('LIPSYNC_ENGINE_KEY','worker-secret')
    original=httpx.AsyncClient
    def upstream(request):
        assert request.headers['authorization']=='Bearer worker-secret'
        if request.method=='POST':
            return httpx.Response(202,json={'job_id':'job_123','status':'queued','progress':0,'secret':'must-not-leak'})
        if request.url.path.endswith('/result'):
            return httpx.Response(200,content=b'finished-mp4',headers={'content-type':'video/mp4'})
        return httpx.Response(200,json={'job_id':'job_123','status':'succeeded','progress':100})
    monkeypatch.setattr('lipsync_api.httpx.AsyncClient',lambda **kw: original(transport=httpx.MockTransport(upstream),**kw))
    response=client.post('/v1/lipsync/jobs',headers=HEADERS,files={'video':('v.mp4',b'v'),'audio':('a.wav',b'a')})
    assert response.status_code==202
    assert 'secret' not in response.json()
    assert client.get('/v1/lipsync/jobs/job_123',headers=HEADERS).json()['status']=='succeeded'
    assert client.get('/v1/lipsync/jobs/job_123/result',headers=HEADERS).content==b'finished-mp4'
    assert client.get('/v1/lipsync/jobs/job_123').status_code==401
    assert client.get('/v1/lipsync/jobs/bad.id',headers=HEADERS).status_code==400

def test_malformed_jobs_and_expired_results(monkeypatch):
    monkeypatch.setenv('ZEMAVOICE_API_KEY','test-private-key')
    monkeypatch.setenv('LIPSYNC_JOBS_URL','https://gpu.example/jobs')
    monkeypatch.setenv('LIPSYNC_ENGINE_KEY','worker-secret')
    original=httpx.AsyncClient
    def upstream(request):
        if request.url.path.endswith('/result'):return httpx.Response(404)
        return httpx.Response(200,json={'job_id':'different','status':'succeeded','progress':100})
    monkeypatch.setattr('lipsync_api.httpx.AsyncClient',lambda **kw: original(transport=httpx.MockTransport(upstream),**kw))
    assert client.get('/v1/lipsync/jobs/job_123',headers=HEADERS).status_code==502
    assert client.get('/v1/lipsync/jobs/job_123/result',headers=HEADERS).status_code==404

def test_profile_validation_and_queue_backpressure(monkeypatch):
    monkeypatch.setenv('ZEMAVOICE_API_KEY','test-private-key')
    monkeypatch.setenv('LIPSYNC_JOBS_URL','https://gpu.example/jobs')
    monkeypatch.setenv('LIPSYNC_ENGINE_KEY','worker-secret')
    original=httpx.AsyncClient
    seen=[]
    def upstream(request):
        seen.append(request.url.params['profile'])
        return httpx.Response(429)
    monkeypatch.setattr('lipsync_api.httpx.AsyncClient',lambda **kw:original(transport=httpx.MockTransport(upstream),**kw))
    files={'video':('v.mp4',b'v'),'audio':('a.wav',b'a')}
    assert client.post('/v1/lipsync/jobs?profile=fast',headers=HEADERS,files=files).status_code==429
    assert seen==['fast']
    assert client.post('/v1/lipsync/jobs?profile=unknown',headers=HEADERS,files=files).status_code==422

def test_transfer_backpressure_keeps_status_available(monkeypatch):
    from lipsync_api import MEDIA_SLOT
    monkeypatch.setenv('ZEMAVOICE_API_KEY','test-private-key')
    assert MEDIA_SLOT.acquire(blocking=False)
    try:
        assert client.post('/v1/lipsync/jobs',headers=HEADERS).status_code==429
        assert client.get('/v1/lipsync/status',headers=HEADERS).status_code==200
    finally:
        MEDIA_SLOT.release()
    # An error in the route must also release admission for the next request.
    monkeypatch.delenv('LIPSYNC_JOBS_URL',raising=False)
    assert client.post('/v1/lipsync/jobs',headers=HEADERS).status_code==503
    assert MEDIA_SLOT.acquire(blocking=False)
    MEDIA_SLOT.release()
