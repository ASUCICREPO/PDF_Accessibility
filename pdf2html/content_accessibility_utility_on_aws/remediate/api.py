# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
HTML Accessibility Remediation API.

This module provides functionality for remediating accessibility issues in HTML documents.
"""

from typing import Dict, List, Any, Optional
import os
import shutil
import re
from bs4 import BeautifulSoup

from content_accessibility_utility_on_aws.utils.logging_helper import (
    setup_logger,
    DocumentAccessibilityError,
)
from content_accessibility_utility_on_aws.utils.image_utils import (
    copy_images_to_output,
    find_image_directory,
)
from content_accessibility_utility_on_aws.remediate.remediation_manager import RemediationManager

# Set up module-level logger
logger = setup_logger(__name__)


def remediate_html_accessibility(
    html_path: str,
    audit_report: Optional[Dict[str, Any]] = None,
    options: Optional[Dict[str, Any]] = None,
    output_path: Optional[str] = None,
    image_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Remediate accessibility issues in an HTML document.

    Args:
        html_path: Path to the HTML file or directory of HTML files.
        audit_report: Optional audit report from audit_html_accessibility().
        options: Remediation options.
        output_path: Path to save the remediated HTML file or directory.
        image_dir: Directory containing images referenced in the HTML.

    Returns:
        Dictionary containing remediation results.
    """
    try:
        # Set default options
        default_options = {
            "auto_fix": True,
            "fix_images": True,
            "fix_headings": True,
            "fix_links": True,
            "fix_tables": True,
            "fix_forms": True,
            "fix_landmarks": True,
            "fix_keyboard_nav": True,
            "fix_alt_text": True,
            "single_page": False,
            "multi_page": False,
            "max_issues": None,
            "issue_types": None,
            "severity_threshold": "minor",
        }

        # Log default options for debugging
        logger.debug(f"Default remediation options: {default_options}")

        # Update with user-provided options
        if options:
            default_options.update(options)

        options = default_options

        # Auto-detect image directory if not specified
        if not image_dir:
            image_dir = find_image_directory(html_path)
            logger.debug(f"Auto-detected image directory: {image_dir}")

        # Determine if we're dealing with a single file or a directory
        is_single_page = os.path.isfile(html_path) or options.get("single_page", False)
        is_multi_page = os.path.isdir(html_path) or options.get("multi_page", False)

        # Auto-detect if not specified
        if not is_single_page and not is_multi_page:
            is_single_page = os.path.isfile(html_path)
            is_multi_page = os.path.isdir(html_path)

            if is_single_page:
                logger.debug(f"Auto-detected single page mode for file: {html_path}")
            elif is_multi_page:
                logger.debug(
                    f"Auto-detected multi-page mode for directory: {html_path}"
                )
            else:
                raise DocumentAccessibilityError(f"Invalid path: {html_path}")

        # Initialize result
        result = {
            "html_path": html_path,
            "is_single_page": is_single_page,
            "is_multi_page": is_multi_page,
            "image_dir": image_dir,
        }

        # Handle single-page remediation
        if is_single_page:

            # Copy the original file to output_path if provided
            if output_path:
                # Fix bug: Ensure we don't try to create directories with empty string
                # This happens when output_path is just a filename with no directory
                output_dir = os.path.dirname(output_path)
                if output_dir:  # Only create directories if there's a directory part
                    os.makedirs(output_dir, exist_ok=True)
                shutil.copy2(html_path, output_path)
                result["remediated_html_path"] = output_path

                # Process the audit report and remediate issues
                if audit_report:
                    # Get issues for this file
                    file_issues = [
                        issue
                        for issue in audit_report.get("issues", [])
                        if issue.get("remediation_status") == "needs_remediation"
                    ]

                    # Read and parse the HTML
                    with open(output_path, "r", encoding="utf-8") as f:
                        soup = BeautifulSoup(f.read(), "html.parser")

                    # Skip copying images here - we'll do it once at the end to the images/ folder
                    # This prevents duplicate images in the root directory

                    # Remediate the issues
                    remediation_result = _remediate_html_file(
                        html_path=output_path,
                        issues=file_issues,
                        options=options,
                        image_dir=image_dir,
                        soup=soup,
                    )

                    # Save the modified HTML
                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write(str(soup))

                    # Update result with remediation counts
                    result.update(remediation_result)

                    # Write the updated HTML back to the file
                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write(str(soup))

                    # Copy images if specified
                    if image_dir and os.path.exists(image_dir):
                        # Create images subdirectory in the output directory
                        images_dest_dir = os.path.join(os.path.dirname(output_path), "images")
                        logger.debug(
                            f"Copying images from {image_dir} to {images_dest_dir}"
                        )
                        copy_images_to_output(image_dir, images_dest_dir, soup, use_images_prefix=True)

                        # Write the updated HTML with image references back to the file
                        with open(output_path, "w", encoding="utf-8") as f:
                            f.write(str(soup))
                    else:
                        logger.warning(
                            f"Image directory not specified or does not exist: {image_dir}"
                        )

        # Handle multi-page remediation
        elif is_multi_page:
            # Get list of HTML files in the directory
            html_files = []
            for root, _, files in os.walk(html_path):
                for file in files:
                    if file.lower().endswith(".html"):
                        html_files.append(os.path.join(root, file))

            logger.debug(
                f"Found {len(html_files)} HTML files for multi-page remediation"
            )
            result["html_files"] = html_files

            # Create output directory if needed
            if output_path:
                os.makedirs(output_path, exist_ok=True)

                # Process each HTML file
                total_processed = 0
                total_remediated = 0
                total_failed = 0
                file_results = []  # Store individual file results

                # If we have an audit report, process each file with its issues
                if audit_report:
                    for html_file in html_files:
                        try:
                            # Just use the basename of the HTML file for the output
                            filename = os.path.basename(html_file)
                            output_file = os.path.join(output_path, filename)

                            # Create output directory if needed
                            os.makedirs(os.path.dirname(output_file), exist_ok=True)

                            # Get issues for this file - normalize paths for comparison
                            file_issues = []
                            for issue in audit_report.get("issues", []):
                                if (
                                    issue.get("remediation_status")
                                    != "needs_remediation"
                                ):
                                    continue

                                # Try multiple places where the path might be stored
                                issue_path = issue.get("file_path", "")
                                issue_file_name = issue.get("file_name", "")
                                issue_page_number = issue.get("page_number")
                                
                                # Check location field if root level fields aren't available
                                if "location" in issue and issue["location"]:
                                    if not issue_path:
                                        issue_path = issue["location"].get("file_path", "")
                                    if not issue_file_name:
                                        issue_file_name = issue["location"].get("file_name", "")
                                    if issue_page_number is None:
                                        issue_page_number = issue["location"].get("page_number")

                                # Get current file name for comparison
                                current_file_name = os.path.basename(html_file)
                                
                                # Match by file path (exact or basename)
                                if issue_path and (issue_path == html_file or 
                                                  os.path.basename(issue_path) == current_file_name or
                                                  os.path.abspath(issue_path) == os.path.abspath(html_file)):
                                    file_issues.append(issue)
                                    continue
                                    
                                # Match by file name
                                if issue_file_name and issue_file_name == current_file_name:
                                    file_issues.append(issue)
                                    continue
                                
                                # Match by page number (extracted from filename)
                                if issue_page_number is not None:
                                    match = re.search(r"page[_-]?(\d+)\.html$", current_file_name, re.IGNORECASE)
                                    if match and int(match.group(1)) == issue_page_number:
                                        file_issues.append(issue)
                                        continue

                                # If no file_path, file_name, or page_number found and this is the first HTML file, 
                                # assign all issues with no location info to it
                                if not issue_path and not issue_file_name and issue_page_number is None and html_file == html_files[0]:
                                    file_issues.append(issue)

                            # Log the number of issues found for this file
                            if file_issues:
                                logger.debug(
                                    f"Found {len(file_issues)} issues to remediate for file: {os.path.basename(html_file)}"
                                )
                            else:
                                logger.debug(
                                    f"No issues found for file: {os.path.basename(html_file)}"
                                )

                            # Copy the original file to output
                            shutil.copy2(html_file, output_file)

                            # Read and parse the HTML
                            with open(output_file, "r", encoding="utf-8") as f:
                                soup = BeautifulSoup(f.read(), "html.parser")

                            # Skip copying images here - we'll do it once at the end to the images/ folder
                            # This prevents duplicate images in the root directory

                            # Remediate the issues
                            file_result = _remediate_html_file(
                                html_path=output_file,
                                issues=file_issues,
                                options=options,
                                image_dir=image_dir,
                                soup=soup,
                            )

                            # Save the modified HTML
                            with open(output_file, "w", encoding="utf-8") as f:
                                f.write(str(soup))

                            # Store file result for later aggregation, include the full remediation details
                            file_result["file_path"] = os.path.relpath(
                                html_file, html_path
                            )

                            # Add the file result to the list
                            # FIX: Make sure issues_remediated matches the issues_processed count
                            # This fixes the discrepancy in the file results
                            if (
                                file_result["issues_remediated"]
                                > file_result["issues_processed"]
                            ):
                                file_result["changes_applied"] = file_result[
                                    "issues_remediated"
                                ]
                                file_result["issues_remediated"] = file_result[
                                    "issues_processed"
                                ]
                                file_result["explanation"] = (
                                    f"Fixed {file_result['issues_processed']} issues with {file_result['changes_applied']} HTML changes"
                                )

                            file_results.append(file_result)

                            # Update counts
                            total_processed += file_result.get("issues_processed", 0)
                            total_remediated += file_result.get("issues_remediated", 0)
                            total_failed += file_result.get("issues_failed", 0)

                            # Track failed issue types
                            if "failed_issue_types" in file_result:
                                if "failed_issue_types" not in result:
                                    result["failed_issue_types"] = []
                                result["failed_issue_types"].extend(
                                    file_result.get("failed_issue_types", [])
                                )

                            # Copy images if specified
                            if image_dir and os.path.exists(image_dir):
                                images_dest_dir = os.path.join(output_path, "images")
                                logger.debug(
                                    f"Copying images from {image_dir} to {images_dest_dir}"
                                )
                                copy_images_to_output(image_dir, images_dest_dir, soup, use_images_prefix=True)

                                # Write the updated HTML with image references back to the file
                                with open(output_file, "w", encoding="utf-8") as f:
                                    f.write(str(soup))
                            else:
                                logger.warning(
                                    f"Image directory not specified or does not exist: {image_dir}"
                                )
                        except Exception as e:
                            logger.warning(f"Error remediating HTML file: {e}")
                            total_processed += len(file_issues)
                            total_failed += len(file_issues)

                    # Update result with total counts
                    result["issues_processed"] = total_processed
                    result["issues_remediated"] = total_remediated
                    result["issues_failed"] = total_failed
                    result["file_results"] = (
                        file_results  # Store individual file results
                    )

                    # Add field to explain the discrepancy between processed and remediated counts
                    result["explanation"] = (
                        "Issues count has been standardized to show actual issues processed and remediated correctly."
                    )

                    # Deduplicate failed issue types
                    if "failed_issue_types" in result:
                        result["failed_issue_types"] = list(
                            set(result["failed_issue_types"])
                        )

                    # Handle page mode based on flags
                    # If multi_page is True, never combine pages
                    # If single_page is True, always combine pages
                    # If neither flag is set, default to multi_page
                    if options.get("single_page", False):
                        logger.debug(
                            "Creating combined HTML document with all remediated pages"
                        )
                        combined_html_path = os.path.join(
                            output_path, "remediated_document.html"
                        )

                        # Sort HTML files by page number
                        sorted_html_files = []
                        for html_file in html_files:
                            if os.path.basename(html_file).startswith("page-"):
                                try:
                                    page_num = int(
                                        os.path.basename(html_file)
                                        .split("-")[1]
                                        .split(".")[0]
                                    )
                                    sorted_html_files.append((page_num, html_file))
                                except (IndexError, ValueError):
                                    # If we can't parse the page number, just add it to the end
                                    sorted_html_files.append((999, html_file))
                            else:
                                # Non-page files go at the end
                                sorted_html_files.append((999, html_file))

                        sorted_html_files.sort()
                        sorted_html_files = [f for _, f in sorted_html_files]

                        logger.debug(
                            f"Sorted {len(sorted_html_files)} HTML files for combining"
                        )

                        # Create base document structure
                        combined_soup = BeautifulSoup(
                            """
                        <!DOCTYPE html>
                        <html lang="en">
                        <head>
                            <meta charset="utf-8"/>
                            <meta content="width=device-width, initial-scale=1.0" name="viewport"/>
                            <title>Remediated Document</title>
                            <style>
                                body { font-family: Arial, sans-serif; line-height: 1.6; }
                                .page-break { page-break-after: always; margin-bottom: 30px; border-bottom: 1px dashed #ccc; }
                                
                                .skip-link {
                                    position: absolute;
                                    top: -40px;
                                    left: 0;
                                    background: #000;
                                    color: white;
                                    padding: 8px;
                                    z-index: 100;
                                    transition: top 0.3s;
                                }
                                
                                .skip-link:focus {
                                    top: 0;
                                }
                            </style>
                        </head>
                        <body>
                            <header role="banner"><h1>Remediated Document</h1></header>
                            <nav aria-label="Main navigation" role="navigation">
                                <ul>
                                    <li><a href="#">Home</a></li>
                                    <li><a href="#">Table of Contents</a></li>
                                </ul>
                            </nav>
                            <a class="skip-link" href="#main-content">Skip to main content</a>
                            <main id="main-content" role="main">
                            </main>
                        </body>
                        </html>
                        """,
                            "html.parser",
                        )

                        # Get the main content container
                        main_content = combined_soup.find("main")

                        # Try to find a title in the first few pages
                        for i, html_file in enumerate(sorted_html_files[:5]):
                            try:
                                rel_path = os.path.relpath(html_file, html_path)
                                remediate_path = os.path.join(output_path, rel_path)

                                with open(remediate_path, "r", encoding="utf-8") as f:
                                    page_soup = BeautifulSoup(f.read(), "html.parser")

                                # Look for a title or h1
                                title = page_soup.find("title")
                                if (
                                    title
                                    and title.string
                                    and title.string.strip()
                                    and title.string.strip() != "0"
                                ):
                                    combined_soup.title.string = title.string
                                    combined_soup.find("h1").string = title.string
                                    break

                                h1 = page_soup.find("h1")
                                if h1 and h1.string and h1.string.strip():
                                    combined_soup.title.string = h1.string
                                    combined_soup.find("h1").string = h1.string
                                    break
                            except Exception as e:
                                logger.warning(
                                    f"Error extracting title from {html_file}: {e}"
                                )

                        # Process each HTML file and add its content to the combined document
                        for i, html_file in enumerate(sorted_html_files):
                            try:
                                rel_path = os.path.relpath(html_file, html_path)
                                remediate_path = os.path.join(output_path, rel_path)

                                with open(remediate_path, "r", encoding="utf-8") as f:
                                    page_soup = BeautifulSoup(f.read(), "html.parser")

                                # Create a section for this page
                                page_section = combined_soup.new_tag("section")
                                page_section["id"] = f"page-{i+1}"
                                page_section["class"] = "page-content"
                                page_section["aria-label"] = f"Page {i+1}"

                                # Get the page content (body content)
                                page_content = page_soup.find("body")
                                if page_content:
                                    # Add all content from the page body to the section
                                    for element in list(page_content.children):
                                        if element.name:  # Skip text nodes
                                            page_section.append(element.extract())

                                # Add a page break after each page (except the last one)
                                if i < len(sorted_html_files) - 1:
                                    page_break = combined_soup.new_tag("div")
                                    page_break["class"] = "page-break"
                                    page_section.append(page_break)

                                # Add the page section to the main content
                                main_content.append(page_section)

                                logger.debug(
                                    f"Added content from {os.path.basename(html_file)}"
                                )

                            except Exception as e:
                                logger.error(f"Error processing {html_file}: {e}")

                        # Save the combined HTML
                        with open(combined_html_path, "w", encoding="utf-8") as f:
                            f.write(str(combined_soup))

                        logger.debug(f"Combined HTML saved to {combined_html_path}")
                        result["remediated_html_path"] = combined_html_path
                    else:
                        # When in multi-page mode, set the output directory as the result
                        result["remediated_html_path"] = output_path
                        logger.debug(
                            f"Multi-page remediation completed, output saved to directory: {output_path}"
                        )

        # Add options to result
        result["options"] = {
            "auto_fix": options["auto_fix"],
            "fix_images": options["fix_images"],
            "fix_headings": options["fix_headings"],
            "fix_links": options["fix_links"],
            "fix_tables": options["fix_tables"],
            "fix_forms": options["fix_forms"],
            "fix_landmarks": options["fix_landmarks"],
            "fix_keyboard_nav": options["fix_keyboard_nav"],
            "fix_alt_text": options["fix_alt_text"],
            "max_issues": options["max_issues"],
            "issue_types": options["issue_types"],
            "severity_threshold": options["severity_threshold"],
            "image_dir": image_dir,
        }

        return result

    except Exception as e:
        raise DocumentAccessibilityError(f"Failed to remediate HTML accessibility: {e}")


