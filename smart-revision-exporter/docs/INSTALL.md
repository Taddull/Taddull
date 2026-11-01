# Installation

Smart Revision Exporter is a **local development build**. It is ad-hoc signed,
not notarized, and is built from source on your Mac.

## Requirements

| Component | Version | Why |
|---|---|---|
| macOS on Apple Silicon | 13 Ventura or later (built for arm64) | app |
| Xcode or Command Line Tools | Swift 5.9+ (`xcode-select --install`) | building the app |
| Python 3 | 3.9 or later (python.org or Homebrew) | engine and Resolve scripting |
| FFmpeg + FFprobe with **libx264** | 5.1+ (Homebrew `ffmpeg` includes libx264) | analysis, patch encoding, verification |
| DaVinci Resolve | 18.5+ (19 recommended; In/Out import needs 19) | rendering revised ranges |
| numpy (optional) | any | faster PSNR/audio maths; the app can install it |

## 1. Install dependencies

```bash
brew install ffmpeg python
```

Check them:

```bash
cd smart-revision-exporter/engine
python3 -m srx doctor
```

Every line marked `required` must show `"ok": true`.

## 2. Allow DaVinci Resolve scripting

1. Open DaVinci Resolve.
2. Go to **Preferences ▸ System ▸ General** and set **External scripting using: Local**.
3. Keep Resolve running with your project and timeline open.

Smart Revision Exporter uses Resolve's official scripting module at
`/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules`.
It does **not** modify Resolve, its installation or its preferences. It
temporarily creates a render job, removes it afterwards and restores your
render settings. If your Resolve edition refuses external scripting, use
**Manual render import** (see the User Guide).

## 3. Build the app

```bash
cd smart-revision-exporter
./packaging/build_app.sh
```

This runs the Swift unit tests (`swift test`), builds an arm64 release,
embeds the engine and icon, and ad-hoc signs `dist/Smart Revision Exporter.app`.
To also copy it to /Applications:

```bash
./packaging/build_app.sh --install
```

On first launch macOS will say the app is from an unidentified developer.
Right-click the app, choose **Open**, then **Open** again.

## 4. Permissions

* **Files:** the app only reads the master you choose and writes the output
  you choose (via the standard open/save panels), plus its own data folder
  `~/Library/Application Support/Smart Revision Exporter`.
* **Automation:** none. Resolve is controlled through its own scripting
  library, not Apple Events.

## 5. Diagnostics and logs

* **Help ▸ Diagnostics…** shows dependency checks, the Resolve API methods
  available in your version, the Python path, and buttons to install numpy and
  to recover interrupted jobs.
* Every job has a folder in
  `~/Library/Application Support/Smart Revision Exporter/jobs/<id>/` with
  `job.json` (recoverable manifest), `log.jsonl` (all events and FFmpeg
  commands), `plan.json`, `report.json` and `report.md`.
* Command line equivalents:

  ```bash
  python3 -m srx doctor
  ```

  ```bash
  python3 -m srx jobs list
  ```

  ```bash
  python3 -m srx jobs recover
  ```

## 6. Uninstall

```bash
./packaging/uninstall.sh
```

This removes the app and keeps your logs, reports and revision history.
To remove those too:

```bash
./packaging/uninstall.sh --all
```

Your masters and exported revisions are never touched, and nothing needs
undoing in DaVinci Resolve.

## Using the engine without the app

The engine is a standard Python package with no required third-party
dependencies:

```bash
cd smart-revision-exporter/engine
python3 -m srx export master.mp4 -o master_rev2.mp4 --rev 13500:13650 --source resolve
```

Run `python3 -m srx --help` for every command.
