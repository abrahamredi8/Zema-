# ZemaVoice AI — Private Beta

Amharic text-to-speech website and API, prepared for Render hosting.

## Status
This repository contains a FastAPI service, an HTML interface, Docker configuration, and a Render Blueprint. It is **not deployed** until you create a Render service. It requires an Addis AI provider key for speech generation. The independent ZemaVoice speech model is still a future milestone.

## Deploy to Render
1. Connect this GitHub repository to Render (https://dashboard.render.com).
2. Choose **New → Blueprint** and select this repository.
3. Set `ADDIS_API_KEY` in Render's environment settings. **Never commit real keys.**
4. Render generates `ZEMAVOICE_API_KEY`; use it privately for the beta interface.
5. Deploy, open the HTTPS URL and check `/health`.
6. Test voices and speech generation with a valid provider account.

## Endpoints
- `GET /` — Amharic voice studio
- `GET /health` — health status
- `GET /v1/voices` — requires `x-zemavoice-key` header
- `POST /v1/tts` — requires `x-zemavoice-key` header

Example request body:
```json
{"text":"ሰላም፣ እንኳን ደህና መጡ።","voice_id":"am-hamen","language":"am","output_format":"mp3_44100"}
```

## Important security limitations
This is a **private beta**, not a public multi-user paid service. The browser asks users to paste a private beta key, so it must not be given to untrusted customers. The hourly limit is in-memory and per-process; production needs durable distributed metering, user authentication, quotas, billing, audit logs, abuse controls, and more robust error handling. Keep provider and API keys in Render secrets. The voice provider's API format and response must be tested with a real account before launch.

## Local development
```bash
pip install -r requirements.txt
uvicorn app:app --reload
```
See `.env.example` for environment variable names.

## Video integration (prepared; GPU engine still required)

`/video` provides upload, playback and MP4 download for private evaluation. It is separate
from the existing energy-based mouth preview and does not change the speech routes.
The home page now includes an installable web-app manifest. This is not an App Store submission.

Configure these server-side secrets only after a compatible GPU service is running:

- `LIPSYNC_ENGINE_URL`: HTTPS endpoint accepting multipart `video` and `audio` fields.
- `LIPSYNC_ENGINE_KEY`: separate secret sent as a Bearer token to that endpoint.

The upstream must validate/decode both media files, enforce duration and resource limits,
render the video, and return HTTP 200 with `Content-Type: video/mp4`. The gateway caps
uploads at 40 MiB, downloads at 100 MiB, does not follow redirects, and limits upstream
waiting to five minutes. This synchronous beta route is for short tests; long renders need
an asynchronous GPU queue with polling and durable storage before production use.

Authenticated routes use the existing `x-zemavoice-key` header:

- `GET /v1/lipsync/status` reports configuration only, not GPU health.
- `POST /v1/lipsync/render` forwards multipart media to the configured engine.

No engine URL is configured by this change. The v10 Colab renderer is not an HTTP service
and cannot be connected merely by entering its notebook URL. Until a compatible GPU service
is available, the page disables generation and explains that the engine is disconnected.
Do not share the private beta key in Muse prompts. Use a secure credential field only if
Muse supports a verified API integration. Existing LatentSync/InsightFace model dependencies
have not been cleared for commercial use; keep this evaluation private.

Validation: `python -m pytest -q`; `node --check public/video.js`.

### Asynchronous job integration

For longer scenes set `LIPSYNC_JOBS_URL` to a compatible GPU service's HTTPS job
collection endpoint, such as `https://your-gpu-host/jobs`. The browser prefers this
mode when configured. It uploads once, polls every four seconds, and downloads the
MP4 after completion. It saves only the job ID in this tab's session storage, never
the beta key. A reload requires re-entering the key and checking the connection.

Engine contract:

- POST collection: multipart video/audio; return 200 or 202 with job state.
- GET collection/{id}: return job state.
- GET collection/{id}/result: return MP4, 409 while not ready, or 404 if expired.
- Every request receives the server-only Bearer credential.
- State: `{"job_id":"job_123","status":"queued","progress":0}`. Status must be
  queued, running, succeeded, failed, or cancelled; progress is an integer 0–100.
- The GPU service owns durable job state, retention, resource limits, and access
  isolation. The gateway does not create that queue or provide GPU computation.

Stopping progress checks does not cancel the GPU job. A separate button can forget
a saved reference after confirmation, without deleting upstream data. Submissions
are never automatically retried after an ambiguous upload failure.

Six automated checks cover both gateway modes, including async lifecycle, expired
results, mismatched IDs, and filtering additional upstream fields. End-to-end GPU
rendering and mobile browser interaction still require validation before release.

### GPU worker implementation

A separate private single-GPU worker is now provided in [gpu/README.md](gpu/README.md).
It implements the async protocol with SQLite persistence, bounded queue admission,
interrupted-job recovery, 24-hour retention and intermediate-file cleanup. The
LatentSync renderer adapter preserves the existing v10 notebook and requires the
operator's installed GPU environment. Nine tests pass, including an actual MP4
upload→queue→download flow with FFmpeg substituting for AI. The new renderer has not
yet run on a GPU; this is not a live deployment or a successful 30-second AI test.

## Unified workspace

The draft home page now groups narration, the 20-profile voice library, video tools,
dialogue planning, local mouth timing and latest session downloads behind the existing
Firebase account UI. The voice catalog is shared with the planner. The 20 entries
are explicitly planned briefs; only voices returned by the connected provider can
be selected for speech. See [implementation handoff](docs/WORK_STATUS.md) for exact
capabilities and remaining integration work. Install development checks with
`pip install -r requirements-dev.txt`; test-only dependencies are excluded from the
production container.
