# Open Amharic data ingestion

This workflow prepares speech/text manifests; it does not train or run a TTS model.

## Sources
1. Mozilla Common Voice Scripted Speech (Amharic, CC0): https://commonvoice.mozilla.org/en/datasets
   Download the Amharic archive from Mozilla after reviewing the current terms.
2. Google FLEURS `am_et` (CC BY 4.0): https://huggingface.co/datasets/google/fleurs
   Attribution is required. Review the dataset card and any restrictions before training.

## Install
```bash
pip install -r independent_engine/datasets/requirements.txt
```

## Import Common Voice
Extract its archive and find `validated.tsv` and the `clips/` directory:
```bash
python independent_engine/datasets/prepare.py commonvoice --tsv /path/to/validated.tsv --clips /path/to/clips --output /path/to/cv_amharic.jsonl
```

## Import FLEURS
```bash
python independent_engine/datasets/prepare.py fleurs --output /path/to/fleurs_amharic.jsonl --audio-dir /path/to/fleurs_audio
```
FLEURS will download audio to the specified local directory; do not commit the audio to GitHub. For speaker privacy, this pipeline does not assume that public speaker identifiers are consent to voice cloning. Both sources are for research/prototyping; verify each dataset's license and intended uses before commercial voice products.

## Manifest fields
`audio_path`, `transcript`, `speaker_id`, `consent_record`, `license`, `split`, `source`.

The importer records dataset-level license and source metadata but leaves `consent_record` as `dataset-license`. This is **not** evidence of individual consent to clone a recognizable voice. Never create a voice impersonation model from these records without additional permission. Keep a speaker-disjoint evaluation split when speaker IDs are available.
