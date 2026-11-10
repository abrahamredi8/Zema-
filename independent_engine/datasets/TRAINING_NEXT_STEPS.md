# Training execution checklist

**Status:** source selection and data tooling implemented; no training run or model weights exist.

1. Prepare licensed Common Voice and FLEURS audio with `prepare.py` on a local workstation or cloud GPU machine. Never run large downloads on Render Free.
2. Audit metadata/audio paths using `audit.py`. Inspect audio, verify license obligations and permissions, remove noise and duplicates, normalize Amharic transcripts.
3. Create train/validation/test splits without overlapping speakers where possible. Preserve FLEURS test and validation sets.
4. Choose a TTS model architecture with commercial licensing after reviewing dependencies. Do not use noncommercial pretrained weights in commercial ZemaVoice.
5. Train an initial voice on GPU, measure pronunciation and naturalness with Amharic speakers, and publish only with rights clearance.
6. Build a separately hosted inference service and connect ZemaVoice's API after the model actually generates audio.

**Dataset.ET:** Candidate `snapwre/amharic-speech`. Verify access, dataset schema, terms, voice permissions and commercial training rights before ingestion. Not downloaded or trained on yet.

**Addis AI-associated dataset:** Candidate `b1n1yam/wxl_amh`. License and consent remain unverified; excluded from ingestion.

**Do not mistake a dataset license for consent to clone a particular speaker's voice.**
