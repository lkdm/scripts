#!/usr/bin/env bash

# Set variables
REPO=~/Repos/lkdm/fiction-notes
DIR=~/Repos/lkdm/fiction-notes/jrnl
FILE="$DIR/$(date +%Y-%m-%d).md"

WORDCOUNT_MODE=0

# Help message
show_help() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

A simple journaling script that appends your input to a dated markdown file and syncs it with git.

Options:
  -w         Show word count in the prompt and clear the screen for each entry.
  -h, --help Show this help message and exit.

Examples:
  $(basename "$0")        # Normal journaling mode
  $(basename "$0") -w     # Word count mode (shows word count in prompt)
EOF
}

# Argument parsing
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    show_help
    exit 0
elif [[ "$1" == "-w" ]]; then
    WORDCOUNT_MODE=1
fi

cd "$REPO" || { echo "Repo directory not found!"; exit 1; }
git pull origin
if [ $? -ne 0 ]; then
    echo -e "\033[31mWarning: git pull failed.\033[0m"
    read -r -p "Continue anyway? [Y/n] " answer
    answer=${answer:-Y}
    if [[ ! "$answer" =~ ^[Yy]$ ]]; then
        echo "Exiting."
        exit 1
    fi
fi

mkdir -p "$DIR"

echo "Journal entry mode. Type your text. Type ':q' to quit."

tput civis
trap "tput cnorm; echo; exit" INT

while true; do
    if [[ "$WORDCOUNT_MODE" -eq 1 ]]; then
        clear
        WORDCOUNT=$(wc -w < "$FILE" 2>/dev/null)
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
    echo "$INPUT" >> "$FILE"
done

tput cnorm

cd "$REPO" || exit 1
git add "$FILE"
git commit -m "Journal update for $(date +%Y-%m-%d)"
git push origin

echo "Journal saved and pushed to origin."
