# Test Report

Environment: Linux container (Ubuntu 24.04, 4 vCPU x86-64), Python 3.13.18,
FFmpeg 6.1.1 with libx264, numpy 2.5.3. Raw logs:
`docs/test-results/pytest-full-suite.txt`, `junit.xml`,
`pytest-15-minute-master.txt`.

Result: **78 passed** (fast suite) + **1 passed** (15-minute master,
`-m slow`). 0 failed. A subset (20 tests) also passed in a second Python
environment **without numpy** (pure-Python fallback path).

All media is synthetic. FFmpeg `testsrc2` produces a different picture on
every frame (moving objects, frame counter), and a multi-tone signal stands in
for the programme audio. Revisions are hue/negate effects, cross-fade
transitions, tone changes and inserted/removed frames, defined
frame-accurately on a synthetic "timeline". Every patch test checks the
engine's own report **and** re-checks pixel identity independently with
FFmpeg's `framehash` muxer (SHA-256), which shares no code with the engine.

## Requirements traceability (prompt section 12)

| # | Requirement | Test(s) | Result |
|---|---|---|---|
| 1 | 5-second revision in a 15-minute H.264 master | `test_long.py::test_five_second_revision_in_fifteen_minute_master` (26,973 frames @ 29.97, revision at 7:30) | **PASS** – 257 frames rendered (0.95 %), 26,723 preserved & verified identical, 250 re-encoded (150 revised + 100 boundary) |
| 2 | Revision starting between keyframes | `test_revision_starts_between_keyframes` | **PASS** – head preserved down to the mini-GOP (≤ 4 frames re-encoded before the revision) |
| 3 | Revision ending between keyframes | `test_revision_ends_between_keyframes` | **PASS** – tail rebuilt to the next IDR, reported as 33 boundary frames |
| 4 | Multiple separate revisions | `test_multiple_separate_revisions`, `test_overlapping_and_adjacent_revisions_are_merged` | **PASS** – 3 render jobs; overlapping/adjacent ranges merged |
| 5 | Revisions near beginning and end | `test_revisions_near_beginning_and_end` | **PASS** |
| 6 | Revisions containing transitions | `test_transition_outside_declared_range_is_detected`, `test_transition_with_handles_passes` | **PASS** – undeclared cross-fade frames detected and the export refused; with handles it passes |
| 7 | Audio-only revisions | `test_audio_only_revision_renders_no_video` | **PASS** – 0 video frames re-encoded, all 250 frames identical, audio spliced |
| 8 | Video-only revisions | `test_video_only_revision_keeps_audio_bit_identical` | **PASS** – decoded audio hashes identical to master |
| 9 | Simultaneous audio + video | `test_simultaneous_audio_and_video_revision` | **PASS** – PCM bit-identical outside transition blocks, sync lag 0 |
| 10 | 23.976, 24, 25, 29.97, 30, 60 fps (+59.94) | `test_frame_rates[…]` ×7, with 01:00:00:00 timeline start | **PASS** – exact rational rate preserved; audio splice aligned at fractional sample positions (29.97 → 1601.6 samples/frame) |
| 11 | B-frame-heavy streams | `test_b_frame_heavy_stream` (8 B-frames, b-adapt 0) | **PASS** |
| 12 | Different GOP lengths | `test_gop_lengths[1, 12, 48, 400]` | **PASS** – all-intra gives 0 boundary frames |
| 13 | Different H.264 profiles | `test_h264_profiles[baseline, main, high]`, `test_high10_profile_if_supported` | **PASS** – profile and entropy coder (CAVLC/CABAC) matched; 10-bit 4:2:0 works |
| 14 | Missing or incompatible metadata | `test_master_without_colour_metadata`, `test_variable_frame_rate_master_is_refused`, `test_interlaced_master_is_refused`, `test_unsupported_codec_hevc`, `test_master_without_audio`, `test_open_gop_master_uses_only_idr_resume_points` | **PASS** – untagged masters stay untagged; VFR/interlaced/HEVC refused with explanations |
| 15 | Interrupted exports | `test_interrupted_export_leaves_master_untouched` (SIGINT during encode), `test_crash_recovery` (SIGKILL + `jobs recover`) | **PASS** – exit 130, master SHA-256 unchanged, no output/partial files, job marked cancelled/interrupted, temp removed |
| 16 | Repeated revision cycles | `test_repeated_revision_cycles_no_generation_loss` (3 cycles, incl. re-revising the same region) | **PASS** – earlier patches survive later cycles bit-exactly; only referenced parameter sets kept; history records 3 cycles |
| 17 | Frame count and timestamp validation | `test_frame_count_and_timestamps` + `frame_count`/`timestamps` checks in every report | **PASS** – per-frame PTS of output identical to master |
| 18 | Pixel identity outside revisions | every patch test via `independent_identity()` (FFmpeg framehash) + engine `pixel_identity` check | **PASS** |

## Additional coverage

