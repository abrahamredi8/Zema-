# ZemaVoice implementation handoff

All new work is on `codex/video-gateway-app`, draft PR #1. The live Render service
still follows main. Do not assume this draft is deployed or that Muse calls its GPU
API. No compatible external GPU endpoint is currently configured by this work.
Check remote heads and use a lease before updating this shared branch.

## Implemented

- One signed-in workspace: provider narration, 20-profile voice library, embedded
  human video tools, dialogue planning, local mouth timing, and latest downloads.
- Shared profile definitions for the main library and dialogue planner. Previous
  child-profile IDs remain importable in older planning projects.
- Exactly 20 adult/narrator voice briefs: ten female and ten male. These are NOT
  twenty working voices. Real selectable voices come from `/v1/voices`; the Mekdes
  entry is a quality reference, not an automatically connected Azure engine.
- Existing Firebase sign-in. Generation still uses the private beta API key; account
  UI sign-in is not server-side Firebase authorization or multi-tenant isolation.
- Compatible sync and async GPU gateway, one buffered media transfer at a time,
  bounded uploads/downloads, resumable job monitoring and ephemeral key sharing
  only between same-origin parent and video frame.
- Separate persistent single-GPU worker, optional resident LatentSync model,
  20-step fast preview and original 30-step quality default.
- Longer audio can use serial five-second cores with 0.4-second context. Assembly
  muxes the full original audio once to avoid cumulative AAC chunk timing drift.
- Final audio uses the original recording, not the 16 kHz analysis copy. Trailing
  silence skips unnecessary diffusion; the original human footage returns after
  speech. Source-mouth movement during silence cannot be fixed by this fallback.

## Validation and limits

Local API/media tests use FFmpeg and synthetic fake-render frames. Actual T4 short
sample benchmarks have also run; see performance notes when published. A full
30-second stress run is separate from a natural dialogue quality review.

No twenty-voice model collection, Azure billing integration, Muse-specific connector,
app-store submission, durable customer project store, automatic silence correction
for every source, or commercial license clearance is supplied. Those are pending
features, not buttons that pretend to work. Preserve the existing male and female
notebooks and audio references. Current LatentSync/InsightFace auxiliary model
restrictions keep this evaluation out of a paid service.

The GPU worker needs an operator-provided GPU environment, private persistent disk
and HTTPS. Colab is a test runtime, not reliable always-on hosting. No paid hosting
or public endpoint was provisioned. No credentials belong in repository content.

A browser-local audio-volume tool is also implemented: preview and PCM WAV export,
peak-limited gain, no speed/pitch change, no uploads, and no claim of denoising.
The signed-in workspace still requires real browser testing before release.
