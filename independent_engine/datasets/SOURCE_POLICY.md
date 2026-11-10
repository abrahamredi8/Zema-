# ZemaVoice independent engine: source selection

## Ready for evaluation (license still must be honored)
- Mozilla Common Voice Amharic: CC0; https://commonvoice.mozilla.org/
- Google FLEURS Amharic: CC BY 4.0; https://huggingface.co/datasets/google/fleurs
- Dataset.ET Amharic Speech: CC BY 4.0; https://huggingface.co/datasets/snapwre/amharic-speech — published as 51.547 hours, 16,866 clips, 493 speakers. **Check dataset card restrictions, consent scope and speaker protections before TTS training**. Do not clone identifiable speakers without appropriate permission.

## License review required — DO NOT INGEST YET
- b1n1yam/wxl_amh: https://huggingface.co/datasets/b1n1yam/wxl_amh — dataset is publicly listed, but commercial TTS training rights and consent scope have not been verified. Do not download, train on, or redistribute until independently confirmed.
- Addis AI production API outputs or voices: not authorized for competing model training without written permission.

## Next steps
1. Use the existing Common Voice and FLEURS import scripts for an initial small-scale experiment.
2. Inspect dataset audio quality and transcription accuracy. Preserve source attribution.
3. Audit consent and speaker identity before voice cloning or commercial release.
4. Train only on properly authorized data using external GPU compute. Render Free cannot perform this training.

**Status:** source policy only. No dataset downloaded and no model trained by this change.
