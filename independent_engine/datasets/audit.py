"""Audit a prepared Amharic JSONL dataset before any model training.

Usage: python independent_engine/datasets/audit.py path/to/manifest.jsonl
Exits nonzero for missing files, missing Amharic text, invalid splits or metadata.
"""
import argparse
import json
from collections import Counter
from pathlib import Path

def audit(path):
    counts = Counter()
    errors = []
    seen = set()
    for line_no, raw in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            item = json.loads(raw)
            if not isinstance(item, dict):
                raise ValueError("expected object")
        except (ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{line_no}: invalid JSON: {exc}")
            continue
        counts["clips"] += 1
        for field in ("audio_path", "transcript", "license", "source", "split"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                errors.append(f"{line_no}: missing {field}")
        audio = item.get("audio_path", "")
        if audio:
            if audio in seen:
                errors.append(f"{line_no}: duplicate audio path")
            seen.add(audio)
            if not Path(audio).is_file():
                errors.append(f"{line_no}: audio missing: {audio}")
        if not any("\u1200" <= c <= "\u137f" for c in item.get("transcript", "")):
            errors.append(f"{line_no}: transcript lacks Ethiopic script")
        split = item.get("split")
        counts[f"split:{split}"] += 1
        if split not in ("train", "validation", "test"):
            errors.append(f"{line_no}: split must be train/validation/test")
        if item.get("license", "").lower() in ("unknown", "none", "unlicensed"):
            errors.append(f"{line_no}: unknown license")
    return counts, errors

def main():
    p = argparse.ArgumentParser()
    p.add_argument("manifest")
    args = p.parse_args()
    counts, errors = audit(args.manifest)
    print("Dataset summary:", dict(counts))
    if errors:
        print("NOT READY:", len(errors), "issues")
        for error in errors[:30]:
            print(" -", error)
        raise SystemExit(1)
    print("Metadata/audio-path checks passed. Human review of consent, licensing, speaker splits, and audio quality still required.")

if __name__ == "__main__":
    main()
