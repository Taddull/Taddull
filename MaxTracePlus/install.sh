#!/bin/bash
# MaxTrace+ installer (macOS, user-level, no administrator rights needed).
#
#   ./install.sh                 install or update
#   ./install.sh --check         only diagnose an existing installation (changes nothing)
#   ./install.sh --with-tests    also install pytest into the engine venv and run the test suite
#   ./install.sh --python PATH   use a specific Python 3.9-3.13 interpreter
#
# Double-clickable alternatives: "Install MaxTrace+.command", "Check MaxTrace+.command".
#
# Installs:
#   ~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Comp/MaxTrace+.lua
#   ~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility/MaxTrace+.lua
#       (same file in both: Comp scripts are listed on the Fusion page,
#        Utility scripts on every page; Mac App Store containers are covered too)
#   ~/Library/Application Support/MaxTrace+/app        application files (replaced on update)
#   ~/Library/Application Support/MaxTrace+/venv       isolated Python with NumPy + OpenCV
#   ~/Library/Application Support/MaxTrace+/python     private Python, only if no usable one exists
# Never touches: user presets, settings, calibration, rendered highlights,
# other scripts, Resolve's own Python or preferences.
# A full log is written to ~/Library/Application Support/MaxTrace+/logs/install.log

set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUPPORT="${MAXTRACE_HOME:-$HOME/Library/Application Support/MaxTrace+}"
APP="$SUPPORT/app"
VENV="$SUPPORT/venv"
PRIVATE_PY="$SUPPORT/python"
RESOLVE_USER="$HOME/Library/Application Support/Blackmagic Design/DaVinci Resolve"
SCRIPTS_ROOT="${MAXTRACE_SCRIPTS_ROOT:-$RESOLVE_USER/Fusion/Scripts}"
LAUNCHER_NAME="MaxTrace+.lua"
MENU_DIRS="Comp Utility"
WITH_TESTS=0
CHECK_ONLY=0
PYTHON_OVERRIDE=""

# Standalone CPython (astral-sh/python-build-standalone), pinned with checksums.
PBS_BASE="https://github.com/astral-sh/python-build-standalone/releases/download/20241016"
PBS_ARM="cpython-3.12.7%2B20241016-aarch64-apple-darwin-install_only.tar.gz"
PBS_ARM_SHA="4c18852bf9c1a11b56f21bcf0df1946f7e98ee43e9e4c0c5374b2b3765cf9508"
PBS_X86="cpython-3.12.7%2B20241016-x86_64-apple-darwin-install_only.tar.gz"
PBS_X86_SHA="60c5271e7edc3c2ab47440b7abf4ed50fbc693880b474f74f05768f5b657045a"

while [ $# -gt 0 ]; do
	case "$1" in
	--with-tests) WITH_TESTS=1 ;;
	--check) CHECK_ONLY=1 ;;
	--python) shift; PYTHON_OVERRIDE="${1:-}" ;;
	-h|--help) sed -n '2,22p' "$0"; exit 0 ;;
	*) echo "Unknown option: $1" >&2; exit 2 ;;
	esac
	shift
done

mkdir -p "$SUPPORT/logs"
LOG="$SUPPORT/logs/install.log"
exec > >(tee -a "$LOG") 2>&1
echo "===== $(date) install.sh $* ====="

say() { printf '\033[1m%s\033[0m\n' "$*"; }
note() { printf '  %s\n' "$*"; }
die() { printf '\033[31mError:\033[0m %s\n' "$*"; printf '  (full log: %s)\n' "$LOG"; exit 1; }

# Every Fusion "Scripts" folder Resolve may read: the standard per-user one
# and the ones inside Mac App Store sandbox containers.
script_roots() {
	echo "$SCRIPTS_ROOT"
	if [ -z "${MAXTRACE_SCRIPTS_ROOT:-}" ]; then
		local c
		for c in "$HOME"/Library/Containers/com.blackmagic-design.*/Data/Library/Application\ Support/Blackmagic\ Design/DaVinci\ Resolve; do
			[ -d "$c" ] && echo "$c/Fusion/Scripts"
		done
	fi
	return 0
}
is_ours() { grep -q "MAXTRACE_PLUS_LAUNCHER" "$1" 2>/dev/null; }

