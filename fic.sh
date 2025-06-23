#!/usr/bin/env bash

WORDCOUNT_MODE=0

show_help() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

A simple journaling script that appends your input to a new jrnl entry.

Options:
  -w         Show word count in the prompt and clear the screen for each entry.
  -h, --help Show this help message and exit.

Examples:
  $(basename "$0")        # Normal journaling mode
  $(basename "$0") -w     # Word count mode (shows word count in prompt)
EOF
}

if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    show_help
    exit 0
elif [[ "$1" == "-w" ]]; then
    WORDCOUNT_MODE=1
fi

TMPFILE=$(mktemp)
trap 'rm -f "$TMPFILE"' EXIT

echo "Journal entry mode. Type your text. Type ':q' to quit."

tput civis
trap "tput cnorm; echo; exit" INT

while true; do
    if [[ "$WORDCOUNT_MODE" -eq 1 ]]; then
        clear
        WORDCOUNT=$(wc -w < "$TMPFILE" 2>/dev/null)
        WORDCOUNT=${WORDCOUNT:-0}
        tput cup $(($(tput lines)-1)) 0
        read -e -p "$WORDCOUNT > " INPUT
    else
        read -e -p "> " INPUT
        tput cuu1
        tput el
    fi

    if [[ "$INPUT" == ":q" ]]; then
        tput cnorm
        echo "Exiting journal mode."
        break
    fi
    echo "$INPUT" >> "$TMPFILE"
done

export JRNL="$HOME/Repos/lkdm/fic"
~/.config/jrnl/scripts/pull.sh || return 1
jrnl fic < "$TMPFILE"
~/.config/jrnl/scripts/commit.sh || return 1
~/.config/jrnl/scripts/push.sh &


rm -f "$TMPFILE"

