#!/usr/bin/env bash
# Scans home directory for viruses on POSIX systems

LOG_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/clamav"
SCAN_PATHS=(
  "$HOME"
  "/tmp"
)
HELP="You can install ClamAV using Homebrew with:\n\n  brew install clamav\n\nMake sure you have Homebrew installed first: https://brew.sh/"

set -euo pipefail

command -v freshclam >/dev/null 2>&1 || { echo -e "freshclam is not installed or not in \$PATH.\n$HELP" >&2; exit 1; }
command -v clamdscan >/dev/null 2>&1 || { echo -e "clamdscan is not installed or not in \$PATH.\n$HELP" >&2; exit 1; }

# Using XDG spec logging directory
mkdir -p "$LOG_DIR"

# Update the virus descriptions database
freshclam


echo "Starting virus scan..."
clamdscan --fdpass --multiscan --log="$LOG_DIR/scan.log" "${SCAN_PATHS[@]}" &
scan_pid=$!
spinner="/|\\-/|\\-"
i=0
while kill -0 "$scan_pid" 2>/dev/null; do
  i=$(( (i+1) %8 ))
  printf "\rScanning... %c" "${spinner:$i:1}"
  sleep 5
done
wait "$scan_pid"
echo -e "\rScan complete. Log saved to: $LOG_DIR/scan.log"
