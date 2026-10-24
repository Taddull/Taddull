# Handoff: finish MaxTrace+ on the user's Mac

This file is for a Claude Code session running **locally on the user's Mac**.
MaxTrace+ was built in a cloud session that had no DaVinci Resolve. Read
`README.md`, `docs/FUSION_API_NOTES.md` and `docs/TEST_REPORT.md` first.

## What exists (all in this folder)

* `resolve/MaxTrace+.lua`: Resolve menu launcher (marker line
  `MAXTRACE_PLUS_LAUNCHER`). It loads the app from
  `~/Library/Application Support/MaxTrace+/app/lua/maxtrace/main.lua`.
* `lua/maxtrace/*.lua`: UIManager panel (`ui.lua`), controller (`main.lua`),
  Fusion integration (`fusionio.lua`), worker jobs (`worker.lua`), JSON,
  config, util. Lua 5.1/LuaJIT, run with `dofile`.
* `engine/`: Python CV engine run as a separate process
  (`venv/bin/python3 -I engine/maxtrace_worker.py <job_dir>`), communicating
  through job files (`job.json` in; `status.lua` and `result.lua` out).
* `install.sh` (`--check` diagnoses), `uninstall.sh`, plus double-click
  `Install MaxTrace+.command` and `Check MaxTrace+.command`.
* `tests/`: 62 offline tests (pytest; the Lua tests need `lupa`).

## The open problem

The user installed it, restarted Resolve, and **MaxTrace+ does not appear
under Workspace > Scripts**. The cause is unknown; it was never seen on a
real Mac. The installer copies the launcher into
`~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/{Comp,Utility}/MaxTrace+.lua`
(and the same folders inside `~/Library/Containers/com.blackmagic-design.*` if present).

Hypotheses to test, in order:

1. The installer never finished, or never ran. Check
   `~/Library/Application Support/MaxTrace+/logs/install.log` and run `./install.sh --check`.
2. This Resolve reads scripts from another folder: a Mac App Store build,
   a system-wide `/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts`,
   or a custom *Scripts:* path map. Find the real folder by asking Resolve:
   `fu:MapPath("Scripts:")` and `fu:MapPathSegments("Scripts:")` (see *Live access* below).
3. A menu quirk: no script is listed at all, or only under submenus. Test with
   a trivial `hello.lua` (`print("hello")`) in the same folder.
4. The free edition of Resolve 19.1+ (no UIManager for scripts). The menu
   entry would still appear, but the panel cannot open.
5. The filename. `+` is believed fine (a Reactor script is named
   "Notepad++.lua"), but compare with a test file named `MaxTracePlus.lua`.

## Live access to Resolve (do this to test for real)

Resolve ships `fuscript`, e.g.
`/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fuscript`.
With Resolve running and **Preferences > System > General > External
scripting using: Local** enabled (ask the user to set it; it is their
choice), you can run Lua against the live app:

```bash
FS="/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fuscript"
"$FS" -l lua -x 'fu = bmd.scriptapp("Fusion"); print(fu:MapPath("Scripts:")); local v = fu:GetVersion(); print(v.App, v[1], v[2], v[3]); print(fu:GetCurrentComp())'
```

(If `-x` is not supported by that build, write the Lua to a file and run
`"$FS" -l lua file.lua`. For Python use
`/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/` README + `DaVinciResolveScript`.)

With live access, also verify on the real app what the cloud session could
only simulate: `comp:Render({Tool=saver, FrameRange="t..t", Wait=true})`
writing a PNG, `comp:Paste(bmd.readstring(text))` with the generated
`highlight.setting`, the PolylineStroke rendering and its write-on, and
`fu.UIManager` being non-nil. Fix any difference in `lua/maxtrace/fusionio.lua`
or `engine/maxtrace/fusion_setting.py`, re-run `python3 -m pytest tests -q`,
reinstall, and confirm with the user in the Resolve UI.

## Rules from the user's original brief (keep them)

* Don't fake success; report what was and wasn't verified live.
* Don't modify unrelated scripts, Resolve preferences or the user's files.
  Ask before changing a Resolve setting.
* Keep user presets, settings and calibration across reinstalls.
* The panel must open from Workspace > Scripts > MaxTrace+ on the Fusion
  page, and Generate Highlight must produce a working animation over the
  selected Paint/MediaIn node.