say "MaxTrace+ $(cat "$SRC/VERSION") installer"

# --- Environment ----------------------------------------------------------------
OS="$(uname -s)"
ARCH="$(uname -m)"
MACOS="$(sw_vers -productVersion 2>/dev/null || echo "?")"
note "System: $OS $ARCH (macOS $MACOS)"
if [ "$OS" != "Darwin" ] && [ -z "${MAXTRACE_HOME:-}" ]; then
	die "MaxTrace+ installs into DaVinci Resolve on macOS. (Set MAXTRACE_HOME to install elsewhere for testing.)"
fi

RVER="not found"
for cand in "/Applications/DaVinci Resolve/DaVinci Resolve.app" /Applications/DaVinci\ Resolve*/DaVinci\ Resolve*.app /Applications/DaVinci\ Resolve*.app; do
	if [ -d "$cand" ]; then
		RVER="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$cand/Contents/Info.plist" 2>/dev/null || echo unknown)"
		note "DaVinci Resolve: $RVER ($cand)"
		break
	fi
done
[ "$RVER" = "not found" ] && note "DaVinci Resolve: not found in /Applications (installing anyway)"
if pgrep -xq "Resolve" 2>/dev/null; then
	note "Resolve is running: quit and reopen it after installing so it lists the new script."
fi

# --- Diagnosis only ---------------------------------------------------------------
if [ "$CHECK_ONLY" = "1" ]; then
	say "Checking the MaxTrace+ installation"
	found=0
	while IFS= read -r root; do
		for sub in $MENU_DIRS; do
			f="$root/$sub/$LAUNCHER_NAME"
			if [ -f "$f" ]; then
				found=1
				if is_ours "$f"; then note "menu script OK:      $f"; else note "FOREIGN file:        $f"; fi
			else
				note "no menu script in:   $root/$sub"
			fi
		done
		if [ -d "$root" ]; then
			note "contents of $root:"
			(cd "$root" && find . -maxdepth 2 | sed 's/^/      /' | head -40)
		else
			note "folder does not exist: $root"
		fi
	done < <(script_roots)
	[ -f "$APP/lua/maxtrace/main.lua" ] && note "application OK:      $APP" || note "application MISSING: $APP"
	if [ -x "$VENV/bin/python3" ]; then
		if "$VENV/bin/python3" -I "$APP/engine/maxtrace_worker.py" --selftest >/dev/null 2>&1; then
			note "engine OK:           $VENV"
		else
			note "engine BROKEN:       $VENV (run the installer again)"
		fi
	else
		note "engine MISSING:      $VENV"
	fi
	[ -f "$SUPPORT/logs/maxtrace.log" ] && { note "last panel log lines:"; tail -n 8 "$SUPPORT/logs/maxtrace.log" | sed 's/^/      /'; }
	[ "$found" = "1" ] || note "=> The menu script is not installed. Run the installer and read its output for errors."
	note "Resolve reads the Scripts folders when it starts: quit and reopen it, then look in Workspace > Scripts."
	exit 0
fi

while IFS= read -r root; do
	for sub in $MENU_DIRS; do
		f="$root/$sub/$LAUNCHER_NAME"
		if [ -e "$f" ] && ! is_ours "$f"; then
			die "$f exists and was not installed by MaxTrace+. Rename or remove it, then run the installer again."
		fi
	done
done < <(script_roots)

# --- Application files ----------------------------------------------------------
say "Installing application files"
mkdir -p "$SUPPORT" "$SUPPORT/presets" "$SUPPORT/cache" "$SUPPORT/renders"
STAGE="$SUPPORT/.app.new"
rm -rf "$STAGE"
mkdir -p "$STAGE"
for d in engine lua presets resolve docs; do
	[ -d "$SRC/$d" ] && cp -R "$SRC/$d" "$STAGE/"
