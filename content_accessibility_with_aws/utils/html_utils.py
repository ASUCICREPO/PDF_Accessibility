# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
HTML utility functions for document accessibility.
"""

import os
from typing import List
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


def combine_html_files(html_files: List[str], output_path: str) -> str:
    """
    Combine multiple HTML files into a single HTML file.

    Args:
        html_files: List of paths to HTML files to combine
        output_path: Path to save the combined HTML file

    Returns:
        Path to the combined HTML file
    """
    if not html_files:
        raise ValueError("No HTML files provided to combine")

    # Sort the HTML files by name to ensure correct order
    html_files.sort()

    # Get the first HTML file to use as a template
    with open(html_files[0], "r", encoding="utf-8") as f:
        first_page_content = f.read()

    # Parse the HTML
    combined_soup = BeautifulSoup(first_page_content, "html.parser")

    # Make sure we have a proper HTML structure
    if not combined_soup.html:
        combined_soup = BeautifulSoup(
            '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>Combined Document</title></head><body></body></html>',
            "html.parser",
        )

    # Update the title
    if combined_soup.title:
        combined_soup.title.string = "Combined Document"
    else:
        title_tag = combined_soup.new_tag("title")
        title_tag.string = "Combined Document"
        combined_soup.head.append(title_tag)

    # Make sure we have lang attribute
    if combined_soup.html and not combined_soup.html.get("lang"):
        combined_soup.html["lang"] = "en"

    # Get the body element
    body = combined_soup.body
    if not body:
        body = combined_soup.new_tag("body")
        combined_soup.html.append(body)

    # Clear the body content from the template
    body.clear()

    # Add a style tag for page breaks
    style_tag = combined_soup.new_tag("style")
    style_tag.string = """
        .page-break {
            page-break-after: always;
            margin-bottom: 30px;
            border-bottom: 1px dashed #ccc;
            padding-bottom: 30px;
        }
        .page-container {
            margin-bottom: 2em;
        }
        .page-title {
            margin-top: 1em;
            padding-top: 1em;
            border-top: 1px solid #eee;
            font-size: 1.5em;
            color: #333;
        }
    """
    combined_soup.head.append(style_tag)

    # Process each HTML file
    for i, html_file in enumerate(html_files):
        try:
            with open(html_file, "r", encoding="utf-8") as f:
                page_content = f.read()

            # Parse the HTML
            page_soup = BeautifulSoup(page_content, "html.parser")

            # Create a container for this page
            page_div = combined_soup.new_tag("div")
            page_div["class"] = "page-container"
            page_div["id"] = f"page-{i+1}"

            # Add a page title
            page_title = combined_soup.new_tag("h2")
            page_title["class"] = "page-title"
            page_title.string = f"Page {i+1}"
            page_div.append(page_title)

            # Extract all content from the body
            if page_soup.body:
                # Get all direct children of the body
                for element in page_soup.body.children:
                    # Skip empty elements and whitespace
                    if element.name is not None:
                        # Clone the element to avoid modifying the original
                        cloned = element.extract()
                        page_div.append(cloned)

            # Add the page to the combined document
            body.append(page_div)

            # Add a page break after each page except the last one
            if i < len(html_files) - 1:
                page_break = combined_soup.new_tag("div")
                page_break["class"] = "page-break"
                body.append(page_break)

            logger.debug(f"Added page {i+1} from {html_file}")

        except Exception as e:
            logger.error(f"Error processing HTML file {html_file}: {e}")

    # Write the combined HTML to the output file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(str(combined_soup))

    logger.info(
        f"Created combined HTML file with {len(html_files)} pages at {output_path}"
    )
    return output_path
