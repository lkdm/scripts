#!/usr/bin/env -S uv --quiet run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
# ]
# ///

import sys
import re
import zipfile
from pathlib import Path


def print_help():
    help_text = """
facility agreement template cleaner 
===================================

Fixes common problems that occur while templating facility agreement documents.

Usage:
    script.py <input.docx> [output.docx]

Arguments:
    <input.docx>     Path to the input Word document.
    [output.docx]    Optional path for the processed output file.
                     If not provided, a new file will be created alongside
                     the input with '_processed' appended to the name.

Options:
    -h, --help       Show this help message and exit.

Example:
    script mydoc.docx mydoc_processed.docx
"""
    print(help_text)

def sanitize_template_tags(xml_content: str) -> str:
    """
    Sanitizes template tags in the xml content by stripping out any run/formatting XML
    inside the template tags (|TemplateName|).
    """
    # Define a regex to match the template tag blocks: everything between | |
    tag_pattern = r'(\|[^|]+\|)'
    
    def clean_inner_text(text: str) -> str:
        """
        This function strips out any tags inside a template block, leaving only the plain text.
        """
        # Remove any XML tags (e.g., <w:r>, <w:t>, etc.)
        text = re.sub(r'<[^>]+>', '', text)
        return text

    # This function will process each match and clean the inner content
    def replace_template_tag(match):
        tag = match.group(0)
        cleaned = clean_inner_text(tag)
        return cleaned

    # Apply the regex to replace the content inside the | | with cleaned text
    sanitized_xml = re.sub(tag_pattern, replace_template_tag, xml_content)
    return sanitized_xml

def process_docx_file(input_path: Path, output_path: Path):
    """
    Processes the docx file, sanitizing template tags and saving the result to a new file.
    """
    # Open the DOCX file (zip file)
    with zipfile.ZipFile(input_path, 'r') as docx:
        # Extract the XML document
        xml_content = docx.read('word/document.xml').decode('utf-8')
        
        # Sanitize the XML content (process template tags)
        sanitized_xml = sanitize_template_tags(xml_content)
        
        # Write the sanitized XML back to a new document
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as new_docx:
            # Write the sanitized document.xml back to the DOCX
            new_docx.writestr('word/document.xml', sanitized_xml)
            
            # Copy over all other original files in the DOCX except for document.xml
            for file in docx.namelist():
                if file != 'word/document.xml':
                    new_docx.writestr(file, docx.read(file))

    print(f"✅ Processed saved to {output_path}")

# === ENTRY POINT ===
if __name__ == "__main__":
    if "-h" in sys.argv or "--help" in sys.argv:
        print_help()
        sys.exit(0)

    if len(sys.argv) < 2:
        print("❌ Usage: script.py <input.docx> [output.docx]")
        sys.exit(1)

    input_file = Path(sys.argv[1])
    if not input_file.exists():
        print(f"❌ Input file not found: {input_file}")
        sys.exit(1)

    if len(sys.argv) >= 3:
        output_file = Path(sys.argv[2])
    else:
        output_file = input_file.with_name(input_file.stem + "_processed.docx")

    process_docx_file(input_file, output_file)
