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
