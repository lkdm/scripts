#!/usr/bin/env bash

# Set variables
REPO=~/Repos/lkdm/fiction-notes
DIR=~/Repos/lkdm/fiction-notes/jrnl
FILE="$DIR/$(date +%Y-%m-%d).md"

# Pull latest changes from origin
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
    read -e -p "> " INPUT
    tput cuu1
    tput el
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
