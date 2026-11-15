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
