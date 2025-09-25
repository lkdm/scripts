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

# === CONFIGURATION ===
HIGHLIGHT_STYLE = "HighlightYellow" # Yellow highlight
VARIABLE_REGEX = re.compile(r"\|[^|]+\|")  # matches |VariableName|

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

def flatten_text_within_variable(parent):
    """Flattens text within |Variable| markers by removing internal tags."""
    if parent.text:
        # Search for all |Variable| matches in plain text
        text = parent.text
        new_content = []
        last_index = 0
        for match in VARIABLE_REGEX.finditer(text):
            start, end = match.span()
            # Add text before variable
            if start > last_index:
                new_content.append(text[last_index:start])
            # Create span for variable
            span = etree.Element("{urn:oasis:names:tc:opendocument:xmlns:text:1.0}span", {
                '{urn:oasis:names:tc:opendocument:xmlns:text:1.0}style-name': HIGHLIGHT_STYLE
            })
            span.text = match.group()
            new_content.append(span)
            last_index = end
        # Add remaining text
        if last_index < len(text):
            new_content.append(text[last_index:])

        # Clear original paragraph
        parent.text = None
        parent[:] = []

        # Append new content
        for item in new_content:
            if isinstance(item, str):
                if parent.text is None:
                    parent.text = item
                else:
                    # Create a dummy span to carry leftover text
                    tail_span = etree.Element("{urn:oasis:names:tc:opendocument:xmlns:text:1.0}span")
                    tail_span.text = item
                    parent.append(tail_span)
            else:
                parent.append(item)

    else:
        # Handle nested spans that may split a variable
        text_buffer = ""
        spans_to_remove = []
        for child in list(parent):
            if child.tag.endswith("span"):
                if child.text:
                    text_buffer += child.text
                    spans_to_remove.append(child)
        if "|" in text_buffer:
            matches = VARIABLE_REGEX.findall(text_buffer)
            for span in spans_to_remove:
                parent.remove(span)
            for match in matches:
                new_span = etree.Element("{urn:oasis:names:tc:opendocument:xmlns:text:1.0}span", {
                    '{urn:oasis:names:tc:opendocument:xmlns:text:1.0}style-name': HIGHLIGHT_STYLE
                })
                new_span.text = match
                parent.append(new_span)

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
        f"{{{fo_ns}}}background-color": "#ffff00"
    })
    style_element.append(text_props)

    # Append to automatic styles
    auto_styles.append(style_element)

# === ENTRY POINT ===
if __name__ == "__main__":
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
