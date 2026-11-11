import os
import secrets
import time
import uuid
from collections import defaultdict, deque
from pathlib import Path
from typing import Literal

import httpx
from fastapi import FastAPI, Header, HTTPException, Depends, Request
from fastapi.responses import FileResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field
from auth import router as auth_router

PROD = os.getenv('APP_ENV', 'development') == 'production'
app = FastAPI(title='ZemaVoice AI API', version='0.3.0', docs_url=None if PROD else '/docs', redoc_url=None, openapi_url=None if PROD else '/openapi.json')
BASE = 'https://api.addisassistant.com'
PUBLIC_DIR = Path(__file__).resolve().parent / 'public'
app.include_router(auth_router)

if os.getenv('ALLOWED_HOSTS'):
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=[h.strip() for h in os.getenv('ALLOWED_HOSTS', '').split(',') if h.strip()])

request_times = defaultdict(deque)

def authorize(request: Request, x_zemavoice_key: str | None = Header(default=None)):
    expected = os.getenv('ZEMAVOICE_API_KEY', '')
    if not expected or (PROD and len(expected) < 32):
        raise HTTPException(503, 'Server authentication is not configured')
    if not secrets.compare_digest(x_zemavoice_key or '', expected):
        raise HTTPException(401, 'Invalid API key')
    if request.method == 'POST':
        now = time.monotonic()
        bucket = request_times['private-beta']
        while bucket and bucket[0] < now - 3600:
            bucket.popleft()
        limit = int(os.getenv('HOURLY_GENERATION_LIMIT', '20'))
        if len(bucket) >= limit:
            raise HTTPException(429, 'Hourly private-beta generation limit reached')
        bucket.append(now)

@app.middleware('http')
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://www.gstatic.com; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' https://identitytoolkit.googleapis.com https://securetoken.googleapis.com https://www.googleapis.com https://firebaseapp.com https://*.firebaseapp.com; frame-src https://accounts.google.com https://zemavoice-ai.firebaseapp.com; media-src 'self' https:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
    if PROD:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

class SpeechRequest(BaseModel):
    text: str = Field(min_length=1, max_length=3000)
    voice_id: str = Field(default='am-hamen', pattern=r'^am-[a-z0-9-]+$')
    language: Literal['am'] = 'am'
    output_format: Literal['mp3_44100', 'wav_44100'] = 'mp3_44100'
    client_request_id: str | None = Field(default=None, max_length=100)

@app.get('/')
def index():
    return FileResponse(PUBLIC_DIR / 'index.html')

@app.get('/firebase-auth.js')
def firebase_auth_script():
    return FileResponse(PUBLIC_DIR / 'firebase-auth.js', media_type='application/javascript')

@app.get('/health')
def health():
    return {'service': 'ZemaVoice AI', 'status': 'ok', 'version': '0.3.0'}

async def addis_request(method, path, **kwargs):
    key = os.getenv('ADDIS_API_KEY')
    if not key:
        raise HTTPException(503, 'Speech provider is not configured')
    try:
        async with httpx.AsyncClient(base_url=BASE, timeout=httpx.Timeout(90.0, connect=10.0), follow_redirects=False) as client:
            response = await client.request(method, path, headers={'x-api-key': key}, **kwargs)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(502, f'Speech provider returned HTTP {exc.response.status_code}')
    except (httpx.RequestError, ValueError):
        raise HTTPException(502, 'Speech provider unavailable or returned invalid data')

@app.get('/v1/voices', dependencies=[Depends(authorize)])
async def voices():
    return await addis_request('GET', '/api/v1/voice/voices', params={'language': 'am'})

@app.post('/v1/tts', dependencies=[Depends(authorize)])
async def tts(req: SpeechRequest):
    payload = req.model_dump(exclude_none=True)
    payload['client_request_id'] = payload.get('client_request_id') or str(uuid.uuid4())
    return await addis_request('POST', '/api/v1/voice/generations', json=payload)
