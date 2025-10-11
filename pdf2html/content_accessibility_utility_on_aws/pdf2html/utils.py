# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Utility functions for PDF to HTML conversion.
"""

import re
from typing import List, Dict, Any, Optional

from content_accessibility_utility_on_aws.utils.logging_helper import (
    setup_logger,
    DocumentAccessibilityError,
)

# Set up module-level logger
logger = setup_logger(__name__)


def combine_html_pages(
    page_files: List[str],
    output_path: str,
    continuous: bool = True,
    doc_info: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Combine multiple HTML pages into a single document.

    Args:
        page_files: List of HTML file paths to combine.
        output_path: Path to save the combined document.
        continuous: Whether to use continuous scrolling.
        doc_info: Optional document metadata.

    Returns:
        Path to the combined document.
    """
    try:
        # Read content from each page
        pages_content = []
        for page_file in page_files:
            with open(page_file, "r", encoding="utf-8") as f:
                content = f.read()
                # Extract body content between <body> and </body>
                body_match = re.search(r"<body[^>]*>(.*?)</body>", content, re.DOTALL)
                if body_match:
                    pages_content.append(body_match.group(1).strip())
                else:
                    logger.warning(f"No body content found in {page_file}")
                    pages_content.append(content.strip())

        # Create the combined document
        html_content = [
            "<!DOCTYPE html>",
            f'<html lang="{doc_info.get("language", "en") if doc_info else "en"}">',
            "<head>",
            '<meta charset="utf-8"/>',
            '<meta content="width=device-width, initial-scale=1.0" name="viewport"/>',
            f'<title>{doc_info.get("title", "PDF Document") if doc_info else "PDF Document"}</title>',
            "<style>",
            "        body { font-family: Arial, sans-serif; line-height: 1.6; }",
            "        .page-break { page-break-after: always; margin-bottom: 30px; border-bottom: 1px dashed #ccc; }",
            "    </style>",
            "</head>",
            "<body>",
        ]

        # Add each page's content
        for i, content in enumerate(pages_content):
            html_content.append(f'<div class="page" id="page-{i+1}">')
            html_content.append(content)
            html_content.append("</div>")
            if continuous and i < len(pages_content) - 1:
                html_content.append('<div class="page-break"></div>')

        html_content.append("</body>")
        html_content.append("</html>")

        # Write the combined document
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(html_content))

        return output_path

    except Exception as e:
        logger.warning(f"Error combining HTML pages: {e}")
        raise DocumentAccessibilityError(f"Failed to combine HTML pages: {e}")
