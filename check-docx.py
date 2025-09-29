#!/usr/bin/env -S uv --quiet run --script
# /// script
# requires-python = "==3.13.7"
# dependencies = [
#     "python-docx===1.1.2",
# ]
# ///

from zipfile import ZipFile
import sys
import docx
from pathlib import Path

def check(path: Path):
    try:
        with ZipFile(path, 'r') as zipf:
            print("File is a valid ZIP.")
            # List files inside the ZIP to confirm structure
            print(zipf.namelist())
    except Exception as e:
        print(f"Error opening ZIP file: {e}")

def check_document(path: Path):
    try:
        # Open the document using python-docx
        document = docx.Document(path)
        print(f"✅ Successfully loaded document: {path}")
        # print("Document XML:", document.element.xml)
    except Exception as e:
        print(f"❌ Error loading document with python-docx: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ Usage: script.py <input.docx>")
        sys.exit(1)

    input_file = Path(sys.argv[1])

    if not input_file.exists():
        print(f"❌ Input file not found: {input_file}")
        sys.exit(1)

    print(f"🔍 Checking the ZIP structure of the file: {input_file}")
    check(input_file)  # Check ZIP integrity
    
    print(f"\n🔍 Checking the document integrity with python-docx: {input_file}")
    check_document(input_file)  # Try loading with python-docx
