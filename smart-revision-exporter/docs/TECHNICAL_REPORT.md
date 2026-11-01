# Smart Revision Exporter – Technical Report

Engine version 1.0.0 · local development build

This report explains how the patch engine works, what it guarantees, what it
cannot do, and what was actually verified. Every claim of a passing result
links to an automated test in `engine/tests/`; see `TEST_REPORT.md` for the
full traceability matrix.

## 1. Architecture

```
┌──────────────────────────┐   JSON-lines over stdout    ┌───────────────────────────────┐
│ SwiftUI app (macOS)      │ ──────────────────────────▶ │ srx engine (Python 3, stdlib) │
│  SRXCore: process client,│ ◀── SIGINT = cancel ─────── │  analysis · planning · encode │
│  models, timecode        │                             │  assembly · verification      │
└──────────────────────────┘                             └──────┬───────────────┬────────┘
                                                                │               │
                                       official scripting API   │               │ subprocess
                                                                ▼               ▼
                                                   DaVinci Resolve      FFmpeg / FFprobe / libx264
```

* **Process boundary.** The app never touches media itself. It runs
  `python3 -m srx <command> --json` and renders the event stream (stages,
  progress, ETA, CPU/memory statistics, warnings, plan, result). Cancelling
  sends SIGINT; the engine stops Resolve/FFmpeg, deletes the partial output and
  exits with code 130.
* **Engine modules** (`engine/srx/`):