done
cp "$SRC/VERSION" "$SRC/requirements.txt" "$SRC/README.md" "$STAGE/" 2>/dev/null || true
find "$STAGE" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
rm -rf "$APP.old"
[ -d "$APP" ] && mv "$APP" "$APP.old"
mv "$STAGE" "$APP"
rm -rf "$APP.old"
note "$APP"

# --- Resolve menu script. Installed before anything that can fail, so the
# menu entry always exists; the panel then explains anything still missing. ---
say "Installing the Resolve script"
LAUNCHERS=""
while IFS= read -r root; do
	for sub in $MENU_DIRS; do
		mkdir -p "$root/$sub"
		cp "$APP/resolve/$LAUNCHER_NAME" "$root/$sub/$LAUNCHER_NAME"
		chmod 644 "$root/$sub/$LAUNCHER_NAME"
		note "$root/$sub/$LAUNCHER_NAME"
		LAUNCHERS="$LAUNCHERS $root/$sub/$LAUNCHER_NAME"
	done
	case "$root" in
	*Containers*) note "Note: this is a Mac App Store (sandboxed) Resolve; macOS may block MaxTrace+ from starting its engine there." ;;
	esac
done < <(script_roots)

# --- Python for the engine ----------------------------------------------------
py_ok() {
	"$1" -c 'import sys, venv; sys.exit(0 if (3, 9) <= sys.version_info[:2] <= (3, 13) else 1)' >/dev/null 2>&1
}
pick_python() {
	local c
	local cands=("$PYTHON_OVERRIDE" /opt/homebrew/bin/python3 /usr/local/bin/python3)
	for v in 3.13 3.12 3.11 3.10 3.9; do
		cands+=("/Library/Frameworks/Python.framework/Versions/$v/bin/python3" "/opt/homebrew/bin/python$v" "/usr/local/bin/python$v")
	done
	cands+=("$PRIVATE_PY/bin/python3")
	c="$(command -v python3 2>/dev/null || true)"
	[ -n "$c" ] && [ "$c" != "/usr/bin/python3" ] && cands+=("$c")
	# /usr/bin/python3 is only a stub (it opens an install dialog) unless the
	# Xcode Command Line Tools are installed.
	if xcode-select -p >/dev/null 2>&1; then cands+=(/usr/bin/python3); fi
	for c in "${cands[@]}"; do
		[ -n "$c" ] && [ -x "$c" ] || continue
		if py_ok "$c"; then echo "$c"; return 0; fi
	done
	return 1
}
download_python() {
	local file sha url tgz
	case "$ARCH" in
	arm64) file="$PBS_ARM"; sha="$PBS_ARM_SHA" ;;
	x86_64) file="$PBS_X86"; sha="$PBS_X86_SHA" ;;
	*) return 1 ;;
	esac
	url="$PBS_BASE/$file"
	tgz="$SUPPORT/cache/python.tar.gz"
	note "No suitable Python found; downloading a private Python 3.12 (about 16 MB)..."
	curl -fsSL --retry 3 -o "$tgz" "$url" || return 1
	if [ "$(shasum -a 256 "$tgz" | awk '{print $1}')" != "$sha" ]; then
		rm -f "$tgz"
		note "Checksum mismatch for the downloaded Python; not using it."
		return 1
	fi
	rm -rf "$PRIVATE_PY" "$SUPPORT/.python.new"
	mkdir -p "$SUPPORT/.python.new"
	tar -xzf "$tgz" -C "$SUPPORT/.python.new" || return 1
	mv "$SUPPORT/.python.new/python" "$PRIVATE_PY"
	rm -rf "$SUPPORT/.python.new" "$tgz"
	xattr -dr com.apple.quarantine "$PRIVATE_PY" 2>/dev/null || true
	py_ok "$PRIVATE_PY/bin/python3"
}

say "Preparing the computer-vision engine"
PY="$(pick_python || true)"
if [ -z "$PY" ]; then
	download_python || die "No Python 3.9-3.13 found and the private Python download failed. The menu script IS installed; install Python from https://www.python.org/downloads/macos/ and run the installer again."
	PY="$PRIVATE_PY/bin/python3"
