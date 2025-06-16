#!/usr/bin/env bash

# Pick a random line from the TSV, including its line number
# The output will be: line_number<tab>author<tab>title<tab>quote
selected=$(awk '{print NR "\t" $0}' ~/.prose.tsv | shuf -n 1)

line_number=$(echo "$selected" | cut -f1)
author=$(echo "$selected" | cut -f2)
title=$(echo "$selected" | cut -f3)
quote=$(echo "$selected" | cut -f4)

# Replace literal '\n' with actual newlines
quote=$(echo -e "$quote")

# Output with borders and strict 79-column wrapping (including indentation)
border="======================================================================="
echo "$border"
echo "“$quote”" | fold -s -w64 | sed 's/^/    /'
echo ""

if [ -z "$title" ]; then
    attribution_line="— by $author [:$line_number]"
else
    attribution_line="— from *$title* by $author [:$line_number]"
fi

echo "$attribution_line" | fold -s -w64 | sed 's/^/    /'
echo "$border"

