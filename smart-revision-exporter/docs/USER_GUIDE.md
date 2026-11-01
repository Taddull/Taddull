# User Guide

Smart Revision Exporter replaces only the revised seconds of an approved
H.264 MP4 instead of re-exporting the whole programme. It proves that every
other frame is still pixel-identical before it gives you the file.

## The workflow

1. Open DaVinci Resolve with your project and the timeline you delivered.
2. Make the client's changes on the timeline.
3. Open **Smart Revision Exporter**. The *DaVinci Resolve* card shows the
   connected project, timeline, frame rate and start timecode.
4. **Choose Master…**: select the MP4 you delivered last time. It is analysed
   (resolution, frame rate, GOP structure, colour, audio) and opened read-only.
   The badge must say **PATCHABLE**.
5. Mark what changed (any of these):
   * In Resolve, set In/Out around the change, then **Import In/Out**.
   * Put **duration markers** over each change (any colour; a name starting
     with `REV` helps), then **Import Markers**.
   * **Add** a range at the playhead and type exact timecodes. The Out
     timecode is inclusive, like Resolve's Out point.
6. Check the timeline strip. Blue is what you revised. Amber is unchanged
   frames that must be re-encoded because of the master's GOP structure.
   Everything grey is copied untouched. The header shows how much will be
   rendered.
7. Pick the mode (**Verified Patch** is recommended) and the output name
   (a new file such as `MyDoc_rev2.mp4`, which is suggested automatically).
8. Click **Smart Export** (⌘E). Resolve renders only the required ranges,
   the patch is built, and the result is verified.
9. When the report says **Verified**, the file is in place. Click
   **Approve as New Base** to make it the master for the next round.

You don't need the Terminal.

## Revision ranges: getting them right

* **Transitions and temporal effects.** If a dissolve, motion blur,
  stabilisation or speed ramp near your change also changed, include those
  frames in the range or add **handles** (the two steppers on each row: frames
  before/after). The app warns when a revision edge is within 12 frames of a
  clip edit point.
* **You can't break the master by getting it wrong.** The engine renders
  extra *guard* frames around every revision and compares them with the
  master. If anything outside your declared range changed, the export is
  refused with the exact frames listed. Widen the range and run it again.
* **Overlapping ranges** are merged automatically (or click **Merge**).
* **Audio-only changes** (music, VO, SFX): untick **V**. No video is
  re-encoded at all. **Video-only changes**: untick **A** and the original
  audio is kept bit-for-bit.
* **Duration changes** (a section got longer or shorter) are supported by the
  engine (`delta` in the request / CLI `--rev START:END,delta=N`). The whole
  audio track is then re-encoded from an audio-only Resolve render, because
  every later AAC frame shifts.

## Export modes

| Mode | Renders | Verification | Use when |
|---|---|---|---|
| **Fast Patch** | revised GOPs | structure + frames around every splice | quick internal previews |
| **Verified Patch** | revised GOPs | full decode, every unchanged frame compared (SHA-256) | client delivery (default) |
| **Revision-Ready Master** | whole timeline once | structure, GOP layout, full decode | before the first revision round of a new project, so later patches touch fewer frames |
| **Safe Full Export** | whole timeline | structure vs current master, full decode | when a patch is refused or the edit changed most of the programme |

**Strict frame preservation** refuses to re-encode any unchanged frame. With
a long-GOP master this usually means the patch is refused, with an explanation
and options. With an all-intra Revision-Ready Master it always works.

## Reading the verification report

* **Pixel-identical**: unchanged frames compared and identical. In Verified
  mode this equals *Unchanged compared*, which equals every frame outside the
  rebuilt GOPs.
* **Re-encoded / Boundary**: frames that were re-encoded. Boundary frames
  have unchanged content. Their PSNR against the master is shown (typically
  40–50 dB, i.e. visually identical but not bit-identical).
* **Encode PSNR min**: how closely the re-encoded frames match Resolve's fresh
  render.
* **Audio**: *copy* (bit-identical), *splice* (bit-identical outside the two
  transition blocks, with sync lag 0 measured) or *full* (re-encoded, aligned
  to within half a sample).
* Each check has a one-line explanation. **Open Report** opens the Markdown
  report with all numbers, segments and the exact encoder settings.

If verification fails, **no output is delivered**. The failed file is kept
in the job folder for inspection, and your master is untouched.

## Repeated revision rounds

Approve each verified output as the new base. In the next round, everything
outside the new revision, including earlier patches, is copied packet for
packet. Unchanged material is never re-encoded twice, so quality does not
degrade over rounds. The history (base, revisions, output, verification
result, SHA-256 of every file) is kept per project.

## Without Resolve scripting (manual render import)

If the Resolve card says *Not connected*:

1. Add your revisions and look at the plan. The amber+blue ranges, plus a few
   frames either side, are what needs rendering. `srx plan` prints exact
   timeline frames.
2. In Resolve's Deliver page, render that In/Out range as **QuickTime, Apple
   ProRes 422 HQ, Linear PCM audio**, at the timeline resolution and frame
   rate.
3. **Import Render…** and set the render's start timecode.
4. Smart Export. The render is validated (frame count, rate, size) before it
   is used.

## Getting the most out of it

* For new projects, export a **Revision-Ready Master** (1 s closed GOP).
  Later revisions then re-encode at most about 1 second of unchanged frames
  per change. With **all-intra**, zero.
* In Resolve's own H.264 export, *Keyframes: Every 24–30 frames* with *Frame
  reordering* off gives a similar effect.
* Keep the render settings (resolution, data levels, colour space tags) the
  same as for the master. Otherwise the fresh render won't match the master
  and the guard check will refuse the patch.

## Troubleshooting

| Message | Meaning / fix |
|---|---|
| *Could not connect to DaVinci Resolve* | Resolve not running, or External scripting is not set to Local |
| *timeline frame rate … differs from the master* | wrong master or wrong timeline is open |
| *frames OUTSIDE the declared revision ranges differ* | your edit is longer than the range (transition?), or the timeline moved. Widen the range or add handles |
| *Strict Verified Frame Preservation cannot be met* | the master's GOP structure forces re-encoding of unchanged frames; disable Strict or use a Revision-Ready Master |
| *decoded audio outside the splice regions differs … PNS* | the master's AAC uses noise substitution; choose Audio ▸ Re-encode full track |
| *output already exists* | choose a new name; files are never overwritten |
| *not enough disk space* | the export needs about the master's size plus the intermediate renders |
