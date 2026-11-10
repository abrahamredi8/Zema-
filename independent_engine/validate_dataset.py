"""Validate metadata for consented Amharic TTS training clips (stdlib only)."""
import json
import sys
from pathlib import Path

REQUIRED = ("audio_path", "transcript", "speaker_id", "consent_record", "license", "split")

def validate(path: Path):
    problems = []
    seen = set()
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            item = json.loads(raw)
            if not isinstance(item, dict):
                raise ValueError("must be a JSON object")
        except (ValueError, json.JSONDecodeError) as exc:
            problems.append(f"line {number}: invalid JSON: {exc}")
            continue
        missing = [key for key in REQUIRED if not isinstance(item.get(key), str) or not item[key].strip()]
        if missing:
            problems.append(f"line {number}: missing fields: {', '.join(missing)}")
        if item.get("split") not in ("train", "validation", "test"):
            problems.append(f"line {number}: invalid split")
        if item.get("audio_path") in seen:
            problems.append(f"line {number}: duplicate audio_path")
        seen.add(item.get("audio_path"))
        if item.get("license") in ("unknown", "unlicensed", "none"):
            problems.append(f"line {number}: insufficient license")
        if not any("\u1200" <= ch <= "\u137f" for ch in item.get("transcript", "")):
            problems.append(f"line {number}: transcript contains no Ethiopic characters")
    return problems

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python independent_engine/validate_dataset.py manifest.jsonl")
    errors = validate(Path(sys.argv[1]))
    if errors:
        print("\n".join(errors))
        raise SystemExit(1)
    print("Manifest validation passed (metadata only; does not verify rights or audio quality).")
