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
from dataclasses import dataclass

def print_help():
    help_text = """
facility agreement template cleaner 
===================================

Fixes common problems that occur while templating facility agreement documents.

Usage:
    script.py <input.docx> [output.docx] [--checkboxes] [--templates]

Arguments:
    <input.docx>    Path to the input Word document.
    [output.docx]   Optional path for the processed output file.
                    If not provided, a new file will be created alongside
                    the input with '_processed' appended to the name.

Options:
    -h, --help      Show this help message and exit.
    --checkboxes    Remove locked checkboxes and replace them with `☑`.
    --templates     Sanitise template tags (|TemplateName|) by removing inner formatting.
    --all           Enable all features

Example:
    script mydoc.docx mydoc_processed.docx --checkboxes --templates
"""
    print(help_text)

@dataclass
class Opts:
    remove_locked_checkboxes: bool = False
    sanitise_template_tags: bool = False

def sanitise_template_tags(xml_content: str) -> str:
    """
    sanitises template tags in the xml content by stripping out any run/formatting XML
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
    sanitised_xml = re.sub(tag_pattern, replace_template_tag, xml_content)
    return sanitised_xml

def remove_locked_checkboxes(xml_content: str) -> str:
    """
    Removes locked checkboxes, replacing them with the unicode character `☑`.
    The replacement is wrapped in a <w:t> tag.
    
    Matches blocks starting with <w:sdt>, ending with </w:sdt>, containing <w14:checkbox> within them.
    """
    # Define a regex to match a <w:sdt> block containing <w14:checkbox> inside it
    sdt_pattern = r'(<w:sdt>.*?<w14:checkbox.*?>.*?</w:sdt>)'

    def replace_checkbox_block(match):
        """
        Replaces the matched block with the text `☑` wrapped inside <w:t> tags.
        """
        # Return the replacement text wrapped in <w:t>
        checkbox_replacement = """
        <w:r>
            <w:rPr>
                <w:rFonts w:cs="Arial"/>
                <w:sz w:val="20"/>
                <w:szCs w:val="20"/>
            </w:rPr>
            <w:t>☑</w:t>
        </w:r>
        """
        return checkbox_replacement.strip()

    # Apply the regex and replace matching blocks
    sanitised_xml = re.sub(sdt_pattern, replace_checkbox_block, xml_content, flags=re.DOTALL)

    return sanitised_xml


def process_docx_file(input_path: Path, output_path: Path, opts: Opts):
    """
    Processes the docx file, sanitizing template tags and saving the result to a new file.
    """
    # Open the DOCX file (zip file)
    with zipfile.ZipFile(input_path, 'r') as docx:
        # Extract the XML document
        xml_content = docx.read('word/document.xml').decode('utf-8')

        if opts.remove_locked_checkboxes:
            xml_content = remove_locked_checkboxes(xml_content)
        
        # sanitise the XML content (process template tags)
        if opts.sanitise_template_tags:
            xml_content = sanitise_template_tags(xml_content)
        
        # Write the sanitised XML back to a new document
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as new_docx:
            # Write the sanitised document.xml back to the DOCX
            new_docx.writestr('word/document.xml', xml_content)
            
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
        print("❌ Usage: script.py <input.docx> [output.docx] [--checkboxes] [--templates]")
        sys.exit(1)

    # Process the arguments and differentiate between options and files
    input_file = None
    output_file = None
    options = []

    for arg in sys.argv[1:]:
        if arg.startswith('--'):  # If it's an option, add to the options list
            options.append(arg)
        elif not input_file:  # First non-option argument is the input file
            input_file = Path(arg)
        elif not output_file:  # Second non-option argument is the output file
            output_file = Path(arg)

    if not input_file or not input_file.exists():
        print(f"❌ Input file not found: {input_file}")
        sys.exit(1)

    if not output_file:
        # Default output file is input file with "_processed" suffix
        output_file = input_file.with_name(input_file.stem + "_processed.docx")

    # Parse options
    all = "--all" in options
    opts = Opts(
        remove_locked_checkboxes="--checkboxes" in options or all,
        sanitise_template_tags="--templates" in options or all
    )

    # Check if all options are False and loop through the properties
    inactive_opts = [key for key, value in opts.__dict__.items() if not value]
    
    if len(inactive_opts) == len(opts.__dict__):  # If all options are inactive
        print("⚠️ No operation performed: No options were enabled (no-op). Use '--checkboxes', '--templates' or '--all'.")
    else:
        # If any option is enabled, proceed with processing
        process_docx_file(input_file, output_file, opts)
