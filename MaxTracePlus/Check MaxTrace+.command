#!/bin/bash
# Double-click to diagnose a MaxTrace+ installation; the report is also saved
# to your Desktop so you can send it.
cd "$(dirname "$0")" || exit 1
/bin/bash ./install.sh --check 2>&1 | tee "$HOME/Desktop/MaxTrace+ check.txt"
echo
echo "Saved to: $HOME/Desktop/MaxTrace+ check.txt"
read -r -p "Press Return to close this window." _