def _remediate_html_file(
    html_path: str,
    issues: List[Dict[str, Any]],
    options: Dict[str, Any],
    image_dir: Optional[str] = None,
    soup: Optional[BeautifulSoup] = None,
) -> Dict[str, Any]:
    """
    Remediate accessibility issues in a single HTML file.

    Args:
        html_path: Path to the HTML file.
        issues: List of issues to remediate.
        options: Remediation options.
        image_dir: Directory containing images referenced in the HTML.
        soup: Optional BeautifulSoup object if already parsed

    Returns:
        Dictionary containing remediation results.
    """
    result = {
        "issues_processed": 0,
        "issues_remediated": 0,
        "issues_failed": 0,
        "failed_issue_types": [],
    }

    try:
        # Parse HTML if not already provided
        if not soup:
            with open(html_path, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), "html.parser")

        # Store original URL in soup object for context
        soup.original_url = html_path

        # Create a remediation manager and pass the profile parameter
        # Make sure to pass the profile from options to the RemediationManager
        remediation_manager = RemediationManager(soup, options)

        # Remediate issues
        if issues:
            # Log the number of issues being processed
            logger.debug(
                f"Processing {len(issues)} issues for remediation in {html_path}"
            )

            remediation_result = remediation_manager.remediate_issues(issues)

            # Update result with remediation counts
            result["issues_processed"] = len(issues)
            result["issues_remediated"] = remediation_result.get(
                "actual_issues_fixed", remediation_result.get("issues_remediated", 0)
            )
            result["issues_failed"] = remediation_result.get("issues_failed", 0)
            result["failed_issue_types"] = remediation_result.get(
                "failed_issue_types", []
            )

            # Track the total number of changes applied (which may be more than issues processed)
            if "total_changes_applied" in remediation_result:
                result["changes_applied"] = remediation_result.get(
                    "total_changes_applied"
                )

            # Add detailed issue results for reporting
            result["details"] = remediation_result.get("details", [])
            result["remediated_issues_details"] = remediation_result.get(
                "remediated_issues_details", []
            )
            result["failed_issues_details"] = remediation_result.get(
                "failed_issues_details", []
            )

            # Log detailed results
            logger.debug(
                f"Remediation completed: {result['issues_remediated']} fixed, {result['issues_failed']} failed"
            )
        else:
            # No issues to remediate
            logger.debug(f"No issues to remediate for {html_path}")
            result["issues_processed"] = 0
            result["issues_remediated"] = 0
            result["issues_failed"] = 0

        return result

    except Exception as e:
        logger.warning(f"Error remediating HTML file: {e}")
        raise DocumentAccessibilityError(f"Failed to remediate HTML file: {e}")
