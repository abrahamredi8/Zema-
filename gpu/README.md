# Private GPU evaluation worker

This service implements the web gateway's job protocol. It is a separate process on
an operator-provided GPU host, not part of the CPU-only Render web container.
No host, paid service, model download, or commercial deployment is created here.

## Prerequisites

Use the same LatentSync-1.5 checkout, Python environment, model files and NVIDIA
library paths as the working v10 Colab test. Keep the original notebook unchanged.
The adapted renderer requires FFmpeg/FFprobe, OpenCV, NumPy, and a compatible NVIDIA
GPU in that environment. It enables the same T4 fp16 adapter used by v10. Model and
third-party dependency licensing remains restricted/unverified for commercial use.

Set a fresh server-only `LIPSYNC_ENGINE_KEY` of at least 32 characters. On the GPU
host set:

- `LATENTSYNC_REPO`: absolute path to installed LatentSync checkout.
- `LATENTSYNC_PYTHON`: absolute Python executable for that model environment.
- `LIPSYNC_JOB_DIR`: durable, private directory with enough disk for media and jobs.
- `LIPSYNC_RENDER_COMMAND`: JSON array, for example
  `["/absolute/python", "/absolute/Zema-/gpu/render_latentsync.py", "--video", "{video}", "--audio", "{audio}", "--output", "{output}"]`.

Start from the repository root:

```sh
uvicorn gpu.service:create_app --factory --host 0.0.0.0 --port 8000 --workers 1
```

Use exactly one worker process/replica per job directory and GPU. Put an HTTPS
reverse proxy in front of this service; configure upload limits there too. Set the
web app's `LIPSYNC_JOBS_URL` to its HTTPS `/jobs` URL and the same engine key.
Do not expose notebook session tokens or private keys in prompts or source files.

## Behavior and limits

- Three admitted jobs at a time; one active renderer. SQLite state and job media
  survive process restarts when the directory is on persistent storage.
- Interrupted running jobs become failed on startup rather than silently rerun.
- Uploads cap at 40 MiB. The renderer validates decoded media metadata and accepts
  up to 30 seconds of audio with a covering video of at most 120 seconds and 4K input.
  Input is normalized to at most 1280×720 and 25 fps. No voice speed/pitch changes.
- Restores same-time original human footage after speech, as in the v10 approach.
  A source with an already moving mouth cannot guarantee a closed mouth in silence.
  Internal pauses are not yet explicitly gated. Longer narration and visual quality
  still need GPU testing; these settings alone do not demonstrate success.
- Temporary media is removed after completion/failure. Final results and state expire
  after 24 hours, checked by the worker loop. Run with start_worker=True in production.
- Progress is currently coarse (queued=0, running=10, succeeded=100), not a measured
  per-frame percentage. The command times out after 30 minutes.
- The key is for one trusted private beta tenant. No public account isolation, billing,
  paid generation, cancellation, multi-GPU scaling, or commercial clearance is supplied.

## Validation

The tests cover persistence, queue capacity, failure recovery, expiry, auth, and a
real-media gateway→worker→download round trip using FFmpeg in place of AI. They do
not run or claim GPU inference. Before deployment, render the original human sample,
review lip timing and ending, then test a 30-second dialogue with pauses.

## Speed profiles and resident model

The default quality profile retains 30 inference steps. The experimental fast profile
uses 20; compare mouth detail and timing before selecting it for final output.
Submissions carry `?profile=fast` or `?profile=quality`. A custom command must include
`--profile {profile}` to honor the selected mode.

For repeated jobs, run this service in the actual LatentSync Python environment and
set `LIPSYNC_WARM_MODEL=1`. The serial worker then calls the renderer in-process and
loads the model lazily once, keeping it on the GPU between jobs. This mode must not
run in a shared multi-thread inference environment: the underlying repository uses
relative resource paths. The original subprocess renderer remains the default for
compatibility and process isolation. A process restart reloads the model.

Benchmark with the same uploaded files, without changing the original notebook:

```sh
python -m gpu.benchmark --video /absolute/source.mp4 --audio /absolute/narration.wav --output /absolute/benchmark
```

It runs quality-cold, fast-warm, then quality-warm and saves three MP4s plus JSON
measurements. Compare the two warm runs for profile speed, rather than confusing
model loading time with inference speed. All outputs still require visual review.
No speedup is asserted until this benchmark is measured on the target GPU.

## Longer inputs and memory

The in-process worker uses `gpu.render_long.render_long` for longer recordings.
It renders five-second cores with 0.4 seconds of context and appends original silent
footage after the recording. The final full audio is muxed once. Window boundaries
still need visual review; overlap alone is not a guarantee of seamless motion.
For the cold command renderer, use `python -m gpu.render_long` from the repository
root with the same video/audio/output/profile arguments. Cold rendering loads the
model per window, so the resident mode is recommended for throughput testing.

Timing metrics now separate preprocessing, AI, and final assembly. Normalized 25 fps
inputs avoid a redundant normalization encode, and trailing silence is omitted from
the analysis audio sent to diffusion while the final original audio is preserved.
An experimental detector-weight cache did not show a speed gain on the test clip;
that extra patch was removed rather than made the default.
