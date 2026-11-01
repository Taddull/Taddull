#!/bin/bash
# Remove Smart Revision Exporter and (optionally) its data.
# DaVinci Resolve is never modified by this application, so nothing there needs undoing.
set -euo pipefail
APP="/Applications/Smart Revision Exporter.app"
DATA="$HOME/Library/Application Support/Smart Revision Exporter"
PREFS="$HOME/Library/Preferences/local.smartrevisionexporter.app.plist"

if [[ -d "$APP" ]]; then rm -rf "$APP"; echo "removed $APP"; fi
if [[ "${1:-}" == "--all" ]]; then
  # job logs, verification reports, revision history, frame-hash cache, optional venv
  rm -rf "$DATA" && echo "removed $DATA"
  rm -f "$PREFS" && echo "removed $PREFS"
else
  echo "kept $DATA (logs, reports, revision history). Run with --all to remove it."
fi
echo "Your master files and exported revisions are not touched."
