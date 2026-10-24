#!/bin/bash
# MaxTrace+ installer (macOS, user-level, no administrator rights needed).
#
#   ./install.sh                 install or update
#   ./install.sh --check         only diagnose an existing installation (changes nothing)
#   ./install.sh --with-tests    also install pytest into the engine venv and run the test suite
#   ./install.sh --python PATH   use a specific Python 3.9+ interpreter
#
# Installs:
#   ~/Library/Application Support/MaxTrace+/app        application files (replaced on update)
#   ~/Library/Application Support/MaxTrace+/venv       isolated Python with NumPy + OpenCV
#   ~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility/MaxTrace+.lua
#   (Utility scripts are listed under Workspace > Scripts on every page; the
#   same folder inside Mac App Store sandbox containers is covered too)
# Never touches: user presets, settings, calibration, rendered highlights,
# other scripts, Resolve's own Python or preferences.

set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUPPORT="${MAXTRACE_HOME:-$HOME/Library/Application Support/MaxTrace+}"
APP="$SUPPORT/app"
VENV="$SUPPORT/venv"
RESOLVE_USER="$HOME/Library/Application Support/Blackmagic Design/DaVinci Resolve"
SCRIPTS_ROOT="${MAXTRACE_SCRIPTS_ROOT:-$RESOLVE_USER/Fusion/Scripts}"
LAUNCHER_NAME="MaxTrace+.lua"
WITH_TESTS=0
CHECK_ONLY=0
PYTHON_OVERRIDE=""

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
}
is_ours() { grep -q "MAXTRACE_PLUS_LAUNCHER" "$1" 2>/dev/null; }

while [ $# -gt 0 ]; do
	case "$1" in
	--with-tests) WITH_TESTS=1 ;;
	--check) CHECK_ONLY=1 ;;
	--python) shift; PYTHON_OVERRIDE="${1:-}" ;;
	-h|--help) sed -n '2,18p' "$0"; exit 0 ;;
	*) echo "Unknown option: $1" >&2; exit 2 ;;
	esac
	shift
done

say() { printf '\033[1m%s\033[0m\n' "$*"; }
note() { printf '  %s\n' "$*"; }
die() { printf '\033[31mError:\033[0m %s\n' "$*" >&2; exit 1; }

say "MaxTrace+ $(cat "$SRC/VERSION") installer"

# --- Environment checks -------------------------------------------------------
OS="$(uname -s)"
ARCH="$(uname -m)"
note "System: $OS $ARCH"
if [ "$OS" != "Darwin" ] && [ -z "${MAXTRACE_HOME:-}" ]; then
	die "MaxTrace+ installs into DaVinci Resolve on macOS. (Set MAXTRACE_HOME to install elsewhere for testing.)"
fi

RESOLVE_APP=""
for cand in "/Applications/DaVinci Resolve/DaVinci Resolve.app" "/Applications/DaVinci Resolve Studio/DaVinci Resolve.app" "/Applications/DaVinci Resolve.app"; do
	if [ -d "$cand" ]; then RESOLVE_APP="$cand"; break; fi
done
if [ -n "$RESOLVE_APP" ]; then
	RVER="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$RESOLVE_APP/Contents/Info.plist" 2>/dev/null || echo unknown)"
	note "DaVinci Resolve: $RVER ($RESOLVE_APP)"
else
	RVER="not found"
	note "DaVinci Resolve: not found in /Applications (installing anyway)"
fi
DOCS="/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/README.txt"
if [ -f "$DOCS" ]; then
	note "Scripting docs: $DOCS"
else
	note "Scripting docs: not found (optional)"
fi

# --- Diagnosis only ---------------------------------------------------------------
if [ "$CHECK_ONLY" = "1" ]; then
	say "Checking the MaxTrace+ installation"
	found=0
	while IFS= read -r root; do
		for sub in Utility Comp; do
			f="$root/$sub/$LAUNCHER_NAME"
			if [ -f "$f" ]; then
				found=1
				if is_ours "$f"; then note "menu script OK:      $f"; else note "FOREIGN file:        $f"; fi
			else
				note "no menu script in:   $root/$sub"
			fi
		done
	done < <(script_roots)
	[ -f "$APP/lua/maxtrace/main.lua" ] && note "application OK:      $APP" || note "application MISSING: $APP"
	if [ -x "$VENV/bin/python3" ]; then
		"$VENV/bin/python3" -I "$APP/engine/maxtrace_worker.py" --selftest >/dev/null 2>&1 \
			&& note "engine OK:           $VENV" || note "engine BROKEN:       $VENV (run ./install.sh again)"
	else
		note "engine MISSING:      $VENV"
	fi
	[ -f "$SUPPORT/logs/maxtrace.log" ] && { note "last log lines:"; tail -n 5 "$SUPPORT/logs/maxtrace.log" | sed 's/^/      /'; }
	[ "$found" = "1" ] || note "=> The menu script is not installed. Run ./install.sh and read its output for errors."
	note "After installing, quit and reopen DaVinci Resolve, then look in Workspace > Scripts."
	exit 0
