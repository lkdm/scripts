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
    """
    Highlights |Variables| as flat spans without internal XML.
    Preserves all other structure (bookmarks, hyperlinks, spans) outside the |...| blocks.
    """
    from copy import deepcopy

    def collect_text_and_elements(elem, collected):
        """
        Recursively collects text with their corresponding elements.
        """
        if elem.text:
            collected.append((elem.text, elem))
        for child in elem:
            collect_text_and_elements(child, collected)
            if child.tail:
                collected.append((child.tail, elem))

    # Step 1: Flatten all text content with source elements
    collected = []
    if parent.text:
        collected.append((parent.text, parent))
    for child in parent:
        collect_text_and_elements(child, collected)
        if child.tail:
            collected.append((child.tail, parent))

    full_text = "".join(text for text, _ in collected)
    matches = list(VARIABLE_REGEX.finditer(full_text))
    if not matches:
        return  # No variables found

    # Step 2: Reconstruct content
    new_children = []
    cursor = 0
    var_index = 0

    def append_text_as_cloned_structure(start_idx, end_idx):
        """
        Appends text from start to end by walking `collected` pieces and preserving structure.
        Restores highlight (e.g. grey) if original text had a style-name attribute.
        """
        nonlocal cursor
        remaining = end_idx - start_idx
        offset = 0
        while remaining > 0 and cursor < len(collected):
            text, src_elem = collected[cursor]
            if offset + len(text) <= start_idx:
                offset += len(text)
                cursor += 1
                continue
            take_from = max(0, start_idx - offset)
            take_to = min(len(text), end_idx - offset)
            subtext = text[take_from:take_to]

            if subtext:
                if src_elem.tag.endswith("p"):
                    # Direct paragraph text
                    if new_children and isinstance(new_children[-1], str):
                        new_children[-1] += subtext
                    else:
                        new_children.append(subtext)
                else:
                    # Clone original element (e.g., span or bookmark-ref)
                    clone = deepcopy(src_elem)
                    clone.text = subtext
                    clone[:] = []  # Clear children

                    # 🟡 Special: if it's not a <text:span>, and has no style, wrap it in a styled span
                    style_name = clone.attrib.get("{urn:oasis:names:tc:opendocument:xmlns:text:1.0}style-name")
                    if clone.tag != "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}span" and not style_name:
                        # Wrap in span to re-apply style (e.g., grey highlight)
                        span_wrapper = etree.Element("{urn:oasis:names:tc:opendocument:xmlns:text:1.0}span", {
                            '{urn:oasis:names:tc:opendocument:xmlns:text:1.0}style-name': "T28"  # grey highlight style
                        })
                        span_wrapper.append(clone)
                        new_children.append(span_wrapper)
                    else:
                        new_children.append(clone)

            remaining -= (take_to - take_from)
            offset += len(text)
            cursor += 1
    current = 0
    for match in matches:
        start, end = match.span()
        # Append content before variable (preserve formatting)
        append_text_as_cloned_structure(current, start)

        # Insert clean span with just the variable text
        clean_span = etree.Element("{urn:oasis:names:tc:opendocument:xmlns:text:1.0}span", {
            '{urn:oasis:names:tc:opendocument:xmlns:text:1.0}style-name': HIGHLIGHT_STYLE
        })
        clean_span.text = match.group()
        new_children.append(clean_span)

        current = end

    # Append content after last match
    append_text_as_cloned_structure(current, len(full_text))

    # Step 3: Clear and rebuild paragraph
    parent.text = None
    parent.clear()
    for node in new_children:
        if isinstance(node, str):
            if parent.text:
                parent.text += node
            else:
                parent.text = node
        else:
            parent.append(node)

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
