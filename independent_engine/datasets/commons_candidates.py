"""Discover Wikimedia Commons Amharic audio files for manual licensing review.

No audio is downloaded. Run: python independent_engine/datasets/commons_candidates.py
Writes JSONL candidate metadata; no automatic commercial-training approval.
"""
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API = "https://commons.wikimedia.org/w/api.php"
CATEGORY = "Category:Audio files in Amharic"
OUT = Path("independent_engine/datasets/commons_candidates.jsonl")

def fetch(params):
    url = API + "?" + urlencode(params)
    req = Request(url, headers={"User-Agent": "ZemaVoiceDatasetResearch/0.1 (educational metadata discovery)"})
    with urlopen(req, timeout=30) as response:
        return json.load(response)

def main():
    results = []
    cont = {}
    while True:
        params = {
            "action": "query", "format": "json", "generator": "categorymembers",
            "gcmtitle": CATEGORY, "gcmtype": "file", "gcmlimit": "max",
            "prop": "imageinfo", "iiprop": "extmetadata|url|size", "iilimit": "1",
            **cont,
        }
        data = fetch(params)
        for page in data.get("query", {}).get("pages", {}).values():
            info = (page.get("imageinfo") or [{}])[0]
            meta = info.get("extmetadata") or {}
            def field(name):
                return (meta.get(name) or {}).get("value", "")
            results.append({
                "title": page.get("title"), "page_url": info.get("descriptionurl"),
                "license_short": field("LicenseShortName"),
                "license_url": field("LicenseUrl"),
                "license_html": field("License"),
                "attribution_html": field("Attribution"),
                "license_review": "manual-review-required",
                "speaker_voice_clone_consent": "not-verified",
                "downloaded": False,
                "training_approved": False,
            })
        cont = data.get("continue", {})
        if not cont:
            break
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for item in results:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"Found {len(results)} candidate files; wrote {OUT}. No audio downloaded or approved.")

if __name__ == "__main__":
    main()
