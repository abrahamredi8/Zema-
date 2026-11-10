# ZemaVoice Native Amharic Engine

This directory begins the **independent** ZemaVoice speech-engine project. No Addis AI API, proprietary model, or third-party voice is used here.

## Phase 1: data and evaluation
- Collect consented, licensed, studio-quality Amharic speech recordings and aligned transcripts.
- Include conversational speech, narration, punctuation, numbers, names, ejectives, gemination, and emotional styles.
- Record speaker consent, rights for commercial synthesis, age/guardian permissions for any minors, and withdrawal procedures.
- Reserve speakers and texts for evaluation; never train on evaluation recordings.
- Run `python independent_engine/validate_dataset.py independent_engine/sample_manifest.jsonl` to validate the manifest.

## Phase 2: native model
- Choose a trainable TTS architecture with a commercially usable license after reviewing the exact model and dependencies.
- Train a native Ethiopic-script text frontend and speaker-conditioned acoustic model; build a separate vocoder.
- Train/evaluate on GPU compute outside Render Free. The current web service is not a training server.
- Evaluate pronunciation, intelligibility, naturalness, latency, identity consistency, and misuse risk with native speakers.

## Phase 3: product integration
- Host a model inference worker on appropriate hardware, expose authenticated synthesis jobs and downloadable audio.
- Replace the Addis AI adapter in `app.py` only after tested audio generation is working.
- Add a voice registry, consent/revocation controls, per-user quotas, and audit logs.
- Add timeline-aligned multi-character audio; lip sync comes later.

**Status:** planning/data tooling only. No independently trained model or 40 voices exist yet.

**License warning:** Meta MMS Amharic weights are CC BY-NC 4.0 (noncommercial); do not ship them in a paid product. Any third-party training data or model must be individually audited.
