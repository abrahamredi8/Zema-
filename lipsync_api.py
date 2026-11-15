"""Private beta gateway. The GPU service must implement the same POST contract."""
import os
from urllib.parse import urlsplit
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response

MAX_BYTES = 40 * 1024 * 1024

def build_router(authorize):
    router = APIRouter(prefix='/v1/lipsync', dependencies=[Depends(authorize)])

    @router.get('/status')
    def status():
        return {'configured': bool(os.getenv('LIPSYNC_ENGINE_URL') and os.getenv('LIPSYNC_ENGINE_KEY')),
                'jobs_configured': bool(os.getenv('LIPSYNC_JOBS_URL') and os.getenv('LIPSYNC_ENGINE_KEY')),
                'mode': 'private-evaluation', 'max_upload_bytes': MAX_BYTES,
                'note': 'Configuration does not confirm GPU availability or commercial licensing.'}

    @router.post('/render')
    async def render(request: Request):
        endpoint = os.getenv('LIPSYNC_ENGINE_URL', '')
        key = os.getenv('LIPSYNC_ENGINE_KEY', '')
        if not endpoint or not key:
            raise HTTPException(503, 'GPU lip-sync engine is not connected')
        parsed = urlsplit(endpoint)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise HTTPException(503, 'GPU endpoint configuration is invalid')
        content_type = request.headers.get('content-type', '')
        if not content_type.lower().startswith('multipart/form-data;'):
            raise HTTPException(415, 'Upload multipart fields video and audio')
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > MAX_BYTES:
                raise HTTPException(413, 'Combined upload exceeds 40 MiB')
        try:
            async with httpx.AsyncClient(timeout=300, follow_redirects=False) as client:
                async with client.stream('POST', endpoint, content=bytes(body), headers={
                    'Authorization': f'Bearer {key}', 'Content-Type': content_type}) as upstream:
                    if upstream.status_code != 200:
                        raise HTTPException(502, 'GPU service did not complete the render')
                    if upstream.headers.get('content-type', '').split(';')[0] != 'video/mp4':
                        raise HTTPException(502, 'GPU service returned an unexpected format')
                    result = bytearray()
                    async for chunk in upstream.aiter_bytes():
                        result.extend(chunk)
                        if len(result) > 100 * 1024 * 1024:
                            raise HTTPException(502, 'GPU result exceeds the beta download limit')
            return Response(bytes(result), media_type='video/mp4', headers={
                'Content-Disposition': 'attachment; filename="zemavoice-lipsync.mp4"'})
        except httpx.HTTPError:
            raise HTTPException(502, 'GPU service is unavailable; try again later')
    return router

# Long renders use an engine-owned durable job queue. The web gateway stores no jobs.
import re
from pydantic import BaseModel, Field, ValidationError
from typing import Literal

class JobState(BaseModel):
    job_id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,80}$')
    status: Literal['queued', 'running', 'succeeded', 'failed', 'cancelled']
    progress: int = Field(default=0, ge=0, le=100)

async def bounded_response(response, limit):
    data = bytearray()
    async for chunk in response.aiter_bytes():
        data.extend(chunk)
        if len(data) > limit:
            raise HTTPException(502, 'GPU response exceeds the allowed size')
    return bytes(data)

def build_jobs_router(authorize):
    router = APIRouter(prefix='/v1/lipsync/jobs', dependencies=[Depends(authorize)])

    def settings(job_id=None, result=False):
        endpoint = os.getenv('LIPSYNC_JOBS_URL', '').rstrip('/')
        key = os.getenv('LIPSYNC_ENGINE_KEY', '')
        parsed = urlsplit(endpoint)
        if not endpoint or not key:
            raise HTTPException(503, 'GPU job service is not connected')
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise HTTPException(503, 'GPU job endpoint configuration is invalid')
        if job_id is not None:
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', job_id):
                raise HTTPException(400, 'Invalid job identifier')
            endpoint += '/' + job_id + ('/result' if result else '')
        return endpoint, {'Authorization': f'Bearer {key}'}

    async def proxy(method, endpoint, headers, body=None, result=False, expected_id=None):
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(90, connect=10), follow_redirects=False) as client:
                async with client.stream(method, endpoint, headers=headers, content=body) as upstream:
                    if upstream.status_code == 404:
                        raise HTTPException(404, 'Job was not found or has expired')
                    if upstream.status_code == 409:
                        raise HTTPException(409, 'Video is not ready yet')
                    if upstream.status_code not in (200, 202):
                        raise HTTPException(502, 'GPU job service could not complete the request')
                    data = await bounded_response(upstream, 100*1024*1024 if result else 65536)
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
            raise HTTPException(502, 'GPU job service is unavailable; check the job again before resubmitting')

    @router.post('', status_code=202)
    async def submit(request: Request):
        endpoint, headers = settings()
        content_type = request.headers.get('content-type', '')
        if not content_type.lower().startswith('multipart/form-data;'):
            raise HTTPException(415, 'Upload multipart fields video and audio')
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > MAX_BYTES:
                raise HTTPException(413, 'Combined upload exceeds 40 MiB')
        headers['Content-Type'] = content_type
        return await proxy('POST', endpoint, headers, bytes(body))

    @router.get('/{job_id}')
    async def state(job_id: str):
        endpoint, headers = settings(job_id)
        return await proxy('GET', endpoint, headers, expected_id=job_id)

    @router.get('/{job_id}/result')
    async def result(job_id: str):
        endpoint, headers = settings(job_id, result=True)
        return await proxy('GET', endpoint, headers, result=True)

    return router
