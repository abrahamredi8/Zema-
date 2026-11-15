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

## Latest observed state

- Actual 30-second synthetic T4 run completed, 750 frames, 1400.114 s; see performance notes.
- The added v10 review cell embeds the completed 30-second MP4. A separate result
  notebook copy and final visual playback review were not verified before browser
  access failed. Existing source cells and voices were not edited.
- A separate private UI preview notebook was created and saved:
  https://colab.research.google.com/drive/1MJT3dD_uGOS7d-69gF1aYrLR9sgbDNQT
  It bundles owned UI assets in Colab output, without forwarding a server or
  loading Firebase sign-in. Its source is in tools/preview_bundle.py.
- Browser checks verified tab switching, 20 profile cards, ten female-filter
  results and one Mekdes search result. A duplicated planner library/header was
  found and the embedded view streamlined. The latest streamlining needs a fresh
  browser check. Pure DSP, WAV, API and synthetic media tests are automated.
- The file chooser did not deliver the synthetic WAV in the bundled preview;
  browser end-to-end audio processing/import/export remains unverified.
- No live deployment, paid purchases, public endpoint, or external Muse connector.
