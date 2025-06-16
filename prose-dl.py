#!/usr/bin/env -S uv --quiet run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
# "bs4",
# "requests"
# ]
# ///
import requests
from bs4 import BeautifulSoup
import sys

url = sys.argv[1]
output_file = "output.tsv"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, 'html.parser')

with open(output_file, "a", encoding="utf-8") as f:
    for quote in soup.select(".quote"):
        # Safely extract quote text
        quote_text_elem = quote.select_one(".quoteText")
        quote_text = quote_text_elem.get_text(strip=True) if quote_text_elem else ""

        # Extract author and title (simplified, may need adjustment)
        author_or_title = quote.select(".authorOrTitle")
        author = author_or_title[0].get_text(strip=True) if len(author_or_title) > 0 else ""
        title = author_or_title[1].get_text(strip=True) if len(author_or_title) > 1 else ""

        # Clean quote text (remove extra whitespace, quotes, etc.)

        start = quote_text.find("“")
        end = quote_text.find("”", start + 1)  # Start searching after the first quote

        if start != -1 and end != -1:
            quote_text = quote_text[start + 1:end].strip()
        else:
            # No quotes found, use the whole text (or set to empty if you prefer)
            quote_text = quote_text.strip()
            # Turn linebreaks into \n characters            
            quote_text = quote_text.replace('\r', '').replace('\n', '\\n')

        f.write(f"{author.replace(",", "").strip()}\t{title.strip()}\t{quote_text.strip()}\n")