| Module | Responsibility |
|---|---|
| `mp4.py` | Strict ISO-BMFF reader (every sample's offset, size, DTS, CTS, sync flag) and a writer that rebuilds sample tables and copies sample payloads byte-for-byte |
| `h264.py`, `bitio.py` | NAL parsing, full SPS/VUI/HRD parser, PPS, slice-header prefix, SEI (incl. libx264 settings string), avcC |
| `media.py` | Master analysis: CFR check, edit lists, IDR detection by NAL type, clean cut points, resume points, GOP statistics, audio layout |
| `plan.py` | Revision normalisation/merging, reconstruction regions, guard frames, frame mapping (incl. duration changes), audio strategy, render requests |
| `encoder.py` | libx264 settings derived from the master's SPS/PPS, patch validation (parameter sets, reorder depth, applied encoder settings) |
| `audio.py` | AAC copy / packet splice on the master's frame grid / full re-encode, alignment measurement |
| `assemble.py` | Output MP4 from copied master packets + patch packets; merged parameter-set record |
| `verify.py` | Verification engine (section 5) |
| `resolve_bridge.py` | DaVinci Resolve scripting integration (section 6) |
| `exporter.py`, `jobs.py` | Mode orchestration, job manifests, atomic output, crash recovery, revision history |

## 2. The core problem and the solution

H.264 P- and B-frames reference other frames, so a frame in the middle of a
GOP cannot simply be swapped. The engine works with two exact, provable
properties of the bitstream instead of heuristics:

* **Clean cut point *k*.** The first *k* frames in *decode* order are exactly
  the first *k* frames in *display* order. A picture can only reference
  pictures decoded before it, so the decode-order prefix ending at a clean cut
  point is self-contained. Its frames decode to the same pixels whatever
  follows. With B-frames, clean cut points occur after every mini-GOP
  (every 1–4 frames with typical encoders); with no B-frames, after every frame.
* **Resume point *r*.** A clean cut point whose decode-order sample is an **IDR**
  access unit (NAL type 5, checked in the bitstream, not just the MP4 sync
  flag). An IDR clears all references, so the decode-order suffix starting
  there is self-contained.

Non-IDR I-frames (open GOP / recovery point) are **never** used as resume
points, because later pictures may reference pictures before them.

For a revision covering master frames *[a, b)*:

1. reconstruction start *k* = the largest clean cut point ≤ *a*: unchanged
   frames before the revision are kept down to the mini-GOP;
2. reconstruction end *r* = the smallest resume point ≥ *b* (the next IDR);
3. the rendered range is *[k, r)*. Frames in *[k, a)* and *[b, r)* are
   **boundary frames**: their content is unchanged but they must be
   re-encoded because later frames of the GOP depend on revised frames;
4. everything else is copied as the master's original compressed packets.

Overlapping or touching reconstruction regions are merged. Strict mode refuses
any plan with boundary frames and explains the options instead.

### Why boundary frames cannot be avoided in a long-GOP master

Frames after the revision but before the next IDR reference revised pictures.
To decode them unchanged, the decoder would need the *original* revised
pictures in its reference buffer while it displays the *new* ones. H.264 has
no "decode but don't display" picture, and MP4 edit lists cannot hide
individual B/P frames portably. These frames are therefore rendered fresh from
Resolve and re-encoded at high quality. The quality is measured, and they are
reported separately as *boundary frames*, never claimed as preserved. A
Revision-Ready Master (section 8) reduces them to at most one keyframe
interval, or to zero with all-intra.

## 3. Joining H.264 streams correctly

The engine does **not** use FFmpeg's concat demuxer. It writes the MP4 itself:

* **Parameter sets.** Patch segments are encoded with libx264 using an SPS/PPS
  id that no copied master frame references (`sps-id`). The output `avcC`
  holds the master's sets plus the patch set, and every patch IDR also carries
  its SPS/PPS in-band for decoders that load only the first avcC entry. Each
  IDR activates the right set. Only sets referenced by output frames are kept,
  so repeated cycles don't accumulate unused sets. Id conflicts with
  different content are detected and refused.
* **Bitstream compatibility.** The patch SPS is parsed and compared with the
  master's: profile, chroma format, bit depth, dimensions (incl. cropping),
  frame/field coding, colour primaries/transfer/matrix, full-range flag, SAR,
  chroma location and maximum reorder depth. The entropy coder (CABAC/CAVLC)
  and the 8×8 transform follow the master's PPS.
* **Applied settings are checked, not assumed.** libx264 writes its effective
  settings into an SEI message. The engine parses it and fails if B-frames,
  keyframe interval, VBV, CABAC or open-GOP differ from what was requested.
  This check exists because testing found that FFmpeg silently dropped the VBV
  option when the SAR value contained a `:` separator.
* **Timestamps.** Output DTS are `index × frame_duration`. Every frame's CTS
  is `cts0 + display_index × frame_duration`, with `cts0` (the master's
  composition offset and edit list) kept identical. B-frames in the patch are
  allowed only if their reorder delay fits inside the master's composition
  offset; otherwise the patch is re-encoded without B-frames. Frame rate,
  timescale, frame count and edit list stay identical (or are adjusted exactly
  for duration-changing revisions).
* **Bitrate.** The patch VBV respects the master's declared level. If the
  master itself already exceeds its level, the cap is 1.25× the master's own
  measured 1-second peak, so the patch is never lower quality than the master
  around it. A note is added to the report.
* **Container.** Other tracks, `udta`/`meta`, `colr`/`pasp` boxes and the
  faststart layout are preserved. `btrt` is recomputed. 64-bit offsets are
  used automatically for files over 4 GB.

## 4. Audio

AAC-LC is an MDCT codec with 50 % overlap. Decoded block *i* is the
overlap-add of packets *i−1* and *i*, so independently encoded AAC segments
cannot simply be concatenated.

| Strategy | When | What happens |
|---|---|---|
| **copy** | no revision touches audio | every AAC packet is copied; decoded PCM verified identical |
| **splice** (default for audio revisions) | AAC-LC, no duration change | replace packets *[p, q)* on the master's own frame grid, ≥ 2 frames (2048 samples) away from the revised audio; the new encode starts *W* packets earlier with an input offset computed from the master's priming (edit-list `media_time`) and the encoder's measured delay, so the grids align sample-exactly |
| **full** | duration changes, non-AAC-LC audio, or user choice | the whole track is re-encoded from an **audio-only** Resolve render (no video render) with the master's sample rate, channels and bitrate |

Alignment between Resolve's render and the master is **measured**, not
assumed. It uses cross-correlation (pre-emphasised, with sub-sample
interpolation) on unchanged audio around the splice. This matters at 29.97 fps,
where a frame boundary is 1601.6 samples.

Splice encodes run with FFmpeg's perceptual noise substitution (PNS) disabled.
PNS makes decoder output depend on a running random-number state, so PNS
packets would break bit-identical decoding of every later packet, now and in
future revision cycles. This was found by the repeated-cycle test. If the
**master** uses PNS, bit-identity after a splice is impossible. Verification
detects this and refuses the result, recommending full re-encode
(`test_pns_master_audio_splice_is_not_silently_accepted`).

## 5. Verification engine

Nothing is reported as successful unless it was measured:

| Check | Method |
|---|---|
| Structure | own MP4 parser + ffprobe: frame count, rational frame rate & timescale, dimensions, pixel format, colour metadata (container and VUI), CFR composition timestamps, segment starts on IDR resume points, segment ends on clean cuts, parameter sets |
| Preserved frames (Verified Patch) | full decode of the output; SHA-256 of every decoded frame in the master's native pixel format (no conversion, no frame-rate conversion: `-fps_mode passthrough`), compared with the master's decoded frame hashes (cached by the master's SHA-256) |
| Preserved frames (Fast Patch) | only GOPs around each splice decoded and compared; the rest is reported as "not decoded" with a warning |
| Encode fidelity | PSNR of every re-encoded frame against the exact frame given to the encoder (min over Y, U, V ≥ 35 dB) |
| Unchanged content | boundary frames and ≥ 6 extra **guard** frames rendered fresh around each revision are compared with the master (min-plane PSNR ≥ 30 dB). This catches edits that extend beyond the declared range (e.g. transitions), a wrong master, or a moved timeline. The per-plane minimum catches chroma-only changes; testing showed luma alone misses a hue transition. |
| Seams | copied frames adjacent to each splice decode identically |
| Black frames | re-encoded frames that are black where the render is not |
| Decoder errors | any decoder/demuxer message in decoded ranges fails verification |
| Audio | per strategy: packet byte identity, PCM bit-identity outside transition blocks, transition SNR vs render (click detection), sync lag (sub-sample), duration, level/SNR vs master |

The output is written to a hidden `.<name>.srx-partial-<job>.mp4` next to the
destination. It is moved into place with a hard link only after verification
passes, and never over an existing file. Failed outputs are moved to the job
folder as `FAILED-<name>` for inspection.

**Processing cost of verification** (reported in every report): full decode
of the output, plus a one-time full decode of the master (cached afterwards).
In the 15-minute test (480×270), verification of 26,973 frames took 22.9 s on
this 4-core x86 container.

## 6. DaVinci Resolve integration

Only methods documented in Blackmagic's scripting README are used, and
optional ones are probed at runtime (`srx resolve status` lists them). See the
module docstring in `resolve_bridge.py` for the full list.

* Connects to a running Resolve (`scriptapp("Resolve")`), reads project,
  timeline, frame rate (decimal → exact rational: 23.976 → 24000/1001), drop
  frame, start frame/timecode, resolution, In/Out (`GetMarkInOut`, Resolve 19+,
  optional) and duration markers.
* Renders exact ranges (`MarkIn`/`MarkOut`, absolute timeline frames,
  inclusive) to a high-quality intermediate: ProRes 422 HQ, then 4444, then
  DNxHR, chosen from `GetRenderCodecs`. Audio is Linear PCM where accepted.
  Audio-only requests render with video export disabled. It polls
  `GetRenderJobStatus`, detects failure and cancellation, locates the output
  via `GetRenderJobList`, deletes the temporary render job and restores the
  user's render settings (saved as a temporary preset when the API allows).
* Each render is validated before use: exact frame count, frame rate,
  resolution, audio layout.
* **Not available from Resolve:** which frames changed since the last export.
  Revision ranges always come from the user (In/Out, markers, manual timecode).
  The guard-frame comparison is the safety net for mistakes.
* `srx resolve alignment MASTER` renders a 16-frame probe and finds the master
  frame offset that matches it (−3…+3). This verifies the master/timeline
  relationship before patching.
* **Fallback:** when external scripting is unavailable, the user renders the
  requested ranges manually and imports them (`files` source). They are
  validated in exactly the same way.

**Integration status:** the bridge is exercised against an API mock that
mirrors the documented object model (`resolve_mock.py`): render job creation,
polling, output discovery, cleanup, settings restore, audio-only rendering,
failure and not-running cases. It has **not** been run against a real Resolve
installation in this environment (Linux container, no Resolve). The manual
test procedure is in `MANUAL_RESOLVE_TESTS.md`.

## 7. Supported inputs

| Item | Supported | Not supported (refused with explanation) |
|---|---|---|
| Container | MP4/MOV (`avc1`, `avc3`), faststart or not, > 4 GB | fragmented MP4 |
| Video | H.264 Baseline/Main/High/High 10/High 4:2:2, progressive, CFR, closed or open GOP (open-GOP I-frames ignored as splice points) | HEVC, ProRes, AV1 masters; interlaced/MBAFF; VFR; FMO; multi-edit edit lists; resolution changes |
| Frame rates | any rational CFR; tested 23.976, 24, 25, 29.97, 30, 59.94, 60 | – |
| Audio | AAC-LC (copy/splice/full); other codecs: copy or full re-encode | HE-AAC splicing (full re-encode only) |

## 8. Revision-Ready Master (Engine C)

A one-time full render, encoded with libx264 (`keyint = min-keyint = N`,
`scenecut=0`, closed GOP, B-pyramid) or all-intra, keeping the delivery format
(H.264 High, MP4, same colour tags/AAC). Measured trade-offs:

| Structure | Unchanged frames re-encoded per revision | Size vs 10 s GOP | Notes |
|---|---|---|---|
| all-intra (`keyint=1`) | **0** – every frame outside revisions stays pixel-identical (`test_strict_mode_on_all_intra_master`) | typically 3–6× | standard High profile; high bitrate |
| 1 s closed GOP | ≤ 1 s after + ≤ 3 frames before | a few % larger | recommended default |
| 2 s closed GOP | ≤ 2 s after + ≤ 3 frames before | ~1–3 % larger | |
| ProRes intermediate master | – | 10–20× | not offered as delivery; a ProRes render is used only internally for patch segments |

Resolve users can get a similar structure directly from the Deliver page:
H.264, *Keyframes: Every N frames* and *Frame reordering* off. The engine
analyses whatever structure the master has.

## 9. VideoToolbox

Patch segments are encoded with libx264, not VideoToolbox: VideoToolbox can't
be constrained to a chosen parameter-set id, B-pyramid depth or closed GOP, so
the joined stream could not be guaranteed decodable. Verification uses
FFmpeg's software H.264 decoder for deterministic, bit-exact reference
decoding. Patches are short (seconds), so libx264 at preset *slow* runs in
seconds on Apple Silicon. Resolve's own renders use whatever hardware Resolve
chooses.

## 10. Performance (measured in this container: 4 vCPU x86-64, no GPU)

15-minute 29.97 fps master (480×270, GOP 250, B-frames), 5-second
video+audio revision at 7:30 (`test_five_second_revision_in_fifteen_minute_master`):

| | |
|---|---|
| Frames rendered | 257 of 26,973 (0.95 %) |
| Frames preserved (packet copy, verified identical) | 26,723 |
| Re-encoded | 250 (150 revised + 100 boundary) |
| Encode / audio / assemble | 0.66 s / 2.2 s / 0.9 s |
| Verification (full decode, every frame) | 22.9 s |
| Render | 128 s – synthetic generator artefact (FFmpeg must synthesise every frame from 0 to reach 7:30); in Resolve a render of 257 frames is independent of position |

On the MacBook Air M4, expect assembly to be limited by SSD throughput (a
copy of the master, ~2 GB), and verification by H.264 software decode
(roughly 300–600 fps at 1080p with multithreading). That is about 1–2 minutes
for a 15-minute 1080p master, plus a one-time equal cost for the master
(cached). These numbers are estimates, not measured on an M4.

## 11. Known limitations

1. Long-GOP masters: unchanged frames between a revision and the next IDR are
   re-encoded (reported as boundary frames). Remedy: Revision-Ready Master.
2. The fresh render must match how the master was rendered (same Resolve
   version, render settings and data levels). If it doesn't, the guard check
   fails and the export is refused rather than producing a visible seam.
3. External scripting may be unavailable in some DaVinci Resolve (free)
   releases. Use manual render import.
4. HDR (PQ/HLG) metadata SEI (mastering display, content light level) in the
   master is not re-emitted in patch segments. Colour description is matched;
   HDR delivery is untested.
5. The macOS app was not compiled in this environment (Swift toolchain
   download blocked). `build_app.sh` runs the Swift unit tests and builds on
   the Mac. The UI is untested until then.
6. Code signing: ad-hoc only, not notarized.
