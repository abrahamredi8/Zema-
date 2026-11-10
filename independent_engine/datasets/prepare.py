"""Prepare licensed Amharic audio-text manifests for independent TTS research."""
import argparse
import csv
import json
from pathlib import Path

def write_manifest(rows, output):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

def from_commonvoice(args):
    clips = Path(args.clips).resolve()
    rows = []
    with open(args.tsv, encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream, delimiter="\t"):
            name = row.get("path", "")
            text = row.get("sentence", "").strip()
            audio = (clips / name).resolve()
            if not name or not text or not audio.is_relative_to(clips) or not audio.is_file():
                continue
            speaker = row.get("client_id") or "unknown"
            rows.append({
                "audio_path": str(audio), "transcript": text,
                "speaker_id": "cv_" + speaker, "consent_record": "dataset-license",
                "license": "CC0-1.0", "split": "unassigned",
                "source": "Mozilla Common Voice Amharic",
            })
    write_manifest(rows, args.output)
    print(f"Wrote {len(rows)} Common Voice entries to {args.output}")

def from_fleurs(args):
    from datasets import load_dataset
    import soundfile as sf
    root = Path(args.audio_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    rows = []
    for split in ("train", "validation", "test"):
        ds = load_dataset("google/fleurs", "am_et", split=split)
        for idx, row in enumerate(ds):
            audio = row["audio"]
            path = root / f"{split}_{idx:06d}.wav"
            sf.write(str(path), audio["array"], audio["sampling_rate"])
            text = (row.get("transcription") or row.get("raw_transcription") or "").strip()
            if not text:
                path.unlink(missing_ok=True)
                continue
            rows.append({
                "audio_path": str(path), "transcript": text,
                "speaker_id": "fleurs_unknown", "consent_record": "dataset-license",
                "license": "CC-BY-4.0", "split": split,
                "source": "Google FLEURS am_et",
            })
    write_manifest(rows, args.output)
    print(f"Wrote {len(rows)} FLEURS entries to {args.output}")

def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="source", required=True)
    cv = sub.add_parser("commonvoice")
    cv.add_argument("--tsv", required=True)
    cv.add_argument("--clips", required=True)
    cv.add_argument("--output", required=True)
    fleurs = sub.add_parser("fleurs")
    fleurs.add_argument("--output", required=True)
    fleurs.add_argument("--audio-dir", required=True)
    args = parser.parse_args()
    (from_commonvoice if args.source == "commonvoice" else from_fleurs)(args)

if __name__ == "__main__":
    main()
