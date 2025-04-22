# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
HTML preview utilities for the Document Accessibility Streamlit application.
"""

import os
import base64
import mimetypes
import streamlit as st
from bs4 import BeautifulSoup


def display_html_content(html_path: str) -> None:
    """
    Display HTML content in the Streamlit app with embedded resources.
    
    Args:
        html_path: Path to the HTML file
    """
    try:
        if not os.path.exists(html_path):
            st.warning(f"HTML file not found: {html_path}")
            return
            
        with open(html_path, "r", encoding="utf-8", errors="replace") as f:
            html_content = f.read()

        # Parse the HTML content
        soup = BeautifulSoup(html_content, "html.parser")
        html_dir = os.path.dirname(html_path)

        # Find all elements with src attributes (img, video, audio, etc.)
        for element in soup.find_all(lambda tag: tag.has_attr("src")):
            src = element.get("src", "")

            # Check if this is a relative path (not starting with http:// or https:// or data: or //)
            if not src.startswith(("http://", "https://", "data:", "//", "/")):
                # Handle both ./image.png and image.png formats
                if src.startswith("./"):
                    src = src[2:]  # Remove ./ prefix

                # Construct the full path to the file
                file_full_path = os.path.normpath(os.path.join(html_dir, src))

                if os.path.exists(file_full_path) and os.path.isfile(file_full_path):
                    # Check file size - skip files over 5MB to avoid huge base64 strings
                    if os.path.getsize(file_full_path) <= 5 * 1024 * 1024:  # 5MB limit
                        try:
                            # Get mime type
                            # Get mime type
                            mime_type = mimetypes.guess_type(file_full_path)[0] or 'application/octet-stream'
                            # Read and encode the file
                            with open(file_full_path, "rb", encoding=None) as img_file:
                                file_data = base64.b64encode(img_file.read()).decode()
                                element["src"] = f"data:{mime_type};base64,{file_data}"
                        except Exception as e:
                            st.warning(
                                f"Error processing file {os.path.basename(file_full_path)}: {str(e)}"
                            )

        # Get the modified HTML content
        html_content = str(soup)
        st.html(html_content)

        # Also provide the raw HTML in an expandable section
        with st.expander("View HTML Code"):
            st.code(html_content, language="html")

    except Exception as e:
        st.error(f"Error displaying HTML file: {str(e)}")

def display_html_with_pagination(html_dir: str) -> None:
    """
    Display HTML content with pagination for multi-page documents.
    
    Args:
        html_dir: Directory containing HTML files
    """
    import re
    
    if not os.path.exists(html_dir):
        st.warning(f"HTML directory not found: {html_dir}")
        return
        
    if os.path.isfile(html_dir):
        # Single file
        display_html_content(html_dir)
        return
        
    # Find all HTML files in the directory
    html_files = [
        f for f in os.listdir(html_dir)
        if f.lower().endswith(".html") and os.path.isfile(os.path.join(html_dir, f))
    ]

    if not html_files:
        st.warning(f"No HTML files found in {html_dir}")
        return
        
    # Sort HTML files (try to extract page numbers for proper ordering)
    sorted_html_files = []
    for html_file in html_files:
        match = re.search(r"page[-_]?(\d+)\.html$", html_file.lower())
        if match:
            page_num = int(match.group(1))
            sorted_html_files.append((page_num, html_file))
        else:
            sorted_html_files.append((999, html_file))

    sorted_html_files.sort()
    sorted_display_files = [html_file for _, html_file in sorted_html_files]

    if len(sorted_display_files) == 1 and sorted_display_files[0] == "document.html":
        # If there's only one file called document.html, use it directly
        display_html_content(os.path.join(html_dir, "document.html"))
    else:
        # Display file selection
        st.markdown("### Select HTML Page to Preview")
        # Show the dropdown for selection
        selected_file = st.selectbox(
            "Available HTML pages:",
            sorted_display_files,
            format_func=lambda x: f"Page {re.search(r'(\d+)', x).group(1) if re.search(r'(\d+)', x) else 'Unknown'}: {x}",
        )
        st.divider()

        # Display the selected file
        file_path = os.path.join(html_dir, selected_file)
        display_html_content(file_path)
