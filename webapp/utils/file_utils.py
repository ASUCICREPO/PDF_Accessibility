# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
File handling utilities for the Document Accessibility Streamlit application.
"""

import os
import zipfile
import shutil
from typing import List, Tuple


def save_uploaded_file(uploaded_file, destination_dir: str) -> str:
    """
    Save an uploaded file to the specified directory.

    Args:
        uploaded_file: Streamlit uploaded file object
        destination_dir: Directory path to save the file

    Returns:
        Path to the saved file
    """
    file_path = os.path.join(destination_dir, uploaded_file.name)
    with open(file_path, "wb", encoding=None) as f:
        f.write(uploaded_file.getbuffer())
    return file_path


def detect_file_type(file_name: str) -> str:
    """
    Detect the type of file based on its extension.

    Args:
        file_name: Name of the file

    Returns:
        File type ('pdf', 'html', 'zip', or None)
    """
    file_name = file_name.lower()

    if file_name.endswith(".pdf"):
        return "pdf"
    elif file_name.endswith(".html"):
        return "html"
    elif file_name.endswith(".zip"):
        return "zip"
    else:
        return None


def extract_zip_file(zip_path: str, extract_dir: str) -> List[str]:
    """
    Extract a ZIP archive and return a list of HTML files found.

    Args:
        zip_path: Path to the ZIP file
        extract_dir: Directory to extract files to

    Returns:
        List of paths to HTML files found in the archive
    """
    os.makedirs(extract_dir, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        for file_info in zip_ref.infolist():
            file_path = os.path.join(extract_dir, file_info.filename)
            if os.path.abspath(file_path).startswith(os.path.abspath(extract_dir)):
                zip_ref.extract(file_info, extract_dir)

    # Find all HTML files in the extracted directory
    html_files = []
    for root, _, files in os.walk(extract_dir):
        for file in files:
            if file.lower().endswith(".html"):
                html_files.append(os.path.join(root, file))

    # Sort HTML files to process in a consistent order
    html_files.sort()

    return html_files


def create_zip_archive(source_dir: str, zip_path: str) -> str:
    """
    Create a ZIP archive from the contents of a directory.

    Args:
        source_dir: Directory containing files to archive
        zip_path: Path where the ZIP file should be saved

    Returns:
        Path to the created ZIP file
    """
    base_path = os.path.splitext(zip_path)[0]
    zip_file_path = shutil.make_archive(base_path, "zip", source_dir)
    return zip_file_path


def find_html_files_in_directory(directory: str) -> List[Tuple[int, str]]:
    """
    Find HTML files in a directory and sort them by page number if possible.

    Args:
        directory: Directory to search for HTML files

    Returns:
        List of tuples with (page_number, file_path)
    """
    import re

    if not os.path.exists(directory) or not os.path.isdir(directory):
        return []

    html_files = [
        f
        for f in os.listdir(directory)
        if f.lower().endswith(".html") and os.path.isfile(os.path.join(directory, f))
    ]

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
    return sorted_html_files


def get_mime_type(file_path: str) -> str:
    """
    Get the MIME type for a file.

    Args:
        file_path: Path to the file

    Returns:
        MIME type string
    """
    import mimetypes

    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        # Default to common types based on extension
        ext = os.path.splitext(file_path)[1].lower()
        if ext in [".jpg", ".jpeg"]:
            mime_type = "image/jpeg"
        elif ext in [".png"]:
            mime_type = "image/png"
        elif ext in [".gif"]:
            mime_type = "image/gif"
        elif ext in [".svg"]:
            mime_type = "image/svg+xml"
        elif ext in [".html", ".htm"]:
            mime_type = "text/html"
        else:
            mime_type = "application/octet-stream"

    return mime_type
