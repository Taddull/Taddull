#!/bin/bash
# MaxTrace+ uninstaller.
#
#   ./uninstall.sh            remove the script, application, engine and caches;
#                             keep user presets, settings and rendered highlights
#   ./uninstall.sh --purge    also delete user presets, settings, calibration and
#                             rendered highlight sequences (compositions that use
#                             a rendered MaxTrace_Render node will show it as missing)

set -euo pipefail

SUPPORT="${MAXTRACE_HOME:-$HOME/Library/Application Support/MaxTrace+}"
SCRIPTS_COMP="${MAXTRACE_SCRIPTS_DIR:-$HOME/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Comp}"
LAUNCHER="$SCRIPTS_COMP/MaxTrace+.lua"
PURGE=0
[ "${1:-}" = "--purge" ] && PURGE=1

if [ -f "$LAUNCHER" ]; then
	if grep -q "MAXTRACE_PLUS_LAUNCHER" "$LAUNCHER"; then
		rm -f "$LAUNCHER"
		echo "Removed $LAUNCHER"
	else
		echo "Left $LAUNCHER in place (not a MaxTrace+ file)."
	fi
fi

if [ -d "$SUPPORT" ]; then
	rm -rf "$SUPPORT/app" "$SUPPORT/venv" "$SUPPORT/cache" "$SUPPORT/logs" "$SUPPORT/.app.new" "$SUPPORT/install-info.json"
	echo "Removed application, engine, cache and logs from $SUPPORT"
	if [ "$PURGE" = "1" ]; then
		rm -rf "$SUPPORT"
		echo "Removed all MaxTrace+ user data."
	else
		echo "Kept user presets/settings and rendered highlights in $SUPPORT (use --purge to delete)."
	fi
fi
echo "MaxTrace+ uninstalled. Generated MaxTrace_* nodes in your compositions are ordinary Fusion nodes and can be deleted normally."
