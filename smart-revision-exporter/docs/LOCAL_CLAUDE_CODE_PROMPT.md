I'm on my MacBook Air M4 (Apple Silicon) with DaVinci Resolve installed. Your job is to turn an existing project into a working script inside my real DaVinci Resolve, test it for real, and fix whatever breaks.

## Background (you don't have the earlier conversation, so read this)

In a cloud Claude Code session we built "Smart Revision Exporter". When a client asks for a 5–20 s change in a finished 15-minute H.264 MP4 documentary, it re-renders only the revised part from Resolve. It copies every other compressed frame unchanged, then decodes the result and proves every unchanged frame is pixel-identical (SHA-256 per decoded frame) before writing a new file. The master is never modified.

The code is on GitHub: repo `Taddull/Taddull`, branch `claude/davinci-smart-revision-exporter-tsgju6`, folder `smart-revision-exporter/`.

What's in it:
- `engine/srx/`: Python engine (standard library only; numpy optional) plus FFmpeg. CLI: `python3 -m srx doctor|probe|plan|export|prepare-master|full-export|resolve status|resolve ranges|resolve alignment|jobs|project|frame|filmstrip`. With `--json` it emits JSON-lines events.
- `engine/srx/resolve_bridge.py`: Resolve integration using only documented scripting API calls. It renders exact ranges (`MarkIn`/`MarkOut` = absolute timeline frames, inclusive) to ProRes 422 HQ + Linear PCM, polls the job, deletes it, and restores render settings. Audio-only requests render with video export off.
- `engine/srx/render.py`: render sources. `FileRenderSource` uses renders that already exist (path + absolute timeline start frame).
- `engine/tests/`: 79 pytest tests on synthetic footage, all passing on Linux.
- `app/`: SwiftUI macOS app (`SRXCore` + views). It was **never compiled**.
- `packaging/build_app.sh`, icon, `uninstall.sh`.
- `docs/`: TECHNICAL_REPORT, TEST_REPORT (lists what is UNTESTED), MANUAL_RESOLVE_TESTS (R1–R20), USER_GUIDE, INSTALL.

The cloud session ran on Linux with no Resolve and no Swift. Never tested:
1. Real Resolve.
2. The macOS app build.
3. macOS-only behaviour: FFmpeg's `aac_at` (AudioToolbox) encoder is preferred automatically on macOS and was never tested.
4. Masters encoded by Resolve's own H.264 encoder.
5. Playback of patched files in QuickTime/Safari/YouTube.

Before changing anything, read `README.md`, `docs/TECHNICAL_REPORT.md`, `docs/TEST_REPORT.md`, `docs/MANUAL_RESOLVE_TESTS.md`, `engine/srx/resolve_bridge.py`, `engine/srx/cli.py`, `engine/srx/render.py` and `engine/srx/exporter.py`.

## Step 1 – Set up and run the engine tests on this Mac

