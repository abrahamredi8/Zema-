"""ZemaVoice audio-driven lip-sync timing toolkit.

Outputs per-frame mouth intensity, a coarse mouth shape, and ARKit-compatible
jawOpen/mouthClose weights. These are AUDIO ENERGY heuristics, not phoneme
recognition. Realistic face rendering requires a separate face-tracking/rigging
stage; this script does not modify a person's video.
"""
import argparse
import json
import math
import wave
from pathlib import Path
import numpy as np

SHAPES = ("closed", "small", "medium", "wide")

def read_mono_wav(path):
    with wave.open(str(path), "rb") as w:
        channels, width, rate, frames = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        if width != 2:
            raise ValueError("Use 16-bit PCM WAV (convert with ffmpeg -ac 1 -c:a pcm_s16le)")
        samples = np.frombuffer(w.readframes(frames), dtype="<i2").astype(np.float32) / 32768.0
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)
    return samples, rate

def build_timeline(samples, rate, fps=25, sensitivity=1.0):
    if rate <= 0 or fps <= 0:
        raise ValueError("rate and fps must be positive")
    hop = rate / fps
    nframes = max(1, math.ceil(len(samples) / hop))
    rms = []
    for i in range(nframes):
        seg = samples[int(i * hop):int((i + 1) * hop)]
        rms.append(float(np.sqrt(np.mean(seg ** 2))) if len(seg) else 0.0)
    arr = np.asarray(rms)
    floor = float(np.percentile(arr, 20))
    peak = max(float(np.percentile(arr, 95)) - floor, 0.0001)
    normalized = np.clip((arr - floor) / peak * sensitivity, 0, 1)
    # Smooth jitter, with a one-frame rise/fall to make mouth movement usable.
    smoothed = np.convolve(np.pad(normalized, (1, 1), mode="edge"), [0.2, 0.6, 0.2], mode="valid")
    frames = []
    for i, v in enumerate(smoothed):
        value = round(float(v), 4)
        shape = SHAPES[min(3, int(value * 3.99))]
        frames.append({
            "frame": i,
            "time_seconds": round(i / fps, 4),
            "mouth_open": value,
            "coarse_shape": shape,
            "blendshapes": {"jawOpen": value, "mouthClose": round(1 - value, 4)}
        })
    return frames

def main():
    p = argparse.ArgumentParser()
    p.add_argument("audio", help="16-bit PCM WAV file")
    p.add_argument("--fps", type=int, default=25)
    p.add_argument("--sensitivity", type=float, default=1.0)
    p.add_argument("--output", default="zemavoice_lipsync.json")
    args = p.parse_args()
    samples, rate = read_mono_wav(args.audio)
    frames = build_timeline(samples, rate, args.fps, args.sensitivity)
    payload = {
        "format": "ZemaVoiceLipSync/0.1",
        "audio_file": Path(args.audio).name,
        "duration_seconds": round(len(samples) / rate, 4),
        "fps": args.fps,
        "method": "audio-energy; not phoneme-aligned",
        "supported_targets": ["cartoon_3d_rig", "realistic_face_rig_adapter"],
        "frames": frames,
    }
    Path(args.output).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(frames)} animation frames to {args.output}")
if __name__ == "__main__":
    main()
