#!/usr/bin/env -S uv --quiet run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "lxml",
# ]
# ///

from lxml.etree import Element, SubElement, XMLParser, parse, ElementTree
import lxml.etree as etree
import sys
import re
from pathlib import Path

# Steps
# 1. Every odd | is the start of a variable, and every even | is the end of the variable name.
#   a. This means the entire |VariableName| should be in one tag, not split.
#   c. So first step, is ensure no tags are within odd | and even |.
# 2. All locked/protected inputs should be unlocked (DONE: See remove_loext_content_controls)
# 3. |VariableName| should be wrapped in left align, not justify (not done, make separate function, to call from inject_highlight_style)
# 4. All |VariableName| should be 10pt and highlighted yellow (so I can visually confirm that it worked) (DONE: See inject_highlight_style)
# Biggest problem currently is that flatten_text_within_variable does not work correctly



# === CONFIGURATION ===
HIGHLIGHT_STYLE = "HighlightYellow" # Yellow highlight
VARIABLE_REGEX = re.compile(r"\|[^|]+\|")  # matches |VariableName|


def print_help():
    help_text = """
tfac - templated facility agreement cleaner
===========================================

Fixes common problems that occur while templating facility agreement documents.

Usage:
    script.py <input.fodt> [output.fodt]

Arguments:
    <input.fodt>     Path to the input Flat ODF Text document.
    [output.fodt]    Optional path for the processed output file.
                     If not provided, a new file will be created alongside
                     the input with '_processed' appended to the name.

Options:
    -h, --help       Show this help message and exit.

Steps:
    1. Convert Facilty Agreement in .docx format to .fodt
    2. Insert templated variables surrounded by pipes (example: `|TemplateVariables|`)
    3. Run this script on the templated fodt.
    4. Check output, and convert back to docx for upload to TriOnline

Features:
    • Removes LibreOffice-specific write protection tags (<loext:content-control>).
    • Ensures variables like |VariableName| are kept in a single <text:span>.
    • Applies a 'HighlightYellow' style (yellow background, 10pt font).
    • Preserves all paragraph-level attributes and structure outside variables.

Example:
    script.py mydoc.fodt mydoc_processed.fodt
"""
    print(help_text)

# === FUNCTIONS ===

LOEXT_NS = "urn:org:documentfoundation:names:experimental:office:xmlns:loext:1.0"
def remove_loext_content_controls(root: etree._Element):
    """
    Removes write protection from section of the document
    """
    content_controls = root.findall(".//{%s}content-control" % LOEXT_NS)
    for control in content_controls:
        parent = control.getparent()
        if parent is not None:
            index = parent.index(control)
            # Insert all children in place of the content-control
            for child in reversed(control):
                parent.insert(index, child)
            # Remove the original loext:content-control tag
            parent.remove(control)

def flatten_text_within_variable(paragraph):
    """
    Finds and flattens |VariableName| markers inside a paragraph (<text:p>).
    Each variable is wrapped in a dedicated <text:span> with the highlight style.
    Preserves the paragraph’s attributes, but strips conflicting nested runs.
    """
    text_ns = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"

    # Extract all paragraph text (including nested spans/bookmarks/tails)
    def get_full_text(elem):
        parts = []
        if elem.text:
            parts.append(elem.text)
        for child in elem:
            parts.append(get_full_text(child))
            if child.tail:
                parts.append(child.tail)
        return "".join(parts)

    full_text = get_full_text(paragraph)
    matches = list(VARIABLE_REGEX.finditer(full_text))
    if not matches:
        return

    # Prepare rebuilt children
    new_children = []
    cursor = 0
    for match in matches:
        start, end = match.span()
        # Add plain text before variable
        if start > cursor:
            pre = full_text[cursor:start]
            if pre:
                new_children.append(pre)

        # Add variable span
        span = etree.Element(f"{{{text_ns}}}span", {
            f"{{{text_ns}}}style-name": HIGHLIGHT_STYLE
        })
        span.text = match.group()
        new_children.append(span)

        cursor = end

    # Add trailing text
    if cursor < len(full_text):
        new_children.append(full_text[cursor:])

    # Remove old children but keep paragraph attributes
    for child in list(paragraph):
        paragraph.remove(child)

    # Reattach content
    paragraph.text = None
    first = True
    for node in new_children:
        if isinstance(node, str):
            if first:
                paragraph.text = node
                first = False
            else:
                # Wrap extra text in a simple span so it isn’t lost
                span = etree.Element(f"{{{text_ns}}}span")
                span.text = node
                paragraph.append(span)
        else:
            paragraph.append(node)
            first = False


def process_fodt(input_path: Path, output_path: Path):
    parser = etree.XMLParser(ns_clean=True, recover=True)
    tree = etree.parse(str(input_path), parser)
    root = tree.getroot()

    remove_loext_content_controls(root)

    text_ns = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
    text_elements = root.findall(".//{%s}p" % text_ns)

    for para in text_elements:
        flatten_text_within_variable(para)

    inject_highlight_style(root)

    tree.write(str(output_path), encoding="utf-8", xml_declaration=True, pretty_print=True)
    print(f"✅ Processed saved to {output_path}")


def inject_highlight_style(root):
    nsmap = root.nsmap
    office_ns = nsmap.get('office', 'urn:oasis:names:tc:opendocument:xmlns:office:1.0')
    style_ns = nsmap.get('style', 'urn:oasis:names:tc:opendocument:xmlns:style:1.0')
    fo_ns = nsmap.get('fo', 'urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0')

    # Find automatic styles
    auto_styles = root.find(f".//{{{office_ns}}}automatic-styles")
    if auto_styles is None:
        # Create it if missing
        auto_styles = etree.Element(f"{{{office_ns}}}automatic-styles")
        # Insert it at the top (after root)
        root.insert(0, auto_styles)

    # Check if HighlightYellow style already exists
    for style in auto_styles.findall(f"{{{style_ns}}}style"):
        if style.get(f"{{{style_ns}}}name") == HIGHLIGHT_STYLE:
            return  # Already present

    # Create style element
    style_element = etree.Element(f"{{{style_ns}}}style", {
        f"{{{style_ns}}}name": HIGHLIGHT_STYLE,
        f"{{{style_ns}}}family": "text"
    })
    text_props = etree.Element(f"{{{style_ns}}}text-properties", {
        f"{{{fo_ns}}}background-color": "#ffff00",
        f"{{{fo_ns}}}font-size": "10pt"
    })
    style_element.append(text_props)

    # Append to automatic styles
    auto_styles.append(style_element)

# === ENTRY POINT ===
if __name__ == "__main__":
    if "-h" in sys.argv or "--help" in sys.argv:
        print_help()
        sys.exit(0)

    if len(sys.argv) < 2:
        print("❌ Usage: script.py <input.fodt> [output.fodt]")
        sys.exit(1)

    input_file = Path(sys.argv[1])
    if not input_file.exists():
        print(f"❌ Input file not found: {input_file}")
        sys.exit(1)

    if len(sys.argv) >= 3:
        output_file = Path(sys.argv[2])
    else:
        output_file = input_file.with_name(input_file.stem + "_processed.fodt")

    process_fodt(input_file, output_file)
