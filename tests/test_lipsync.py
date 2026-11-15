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
