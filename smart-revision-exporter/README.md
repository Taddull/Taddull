# Smart Revision Exporter

Revise 5 seconds of a 15-minute DaVinci Resolve documentary without
re-exporting 15 minutes, and prove that nothing else changed.

Smart Revision Exporter takes your approved H.264 MP4 master and the revised
Resolve timeline. It renders only the frames that must be rebuilt, copies every
other compressed frame byte-for-byte, and then decodes the result to verify
that every unchanged frame is pixel-identical (SHA-256 per decoded frame)
before writing the new file. The original master is never modified.

```
master.mp4 ──► analyse GOPs / IDRs ──► plan ──► Resolve renders only [revised GOPs]
                                         │                      │
                                         ▼                      ▼
                         copy unchanged packets ◄── libx264 patch (matched SPS/PPS, VUI, level)
                                         │
                                         ▼
                   assemble MP4 (exact timestamps, merged parameter sets, audio splice)
                                         │
                                         ▼
           verify: frame count · timestamps · colour · SHA-256 of every unchanged frame ·
                   PSNR of re-encoded frames · guard frames · audio sync  ──► master_rev2.mp4
```

## Status of this deliverable

| Part | State |
|---|---|
| Patch engine (`engine/srx`) | **Working, tested** – 79 automated tests pass on synthetic footage, including a 15-minute master (see `docs/TEST_REPORT.md`) |
| Verification engine | **Working, tested** – also cross-checked with FFmpeg's independent `framehash` |
| DaVinci Resolve bridge | Implemented with documented API calls only; **tested against an API mock, not yet against real Resolve** (manual checklist: `docs/MANUAL_RESOLVE_TESTS.md`) |
| macOS SwiftUI app (`app/`) | Source complete; **not compiled in the build environment** (Linux container, Swift toolchain download blocked). `packaging/build_app.sh` runs its unit tests and builds it on macOS |
| Packaging | Build script, Info.plist, icon, uninstall script – **local development build** (ad-hoc signed, not notarized) |

## Quick start (Mac)

```bash
brew install ffmpeg python
```

```bash
cd smart-revision-exporter && ./packaging/build_app.sh --install
```

Then open *Smart Revision Exporter*, choose your master, import the In/Out
range from Resolve and click **Smart Export**. See `docs/INSTALL.md` and
`docs/USER_GUIDE.md`.

Try the engine without Resolve (synthetic 1080p master, 5-second revision):

```bash
cd smart-revision-exporter/engine && python3 demo.py
```

Run the test suite:

```bash
cd smart-revision-exporter/engine && python3 -m pytest -m "not slow"
```

## Key facts

* **Unchanged frames:** every frame outside the rebuilt GOPs is the master's
  own compressed packet and is verified pixel-identical after decoding.
* **Boundary frames:** H.264 frames between a revision and the next IDR depend
  on revised frames, so they are re-rendered and re-encoded (quality measured,
  reported separately, typically 40–50 dB PSNR vs the master). *Strict* mode
  refuses instead. A **Revision-Ready Master** (1 s closed GOP or all-intra)
  reduces them to ≤ 1 s, or to zero.
* **Audio:** copied bit-for-bit when untouched; otherwise AAC packets are
  spliced on the master's frame grid (bit-identical outside two transition
  blocks, sync measured to the sample), or the track is re-encoded from an
  audio-only render.
* **Safety:** atomic output, never overwrites, cancellation-safe, crash
  recovery, a job manifest and log per export, and revision history across
  rounds without generation loss.

## Repository layout

```
engine/       Python engine (no required third-party packages) + tests + demo
app/          SwiftUI app (SRXCore library + app target + XCTest)
packaging/    build_app.sh, Info.plist, icon generator, AppIcon.icns, uninstall.sh
docs/         INSTALL, USER_GUIDE, TECHNICAL_REPORT, TEST_REPORT, MANUAL_RESOLVE_TESTS, test-results/
```
