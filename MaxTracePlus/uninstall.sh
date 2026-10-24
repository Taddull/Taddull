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
SCRIPTS_ROOT="${MAXTRACE_SCRIPTS_ROOT:-$HOME/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts}"
PURGE=0
[ "${1:-}" = "--purge" ] && PURGE=1

roots=("$SCRIPTS_ROOT")
if [ -z "${MAXTRACE_SCRIPTS_ROOT:-}" ]; then
	for c in "$HOME"/Library/Containers/com.blackmagic-design.*/Data/Library/Application\ Support/Blackmagic\ Design/DaVinci\ Resolve; do
		[ -d "$c" ] && roots+=("$c/Fusion/Scripts")
	done
fi
for root in "${roots[@]}"; do
	for sub in Utility Comp; do
		f="$root/$sub/MaxTrace+.lua"
		[ -f "$f" ] || continue
		if grep -q "MAXTRACE_PLUS_LAUNCHER" "$f"; then
			rm -f "$f"
			echo "Removed $f"
		else
			echo "Left $f in place (not a MaxTrace+ file)."
		fi
	done
done

if [ -d "$SUPPORT" ]; then
	rm -rf "$SUPPORT/app" "$SUPPORT/venv" "$SUPPORT/python" "$SUPPORT/cache" "$SUPPORT/logs" "$SUPPORT/.app.new" "$SUPPORT/.python.new" "$SUPPORT/install-info.json"
	echo "Removed application, engine, cache and logs from $SUPPORT"
	if [ "$PURGE" = "1" ]; then
		rm -rf "$SUPPORT"
		echo "Removed all MaxTrace+ user data."
	else
		echo "Kept user presets/settings and rendered highlights in $SUPPORT (use --purge to delete)."
	fi
fi
echo "MaxTrace+ uninstalled. Generated MaxTrace_* nodes in your compositions are ordinary Fusion nodes and can be deleted normally."