1. Clone the repo (use `gh auth login` first if it's private) into `~/Developer/Taddull`, check out the branch, and work in `smart-revision-exporter/`.
2. Check: macOS version, `uname -m` (arm64), DaVinci Resolve version and whether it's Studio or free, `python3 --version` (3.9+), and `ffmpeg -encoders | grep -E "libx264|aac_at"`.
   - If FFmpeg or Python is missing, **ask me** before running `brew install ffmpeg python`.
3. Run `python3 -m srx doctor` from `engine/`.
4. Run `python3 -m pytest -m "not slow"` from `engine/`.
   - Fix any macOS-specific failure. Pay special attention to audio-splice tests with `aac_at`.
   - If `aac_at` can't pass the splice bit-identity checks, make the engine fall back to FFmpeg's native `aac` for splices and document why.
   - Never weaken a verification threshold or skip a test to get green.
5. Run `python3 -m pytest tests/test_long.py -m slow -s` once.
6. Run `python3 demo.py` and record the timings. This is the first measurement on Apple Silicon.

## Step 2 – Build the in-Resolve script (the main goal)

Create a script that appears in Resolve under **Workspace ▸ Scripts ▸ Smart Revision Exporter**, plus an installer.

**Installer** (`packaging/install_resolve_script.sh`):
- Copy `engine/srx` to `~/Library/Application Support/Smart Revision Exporter/engine/srx`, so the script doesn't depend on the clone's location.
- Install the menu script into `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility/`.
- Never modify Resolve's installation, its `/Applications` bundle or its preferences. The user Scripts folder is the only Resolve-related place you may write to.
- Also add an uninstaller (or extend `packaging/uninstall.sh`).

**Script design.** Check every API call against `/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/README.txt` on this Mac. Don't invent methods; probe optional ones (e.g. `Timeline.GetMarkInOut` is Resolve 19+).

1. **Get the Resolve object** from inside Resolve: try the injected `resolve` global, then `app.GetResolve()`, then `bmd.scriptapp("Resolve")`. This works without "External scripting = Local".
   - Add a small constructor to `ResolveSession` that wraps an existing Resolve object (e.g. `ResolveSession.attach(resolve_obj)`) instead of calling `scriptapp`.
2. **UI.** Use Fusion's UIManager window (`fusion.UIManager` + `bmd.UIDispatcher`) if available. Blackmagic has restricted UIManager in some free releases, so detect it and fall back to macOS dialogs via `osascript` (choose file, choose from list, display dialog/notification). The UI should show:
   - project/timeline/frame rate/start timecode;
   - the master file picker (remember the last master per project+timeline in a JSON in the app-support folder);
   - revision ranges: auto-filled from Timeline In/Out and duration markers (name starting with `REV` or a chosen colour), editable, with handles before/after and V/A toggles;
   - the mode: Verified Patch (default), Fast Patch, Revision-Ready Master, Safe Full Export;
   - audio strategy;
   - the output name: suggest `<master>_rev2.mp4` etc.; never overwrite.
3. **Plan.** Run the engine **as a subprocess** with the user's system Python, not Resolve's embedded one: `python3 -m srx plan --request <json> --json` with `PYTHONPATH` set to the installed engine. Show rendered %, re-encoded frames, boundary frames and warnings before exporting.
4. **Render inside Resolve.** Do every render request from the plan (`plan.renders`: absolute timeline frames, end exclusive, `video` flag) with `ResolveSession.render_range` through the attached Resolve object. Save into the job's temp folder. Show progress and support Cancel (`StopRendering`, delete the job, restore settings).
5. **Patch and verify** in a subprocess:

   ```bash
   python3 -m srx export --request <json> --json
   ```

   Use source `{"type": "files", "fps": ..., "timeline_offset": <timeline start frame>, "renders": [{"path": ..., "timeline_start": ...}, ...]}`, so the patching never needs external scripting.
   - **Known gap to fix:** `FileRenderSource` currently assumes every render contains video. Extend it to accept audio-only renders (needed for the full-track audio re-encode, which must stay audio-only — never turn it into a full video render). Add a test.
   - Stream the JSON events to the progress UI.
6. **Finish.** On success, show the verification summary (frames compared / pixel-identical / re-encoded / boundary / audio result), open `report.md`, and reveal the output in Finder. On failure, show the exact failure message. The engine never delivers an unverified file.
7. **Responsiveness.** If running the subprocess or polling blocks Resolve's UI, run the work so Resolve stays responsive (background thread or detached process with a status file), and test it.
8. **Master ↔ timeline offset.** Master frame 0 = timeline start frame unless the master was exported from an In/Out range. Let me set an offset, and offer the "check alignment" probe (the logic in `cli.py::_check_alignment`, adapted to the attached session).

## Step 3 – Build the macOS app (secondary)

Run `./packaging/build_app.sh`. It runs `swift test` and then builds. Fix compile errors with minimal changes, keeping behaviour as designed. Add a "Open in Resolve script" note to the app if useful, but the Resolve menu script is the priority.

## Step 4 – Test for real

Ask me to open a small test project, or create a test timeline yourself via the API in a NEW project named "SRX Test" (never touch my real projects). Use a 2–3 minute 1080p timeline at 01:00:00:00 with H.264 clips, a Fusion title, a grade, a cross-dissolve, music and VO.

1. Export a master with my normal YouTube H.264 preset.
2. Run every applicable item of `docs/MANUAL_RESOLVE_TESTS.md` R1–R20 through the new menu script, including at 29.97 drop-frame. Cover: transition refused without handles / accepted with handles; audio-only; full audio; cancel mid-render (master SHA-256 unchanged); render failure; Revision-Ready Master; Safe Full Export.
3. Open the patched files in QuickTime Player and Safari and check the splice points by eye, frame by frame.

Record every result (pass/fail, numbers, timings on the M4) in `docs/TEST_REPORT.md`. Mark anything you couldn't run as UNTESTED with the reason.

## Rules

- Correctness over speed. Don't weaken verification, don't claim anything works unless you ran it, and don't hide limitations.
- Never overwrite or modify my master files or any existing file; outputs are always new files.
- Only documented Resolve API calls. Don't modify Resolve's installation; only the user Scripts folder.
- Ask me before installing software, deleting anything outside the repo/its own data folders, or doing anything that needs a Resolve preference change (tell me exactly what to click).
- Commit work in small steps on the same branch (`claude/davinci-smart-revision-exporter-tsgju6`) and push when done. Run `python3 -m pytest -m "not slow"` before each push.

## When you finish, report

- How to launch it in Resolve (exact menu path).
- What passed, failed, or is untested, with numbers.
- Any change to engine behaviour and why.
- Remaining limitations, e.g. free vs Studio scripting restrictions you hit.