| Area | Tests | Result |
|---|---|---|
| Strict mode | `test_strict_mode_refuses_reencoding_unchanged_frames`, `test_strict_mode_on_all_intra_master` | PASS |
| Duration-changing revisions (+10, −6, +12/−4 frames) | `test_duration_changing_revision[…]` | PASS – full audio re-encode, sync ≤ 0.5 sample |
| Full audio re-encode | `test_full_audio_reencode_option` | PASS |
| AAC with PNS in master | `test_pns_master_audio_splice_is_not_silently_accepted` | PASS – success only with proven identity |
| Never overwrite / output == master | `test_never_overwrites` | PASS |
| Render failure, wrong frame count, wrong rate/resolution | `test_render_failure_is_reported_cleanly`, `test_render_with_wrong_frame_count_is_rejected`, `test_changed_frame_rate_and_resolution_are_rejected` | PASS |
| Wrong master for timeline (3-frame offset) | `test_wrong_master_for_timeline_is_detected` | PASS – refused by guard/boundary check |
| Corrupted temporary output | `test_corrupted_patch_is_rejected` | PASS |
| Disk-space exhaustion | `test_disk_space_exhaustion_is_detected` | PASS |
| Fast Patch mode | `test_fast_patch_mode` | PASS – reports undecoded frames as a warning, never as verified |
| Revision-Ready Master + later patch | `test_revision_ready_master_then_patch[1, 25]` | PASS – IDR every N frames; later patch has ≤ N−1+3 boundary frames (0 for all-intra) |
| Safe Full Export | `test_safe_full_export` | PASS |
| Manual render import (no scripting) | `test_manual_render_import_source`, `test_manual_render_not_covering_range_is_reported` | PASS |
| Resolve bridge (API mock) | `test_cli_request_export_with_resolve_mock`, `test_cli_resolve_not_running`, `test_cli_resolve_render_failure`, `test_resolve_full_audio_reencode_renders_audio_only` | PASS (mock only – see below) |
| CLI / app protocol | `test_cli_doctor_probe_plan`, strict-JSON check on every event line, `test_cli_frame_and_filmstrip` (preview frame exact) | PASS |
| Unit: timecode (NDF/DF), exp-Golomb, SPS/avcC, MP4 round trip, planner | `test_unit.py` (15 tests) | PASS |

## Defects found by the tests and fixed

Each of these was a real problem found by a failing test, fixed, and re-tested:

1. **VBV silently dropped.** `sar=1:1` in `-x264-params` swallowed the next
   option because `:` is FFmpeg's separator. Fixed (`1/1`). The engine now
   parses libx264's own SEI and fails if any requested setting was not
   applied.
2. **Chroma-only changes undetected.** A hue transition outside the declared
   range passed a luma-only check. All decisions now use the minimum PSNR over
   Y, U and V.
3. **AAC PNS broke later cycles.** Noise substitution in splice encodes made
   decoding of earlier patches differ in the next revision cycle. Disabled.
4. **Audio sync ambiguity.** ±1-sample ambiguity on tonal audio. Correlation
   is now pre-emphasised and sub-sample interpolated.
5. **Full-audio render merged into video render.** The planner merged the
   audio-only full-timeline request with a video request, which would have
   triggered a full video render in Resolve. They are now always separate, and
   the mock test asserts it.
6. **Audio-only render coverage**, **frame-rate mismatch detection** and
   **corrupted media error mapping** were corrected.
7. **Level cap below master quality.** With VBV now applied, small test
   masters exceeded their declared level. The patch VBV now follows the
   master's measured peak in that case, so the patch is never below master
   quality.
8. Two **test-fixture bugs** (synthetic generator off-by-one in chroma, extra
   audio sample on deletions) were caught by the engine's own verification.
   That shows the guard and sync checks detect 1-frame and 1-sample errors.

## Not tested / untestable here

| Item | Status | How to test |
|---|---|---|
| Real DaVinci Resolve integration | **UNTESTED** (no Resolve in the Linux build environment; bridge verified against an API mock only) | `docs/MANUAL_RESOLVE_TESTS.md` R1–R18 |
| SwiftUI app build and UI | **UNTESTED – not compiled** (Swift toolchain download blocked by the environment's network policy) | `packaging/build_app.sh` runs `swift test` (SRXCore tests) then builds; manual test R20 |
| Apple Silicon performance | **UNTESTED** (x86 container) | run `engine/demo.py` and the slow test on the M4 |
| AudioToolbox AAC (`aac_at`) splice | **UNTESTED** (macOS-only encoder). The engine measures the encoder delay at runtime and verifies every splice, so a mismatch would be refused, not shipped | re-run `test_simultaneous_audio_and_video_revision` on macOS |
| Masters exported by Resolve's own H.264 encoder (Apple VideoToolbox bitstreams) | **UNTESTED** – tests used libx264-encoded masters | manual R6–R9 |
| Playback compatibility of multi-SPS outputs in QuickTime/Safari/YouTube | **UNTESTED** here; FFmpeg decodes them with zero errors | manual R19 |
| Code signing / notarization | not done (no credentials) – local development build | – |
