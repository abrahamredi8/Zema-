"""Download and convert licensed FLEURS Amharic training examples into a local TTS manifest.

Install: pip install datasets soundfile numpy
Run: python independent_engine/prepare_fleurs.py --out ./data/fleurs_am --max-clips 200
This downloads data to the local machine (not Render Free). It does not train a model.
"""
import argparse
import json
from pathlib import Path

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="data/fleurs_am")
    p.add_argument("--max-clips", type=int, default=200)
    args = p.parse_args()
    if args.max_clips < 1:
        p.error("--max-clips must be positive")
    try:
        import soundfile as sf
        from datasets import load_dataset, Audio
    except ImportError:
        raise SystemExit("Install dependencies: pip install datasets soundfile numpy")
    out = Path(args.out)
    audio_dir = out / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    # Streaming avoids downloading the entire multilingual dataset.
    ds = load_dataset("google/fleurs", "am_et", split="train", streaming=True)
    ds = ds.cast_column("audio", Audio(decode=True))
    count = 0
    with (out / "manifest.jsonl").open("w", encoding="utf-8") as manifest:
        for item in ds:
            transcript = (item.get("transcription") or "").strip()
            if not transcript:
                continue
            audio = item["audio"]
            path = audio_dir / f"fleurs_{count:06d}.wav"
            sf.write(path, audio["array"], audio["sampling_rate"])
            row = {
                "audio_path": str(path),
                "transcript": transcript,
                "speaker_id": "fleurs_unknown",
                "consent_record": "dataset-license:google/fleurs",
                "license": "CC-BY-4.0",
                "split": "train",
                "dataset": "google/fleurs",
                "source_id": str(item.get("id", count)),
            }
            manifest.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
            if count >= args.max_clips:
                break
    print(f"Prepared {count} training clips in {out}")
    print("Review quality, license, attribution, and speaker identity before training.")

if __name__ == "__main__":
    main()
