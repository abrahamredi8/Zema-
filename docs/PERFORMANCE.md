# T4 performance checks — 15 November 2026

These are actual Google Colab T4 measurements on the user's four-second Amharic
greeting and approximately five-second silent human source. Each row is one run,
not a statistically repeated benchmark or a promise for other video lengths.

| Run | Steps | Wall time | Model loaded during run |
| --- | ---: | ---: | --- |
| Quality, cold process | 30 | 245.259 s | Yes (49.387 s) |
| Fast preview, resident model | 20 | 156.920 s | No |
| Quality, resident model | 30 | 200.222 s | No |

In this run, the fast profile used about 22% less wall time than the warmed quality
profile. Model residency avoided the measured model initialization cost. There is
still substantial preprocessing, audio/face processing and assembly overhead.
This engine is not demonstrated to generate at real-time speed on this T4.

A subsequent detector-weight reuse experiment measured 249.262 s cold quality,
161.832 s warm preview, and 207.697 s warm quality. That run also included the
original-audio mux correction and normal machine variability. It did not establish
a speed gain, so the extra detector patch was removed. Each video's temporal
restorer remains fresh; model weights can stay resident.

## Regression coverage

Local tests use deterministic synthetic frames for audio timing, chunk boundary
frame counts, original-footage restoration after speech, silence skipping,
authentication, transfer/queue limits, worker persistence, workspace asset routes,
20 planned-profile labeling, and volume-normalization/WAV encoding. They do not
replace visual lip-sync review or a real provider voice test.

## Thirty-second stress test

The long test uses seven repeated copies of the original greeting plus trailing
silence, and a loop of the supplied silent human clip. This is a synthetic workload,
not a new natural dialogue or Muse's actual test video. It uses serial five-second
cores with context and muxes the original full audio once. Record its final result,
frame count, audio correlation and elapsed time only after successful completion.
The original source video and audio remain unchanged.

A MuseTalk comparison has not run. No claims about its speed or quality on this GPU
are made here. The website's actual connection to Muse is also not verified by
these direct Colab tests.

## Completed 30-second T4 result

The synthetic stress run completed: renderer wall time **1400.114 seconds** (about
23 minutes 20 seconds), **750 frames**, **30.0 seconds**, and audio correlation
**0.9999590485009013** at the original timing. The resident model loaded once.
The H.264/AAC output was 12,093,177 bytes. Fixture creation time is not included.
This is a successful technical completion, not a real-time performance result or
a full visual/natural-dialogue acceptance test. MuseTalk remains unbenchmarked.

The video was embedded in an added review cell in the working v10 notebook:
https://colab.research.google.com/drive/1BAfaz1OZAAvGdgp4H76tBq1EFiLOiuqS#scrollTo=teUccgsOtsxv

A separate-copy save was attempted but not verified before browser access became
unavailable. Existing working code cells and original voices were preserved; the
added review cell was not removed. Do not describe the notebook as unchanged.
