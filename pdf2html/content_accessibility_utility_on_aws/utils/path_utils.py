# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Path Utility Functions.

This module provides functions for handling file paths in the document accessibility tools.
"""

import os
import re
from typing import List, Optional, Tuple, Dict, Any

from content_accessibility_utility_on_aws.utils.logging_helper import setup_logger

# Set up module-level logger
logger = setup_logger(__name__)


def ensure_directory(path: str) -> str:
    """
    Ensure that a directory exists, creating it if necessary.

    Args:
        path: Directory path to ensure exists

    Returns:
        The path of the created/existing directory
    """
    # Skip empty paths
    if not path:
        return path

    # If path is a file path, get the directory part
    if os.path.splitext(os.path.basename(path))[1]:
        directory = os.path.dirname(path)
    else:
        directory = path

    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
        logger.debug(f"Created directory: {directory}")

    return directory


def resolve_html_path(
    path: str, options: Optional[Dict[str, Any]] = None
) -> Tuple[str, bool, bool]:
    """
    Resolve an HTML path to determine if it's a single file or directory.

    Args:
        path: Path to the HTML file or directory
        options: Optional options dictionary with 'single_page' and/or 'multi_page' flags

    Returns:
        Tuple containing:
            - The resolved path (potentially modifying for extracted_html subdirectory)
            - Boolean flag indicating single page mode
            - Boolean flag indicating multi-page mode
    """
    is_single_page = False
    is_multi_page = False

    # Check explicit mode flags in options
    if options:
        is_single_page = options.get("single_page", False)
        is_multi_page = options.get("multi_page", False)

    # Auto-detect if not specified by flags
    if not is_single_page and not is_multi_page:
        is_single_page = os.path.isfile(path)
        is_multi_page = os.path.isdir(path)

        # Determine mode based on what we found
        if is_single_page:
            logger.debug(f"Auto-detected single page mode for file: {path}")
        elif is_multi_page:
            logger.debug(f"Auto-detected multi-page mode for directory: {path}")

            # Check for extracted_html subdirectory when in multi-page mode
            extracted_html_dir = os.path.join(path, "extracted_html")
            if os.path.isdir(extracted_html_dir):
                logger.debug(f"Found extracted_html subdirectory: {extracted_html_dir}")
                path = extracted_html_dir
        else:
            logger.error(f"Path is neither a file nor a directory: {path}")

    return path, is_single_page, is_multi_page


def find_html_files(directory: str) -> List[str]:
    """
    Find all HTML files in a directory.

    Args:
        directory: Directory to search for HTML files

    Returns:
        List of HTML file paths
    """
    html_files = []
    if not os.path.isdir(directory):
        logger.warning(f"Not a directory: {directory}")
        return html_files

    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(".html"):
                html_files.append(os.path.join(root, file))

    # Sort HTML files (important for page order)
    html_files.sort()
    logger.debug(f"Found {len(html_files)} HTML files in directory")
    return html_files


def sort_html_files_by_page(html_files: List[str]) -> List[str]:
    """
    Sort HTML files by their page number (extracted from filename).

    Args:
        html_files: List of HTML file paths

    Returns:
        Sorted list of HTML file paths
    """
    # Create a list of tuples with (page_number, file_path)
    sorted_files = []
    for html_file in html_files:
        filename = os.path.basename(html_file)

        # Try to extract page number from filename using various patterns
        match = re.search(r"page[_-]?(\d+)\.html$", filename, re.IGNORECASE)
        if match:
            try:
                page_num = int(match.group(1))
                sorted_files.append((page_num, html_file))
            except ValueError:
                # If we can't convert to int, just add it to the end
                sorted_files.append((999, html_file))
        else:
            # Non-page files go at the end
            sorted_files.append((999, html_file))

    # Sort by page number and extract just the file paths
    sorted_files.sort()
    return [f for _, f in sorted_files]


def match_issues_to_file(
    issues: List[Dict[str, Any]],
    html_file: str,
    html_files: Optional[List[str]] = None,
    base_dir: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Match accessibility issues to a specific HTML file.

    Args:
        issues: List of accessibility issues
        html_file: Path to the HTML file to match issues against
        html_files: Optional list of all HTML files (to determine if this is the first file)
        base_dir: Optional base directory for resolving relative paths

    Returns:
        List of issues that match this HTML file
    """
    file_issues = []

    # Process each issue to see if it belongs to this file
    for issue in issues:
        if issue.get("remediation_status") != "needs_remediation":
            continue

        # Try multiple places where the path might be stored
        issue_path = issue.get("file_path", "")
        if not issue_path and "location" in issue and issue["location"]:
            issue_path = issue["location"].get("file_path", "")

        # If no file path in issue, try to match by page number
        if not issue_path and "location" in issue and issue["location"]:
            page_num = issue["location"].get("page_number")
            if page_num is not None:
                # Try to extract page number from filename
                match = re.search(
                    r"page[_-]?(\d+)\.html$", os.path.basename(html_file), re.IGNORECASE
                )
                if match and int(match.group(1)) == page_num:
                    # Match by page number
                    file_issues.append(issue)
                    continue

        # If there is a file path, try different matching approaches
        if issue_path:
            if (
                issue_path == html_file
                or os.path.basename(issue_path) == os.path.basename(html_file)
                or os.path.abspath(issue_path) == os.path.abspath(html_file)
            ):
                file_issues.append(issue)
                continue

        # If no file_path found and this is the first HTML file,
        # assign all issues with no file path to it
        if not issue_path and html_files and html_file == html_files[0]:
            file_issues.append(issue)

    logger.debug(
        f"Matched {len(file_issues)} issues to file: {os.path.basename(html_file)}"
    )
    return file_issues
def zip_output_files(output_files, zip_filename):
    """
    Zip specific output files and folders into a single zip file.

    Args:
        output_files: List of file and folder paths to include in the zip
        zip_filename: Name of the zip file to create

    Returns:
        Path to the created zip file

    Raises:
        FileNotFoundError: If any of the files don't exist
        IOError: If there's an error creating the zip file
    """
    import zipfile
    import os
    
    logger.info(f"Creating zip archive {zip_filename} with {len(output_files)} files/folders")
    
    try:
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Process each file or folder
            for file_path in output_files:
                if not os.path.exists(file_path):
                    logger.warning(f"File not found, skipping: {file_path}")
                    continue
                    
                if os.path.isfile(file_path):
                    # Add file directly with its basename
                    zipf.write(file_path, os.path.basename(file_path))
                    logger.debug(f"Added file to zip: {file_path}")
                elif os.path.isdir(file_path):
                    # For directories, add all files while preserving the directory structure
                    dir_name = os.path.basename(file_path)
                    for root, _, files in os.walk(file_path):
                        for file in files:
                            file_full_path = os.path.join(root, file)
                            # Calculate relative path within the directory
                            rel_path = os.path.join(dir_name, os.path.relpath(file_full_path, file_path))
                            zipf.write(file_full_path, rel_path)
                            logger.debug(f"Added to zip: {rel_path}")
        
        logger.info(f"Successfully created zip archive: {zip_filename}")
        return zip_filename
    except Exception as e:
        logger.error(f"Error creating zip archive: {e}")
        raise IOError(f"Failed to create zip archive: {e}")
