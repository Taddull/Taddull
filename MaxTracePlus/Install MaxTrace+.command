#!/bin/bash
# Double-click to install or update MaxTrace+ (opens in Terminal).
cd "$(dirname "$0")" || exit 1
/bin/bash ./install.sh
status=$?
echo
if [ $status -eq 0 ]; then echo "Installation finished."; else echo "Installation reported a problem (see above)."; fi
read -r -p "Press Return to close this window." _
