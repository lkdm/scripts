#!/usr/bin/env bash
# Scans home directory for viruses on POSIX systems

set -euo pipefail

HELP="You can install ClamAV using Homebrew with:\n\n  brew install clamav\n\nMake sure you have Homebrew installed first: https://brew.sh/"

command -v freshclam >/dev/null 2>&1 || { echo -e "freshclam is not installed or not in \$PATH.\n$HELP" >&2; exit 1; }
command -v clamdscan >/dev/null 2>&1 || { echo -e "clamdscan is not installed or not in \$PATH.\n$HELP" >&2; exit 1; }

# Using XDG spec logging directory
LOG_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/clamav"
mkdir -p "$LOG_DIR"

# Update the virus descriptions database
freshclam

# Directories to scan
SCAN_PATHS=(
  "$HOME"
  "/tmp"
)

echo "Starting virus scan..."

# Run clamdscan on each directory individually (since it doesn't do recursion)
for path in "${SCAN_PATHS[@]}"; do
  find "$path" -type f -print0 | xargs -0 -r clamdscan --fdpass --multiscan --log="$LOG_DIR/scan.log"
done

echo "Scan complete. Log saved to: $LOG_DIR/scan.log"
