# Free Amharic training data — initial selection

## Sources
1. Mozilla Common Voice Scripted Speech 27.0, Amharic (CC0-1.0). https://commonvoice.mozilla.org/
2. Google FLEURS, am_et (CC BY 4.0). https://huggingface.co/datasets/google/fleurs

## Usage rules
- Review the source dataset card and its latest terms before downloading.
- CC BY requires attribution; retain dataset/source metadata.
- Do not treat open speech datasets as permission to clone or impersonate a named person.
- Preserve original evaluation splits; check speaker overlap and audio quality.
- Verify transcript accuracy, clipping, background noise, duplicate content, and Amharic script normalization.
- Do not download copyrighted YouTube movies/news as training data without permission.

## Quick start
```bash
pip install datasets soundfile numpy
python independent_engine/prepare_fleurs.py --out data/fleurs_am --max-clips 200
python independent_engine/validate_dataset.py data/fleurs_am/manifest.jsonl
```
Run on a workstation or GPU environment, **not** the Render Free web server. Audio data is not included in this Git repository.

## Current status
Data sources and preparation script configured. No audio files have been downloaded or validated; no model has been trained. A multi-speaker TTS engine requires additional data, modeling, training, and evaluation.