fi
PYVER="$("$PY" -c 'import sys,platform; print("%d.%d.%d %s" % (sys.version_info[:3] + (platform.machine(),)))')"
note "Python: $PY ($PYVER)"

# A venv built from a different interpreter is rebuilt.
if [ -x "$VENV/bin/python3" ]; then
	if ! "$VENV/bin/python3" -c 'import sys' >/dev/null 2>&1 || ! grep -q "$("$PY" -c 'import sys; print(sys.base_prefix)')" "$VENV/pyvenv.cfg" 2>/dev/null; then
		rm -rf "$VENV"
	fi
fi
if [ ! -x "$VENV/bin/python3" ]; then
	"$PY" -m venv "$VENV" || die "Could not create the Python environment at $VENV"
fi
"$VENV/bin/python3" -m pip install --disable-pip-version-check -q --upgrade pip >/dev/null 2>&1 || true
"$VENV/bin/python3" -m pip install --disable-pip-version-check -q -r "$APP/requirements.txt" \
	|| die "Installing NumPy/OpenCV failed (internet access is needed during installation only). The menu script IS installed."
SELF="$("$VENV/bin/python3" -I "$APP/engine/maxtrace_worker.py" --selftest)" || die "Engine self-test failed."
note "Engine: $SELF"

# --- Smoke test: trace a generated chart with the installed engine -----------
say "Running a detection smoke test"
SMOKE="$SUPPORT/cache/smoke"
rm -rf "$SMOKE"; mkdir -p "$SMOKE/job"
"$VENV/bin/python3" -I - "$APP" "$SMOKE" <<'PYEOF'
import json, os, sys
app, smoke = sys.argv[1], sys.argv[2]
sys.path.insert(0, os.path.join(app, "engine"))
import cv2, numpy as np
img = np.full((540, 960, 3), 255, np.uint8)
pts = np.array([[60, 400], [200, 150], [330, 380], [470, 120], [620, 330], [900, 90]], np.int32)
cv2.polylines(img, [pts], False, (40, 40, 220), 3, cv2.LINE_AA)
cv2.imwrite(os.path.join(smoke, "chart.png"), img)
job = {"job": "build", "image": os.path.join(smoke, "chart.png"), "cache_dir": smoke,
       "timing": {"fps": 24, "duration": 2.5, "start_frame": 0, "comp_start": 0, "comp_end": 60},
       "output": {"mode": "native", "comp_width": 1920, "comp_height": 1080}}
json.dump(job, open(os.path.join(smoke, "job", "job.json"), "w"))
from maxtrace.worker import run_job
code = run_job(os.path.join(smoke, "job"))
res = json.load(open(os.path.join(smoke, "job", "result.json")))
ok = code == 0 and res.get("ok") and res["selected"]["points"] >= 4
print("  smoke test:", "passed" if ok else "FAILED", "-", res.get("message", "%d points, confidence %.2f" % (res["selected"]["points"], res["selected"]["confidence"])) if res.get("ok") else res.get("message"))
sys.exit(0 if ok else 1)
PYEOF
rm -rf "$SMOKE"

if [ "$WITH_TESTS" = "1" ]; then
	say "Running the full test suite"
	"$VENV/bin/python3" -m pip install --disable-pip-version-check -q pytest lupa
	(cd "$SRC" && "$VENV/bin/python3" -m pytest tests -q)
fi

cat > "$SUPPORT/install-info.json" <<EOF
{"version": "$(cat "$SRC/VERSION")", "installed": "$(date -u +%Y-%m-%dT%H:%M:%SZ)", "resolve": "$RVER", "python": "$PYVER", "launchers": "$LAUNCHERS"}
EOF

say "Done."
cat <<EOF

  1. Quit DaVinci Resolve completely (Cmd+Q) and open it again -
     it only reads the Scripts folders when it starts.
  2. Go to the Fusion page, select your Paint (or MediaIn) node.
  3. Workspace > Scripts > MaxTrace+   (on the Fusion page it can also be
     under a "Comp" submenu; on other pages under "Utility").

  Problems?  run "Check MaxTrace+.command" (or ./install.sh --check)
  and send the output.  Full log: $LOG
EOF
