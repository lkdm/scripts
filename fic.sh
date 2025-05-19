#!/usr/bin/env bash

# Set the output directory and file
DIR=~/Repos/lkdm/fiction-notes/jrnl
FILE="$DIR/$(date +%Y-%m-%d).md"

mkdir -p "$DIR"

echo "Journal entry mode. Type your text. Type ':q' to quit."

# Hide cursor for a cleaner look
tput civis

trap "tput cnorm; echo; exit" INT

while true; do
    # Prompt for input on the same line
    read -e -p "> " INPUT
    # Move cursor up and clear the line (remove previous input)
    tput cuu1
    tput el

    if [[ "$INPUT" == ":q" ]]; then
        tput cnorm
        echo "Exiting journal mode."
        break
    fi
    echo "$INPUT" >> "$FILE"
done

# Restore cursor visibility
tput cnorm
