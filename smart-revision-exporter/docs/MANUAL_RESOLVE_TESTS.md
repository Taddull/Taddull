# Manual integration tests with DaVinci Resolve

The Resolve bridge is tested automatically against an API mock
(`engine/tests/test_modes.py`). A real Resolve installation was not available
in the build environment, so these tests must be run once on the target Mac
before relying on the integration. Record the results in `TEST_REPORT.md`.

Preparation: Resolve running, *External scripting using: Local*, a test project
with a 2–3 minute timeline (start 01:00:00:00) containing H.264 clips, a
Fusion title, a colour grade, a cross-dissolve, music and VO.

```bash
cd smart-revision-exporter/engine
```

| # | Test | Steps | Expected |
|---|---|---|---|
| R1 | Connection | `python3 -m srx resolve status` | `connected: true`, correct project/timeline, frame rate as exact rational, start frame (e.g. 86400 at 24 fps), `api` lists the available methods |
| R2 | Not running | quit Resolve, repeat R1 | `connected: false`, code `resolve_not_running`, no crash |
| R3 | No project | Resolve open at Project Manager, repeat R1 | code `no_project` |
| R4 | In/Out import | set In/Out on the timeline, run `python3 -m srx resolve ranges` | range equals the marks (Out inclusive → `end` = Out+1); `master_start` = In − timeline start |
| R5 | Range markers | add a duration marker named `REV test`, repeat R4 | marker range listed |
| R6 | Master export | deliver the whole timeline as H.264 MP4 (your normal preset) → `master.mp4`; `python3 -m srx probe master.mp4` | `patchable: true`; note GOP structure |
| R7 | Alignment | `python3 -m srx resolve alignment master.mp4` | `aligned: true`, `best_offset: 0`, PSNR ≥ 30 dB |
| R8 | Video revision | change the grade of a 5 s section, In/Out over it, export from the app (Verified Patch) | Resolve shows a temporary render job that disappears afterwards; render settings restored; report PASSED; preserved frames = all frames outside the rebuilt GOPs |
| R9 | Fusion/title revision | edit a Fusion title text, repeat R8 | PASSED |
| R10 | Transition | change a cross-dissolve, set In/Out **excluding** the dissolve's first frames | export REFUSED with "frames OUTSIDE the declared revision ranges"; repeat with handles → PASSED |
| R11 | Audio-only | change VO level on a 4 s section, revision with V unticked | no video re-encoded (`reencoded_frames` 0), audio splice PASSED, lag 0 |
| R12 | Full audio | Audio ▸ Re-encode full track | Resolve render job is audio-only (Export Video off); PASSED; sync check lag ≤ 0.5 samples |
| R13 | 29.97 DF | timeline at 29.97 drop-frame; repeat R8 | timecodes shown with `;`, PASSED |
| R14 | Cancel | start an export with a long revision, press Cancel during the render | Resolve render stops, job deleted, no output file, master unchanged (compare SHA-256) |
| R15 | Render failure | set the target volume read-only or disconnect media, export | clear "render failed" error, no output |
| R16 | Manual import | disable external scripting; render the requested range manually (ProRes 422 HQ + LPCM), import in the app | PASSED |
| R17 | Revision-Ready Master | mode Revision-Ready Master, 1 s | output analysed: IDR every second; a later revision has ≤ 1 s boundary frames |
| R18 | Safe Full Export | mode Safe Full Export with your delivery preset | PASSED structural verification; master untouched |
| R19 | Playback | open patched outputs in QuickTime Player, Safari, VLC; upload one to YouTube as unlisted | plays seamlessly across splices; no glitches at splice points |
| R20 | App UI | timeline navigation (arrows, ⇧arrows, Home/End), timecode entry, Diagnostics, Approve as New Base | behave as described in the User Guide |

Report any differences in the Resolve API (methods missing or returning
different shapes). `srx resolve status` prints the probed method list.