fi

while IFS= read -r root; do
	for sub in Utility Comp; do
		f="$root/$sub/$LAUNCHER_NAME"
		if [ -e "$f" ] && ! is_ours "$f"; then
			die "$f exists and was not installed by MaxTrace+. Rename or remove it, then run the installer again."
		fi
	done
done < <(script_roots)

# --- Python for the engine ----------------------------------------------------
pick_python() {
	local c
	for c in "$PYTHON_OVERRIDE" /opt/homebrew/bin/python3 /usr/local/bin/python3 \
		/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 \
		/Library/Frameworks/Python.framework/Versions/3.12/bin/python3 \
		/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 \
		/Library/Frameworks/Python.framework/Versions/3.10/bin/python3 \
		"$(command -v python3 2>/dev/null || true)" /usr/bin/python3; do
		[ -n "$c" ] && [ -x "$c" ] || continue
		if "$c" -c 'import sys,venv; sys.exit(0 if sys.version_info >= (3, 9) else 1)' >/dev/null 2>&1; then
			echo "$c"; return 0
		fi
	done
	return 1
}
PY="$(pick_python)" || die "Python 3.9 or newer is required (install from python.org or Homebrew, or the Xcode Command Line Tools), then run this installer again."
PYVER="$("$PY" -c 'import sys,platform; print("%d.%d.%d %s" % (sys.version_info[:3] + (platform.machine(),)))')"
note "Python for the engine: $PY ($PYVER)"
if [ "$ARCH" = "arm64" ] && ! echo "$PYVER" | grep -q arm64; then
	note "Warning: this Python is not native arm64; the engine will run under Rosetta."
fi

# --- Application files ----------------------------------------------------------
say "Installing application files"
mkdir -p "$SUPPORT" "$SUPPORT/presets" "$SUPPORT/logs" "$SUPPORT/cache" "$SUPPORT/renders"
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

# --- Resolve menu script (installed first so the menu entry exists even if a
# later step fails; the panel then explains what is missing) -----------------
say "Installing the Resolve script"
LAUNCHERS=""
while IFS= read -r root; do
	mkdir -p "$root/Utility"
	cp "$APP/resolve/$LAUNCHER_NAME" "$root/Utility/$LAUNCHER_NAME"
	note "$root/Utility/$LAUNCHER_NAME"
	LAUNCHERS="$LAUNCHERS $root/Utility/$LAUNCHER_NAME"
	# Earlier versions installed into Comp/; avoid a duplicate menu entry.
	if [ -f "$root/Comp/$LAUNCHER_NAME" ] && is_ours "$root/Comp/$LAUNCHER_NAME"; then
		rm -f "$root/Comp/$LAUNCHER_NAME"
	fi
	case "$root" in
	*Containers*) note "Note: this is a Mac App Store (sandboxed) Resolve; macOS may block MaxTrace+ from starting its engine there." ;;
	esac
done < <(script_roots)

# --- Isolated Python environment ------------------------------------------------
say "Preparing the computer-vision engine (isolated Python environment)"
if [ -x "$VENV/bin/python3" ] && ! "$VENV/bin/python3" -c 'import sys' >/dev/null 2>&1; then
	rm -rf "$VENV"
fi
if [ ! -x "$VENV/bin/python3" ]; then
	"$PY" -m venv "$VENV" || die "Could not create the Python environment at $VENV"
fi
"$VENV/bin/python3" -m pip install --disable-pip-version-check -q --upgrade pip >/dev/null 2>&1 || true
"$VENV/bin/python3" -m pip install --disable-pip-version-check -q -r "$APP/requirements.txt" \
	|| die "Installing NumPy/OpenCV failed (internet access is needed during installation only)."
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

  Quit and reopen DaVinci Resolve Studio (it reads the Scripts folders at
  startup). Then go to the Fusion page, select your Paint (or MediaIn) node
  and choose  Workspace > Scripts > MaxTrace+.
  Problems?  ./install.sh --check

  Uninstall:  "$SRC/uninstall.sh"
EOF
