from html.parser import HTMLParser
import json
from pathlib import Path
from fastapi.testclient import TestClient
from app import app

class Elements(HTMLParser):
    def __init__(self):super().__init__();self.ids=[];self.scripts=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if 'id' in attrs:self.ids.append(attrs['id'])
        if tag=='script' and 'src' in attrs:self.scripts.append(attrs['src'])


def test_workspace_catalog_and_required_controls():
    client=TestClient(app)
    page=client.get('/');parser=Elements();parser.feed(page.text)
    assert len(parser.ids)==len(set(parser.ids)), 'Duplicate control IDs'
    for required in ('workspace','accountForm','voicePanel','libraryPanel','videoPanel','dialoguePanel','lipPanel','downloadsPanel','key','voice','face','videoTool'):
        assert required in parser.ids
    assert 'id="workspace" hidden' in page.text
    for script in parser.scripts:assert client.get(script).status_code==200
    text=client.get('/voice-profiles.js').text
    profiles=json.loads(text.split('Object.freeze(',1)[1].rsplit(');',1)[0])
    assert len(profiles)==20 and len({v['id'] for v in profiles})==20
    assert sum(v['gender']=='Female' for v in profiles)==10
    assert all(v['available'] is False for v in profiles), 'Unverified profiles must not appear usable'
    assert client.get('/workspace.css').status_code==200
    assert client.get('/.env').status_code==404


def test_embedded_tools_allow_only_same_origin_frames():
    client=TestClient(app)
    assert "frame-ancestors 'none'" in client.get('/').headers['content-security-policy']
    for path in ('/video','/studio'):
        response=client.get(path)
        assert response.headers['x-frame-options']=='SAMEORIGIN'
        assert "frame-ancestors 'self'" in response.headers['content-security-policy']


def test_design_preview_is_not_a_login_or_production_route(monkeypatch):
    client=TestClient(app)
    response=client.get('/preview')
    assert response.status_code==200
    assert '/preview.js' in response.text
    assert 'src="/firebase-auth.js"' not in response.text
    monkeypatch.setattr('app.PROD', True)
    assert client.get('/preview').status_code==404
