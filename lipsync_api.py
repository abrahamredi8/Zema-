"""Private beta gateway; keeps existing sync and async routes compatible."""
import os
import re
from typing import Literal
from urllib.parse import urlsplit

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, ValidationError

MAX_BYTES = 40 * 1024 * 1024
RESULT_LIMIT = 100 * 1024 * 1024

class JobState(BaseModel):
    job_id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,80}$')
    status: Literal['queued', 'running', 'succeeded', 'failed', 'cancelled']
    progress: int = Field(default=0, ge=0, le=100)

async def bounded_bytes(chunks, limit):
    data = bytearray()
    async for chunk in chunks:
        data.extend(chunk)
        if len(data) > limit:
            raise HTTPException(413 if limit == MAX_BYTES else 502, 'Media exceeds the allowed size')
    return bytes(data)

def settings(variable):
    endpoint = os.getenv(variable, '').rstrip('/')
    key = os.getenv('LIPSYNC_ENGINE_KEY', '')
    if not endpoint or not key:
        raise HTTPException(503, 'GPU lip-sync engine is not connected')
    parsed = urlsplit(endpoint)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise HTTPException(503, 'GPU endpoint configuration is invalid')
    return endpoint, {'Authorization': f'Bearer {key}'}

async def upload(request, headers):
    kind = request.headers.get('content-type', '')
    if not kind.lower().startswith('multipart/form-data;'):
        raise HTTPException(415, 'Upload multipart fields video and audio')
    headers['Content-Type'] = kind
    return await bounded_bytes(request.stream(), MAX_BYTES)

async def proxy(method, endpoint, headers, body=None, result=False, expected_id=None, timeout=90):
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=10), follow_redirects=False) as client:
            async with client.stream(method, endpoint, headers=headers, content=body) as upstream:
                errors = {404: 'Job was not found or has expired', 409: 'Video is not ready yet', 429: 'GPU queue is full; try later'}
                if upstream.status_code in errors:
                    raise HTTPException(upstream.status_code, errors[upstream.status_code])
                if upstream.status_code not in ((200,) if result else (200, 202)):
                    raise HTTPException(502, 'GPU service could not complete the request')
                data = await bounded_bytes(upstream.aiter_bytes(), RESULT_LIMIT if result else 65536)
                if result:
                    if upstream.headers.get('content-type', '').split(';')[0] != 'video/mp4':
                        raise HTTPException(502, 'GPU service did not return an MP4')
                    return Response(data, media_type='video/mp4', headers={
                        'Content-Disposition': 'attachment; filename="zemavoice-lipsync.mp4"'})
                try:
                    state = JobState.model_validate_json(data)
                except ValidationError:
                    raise HTTPException(502, 'GPU service returned invalid job information')
                if expected_id and state.job_id != expected_id:
                    raise HTTPException(502, 'GPU service returned a different job identifier')
                return state.model_dump()
    except httpx.HTTPError:
        raise HTTPException(502, 'GPU service unavailable; check the job before resubmitting')

def build_router(authorize):
    router = APIRouter(prefix='/v1/lipsync', dependencies=[Depends(authorize)])

    @router.get('/status')
    def status():
        key = bool(os.getenv('LIPSYNC_ENGINE_KEY'))
        return {'configured': bool(os.getenv('LIPSYNC_ENGINE_URL')) and key,
                'jobs_configured': bool(os.getenv('LIPSYNC_JOBS_URL')) and key,
                'mode': 'private-evaluation', 'max_upload_bytes': MAX_BYTES,
                'note': 'Configuration does not confirm GPU availability or commercial licensing.'}

    @router.post('/render')
    async def render(request: Request):
        endpoint, headers = settings('LIPSYNC_ENGINE_URL')
        return await proxy('POST', endpoint, headers, await upload(request, headers), result=True, timeout=300)
    return router

def build_jobs_router(authorize):
    router = APIRouter(prefix='/v1/lipsync/jobs', dependencies=[Depends(authorize)])

    def job_endpoint(job_id, result=False):
        endpoint, headers = settings('LIPSYNC_JOBS_URL')
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', job_id):
            raise HTTPException(400, 'Invalid job identifier')
        return endpoint + '/' + job_id + ('/result' if result else ''), headers

    @router.post('', status_code=202)
    async def submit(request: Request, profile: Literal['fast', 'quality'] = 'quality'):
        endpoint, headers = settings('LIPSYNC_JOBS_URL')
        return await proxy('POST', endpoint + '?profile=' + profile, headers, await upload(request, headers))

    @router.get('/{job_id}')
    async def state(job_id: str):
        endpoint, headers = job_endpoint(job_id)
        return await proxy('GET', endpoint, headers, expected_id=job_id)

    @router.get('/{job_id}/result')
    async def result(job_id: str):
        endpoint, headers = job_endpoint(job_id, result=True)
        return await proxy('GET', endpoint, headers, result=True)
    return router
