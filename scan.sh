#!/usr/bin/env bash
# Scans home directory for viruses on POSIX systems

# Exit if running inside a Distrobox container
if [[ -n "$CONTAINER_ID" ]]; then
  echo "This script should not run inside a Distrobox container." >&2
  exit 1
fi

HELP="You can install ClamAV using Homebrew with:\n\n  brew install clamav\n\nMake sure you have Homebrew installed first: https://brew.sh/"

command -v freshclam >/dev/null 2>&1 || { echo -e "freshclam is not installed or not in \$PATH.\n$HELP" >&2; exit 1; }
command -v clamdscan >/dev/null 2>&1 || { echo -e "clamdscan is not installed or not in \$PATH.\n$HELP" >&2; exit 1; }

# Using XDG spec logging directory
LOG_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/clamav"
mkdir -p "$LOG_DIR"

# Update the virus descriptions database
freshclam

# Recursively scan directories that are writeable on Fedora Atomic distros
clamscan --recursive --log="$LOG_DIR/scan.log" /tmp /var/tmp ~ /var/home/linuxbrew
