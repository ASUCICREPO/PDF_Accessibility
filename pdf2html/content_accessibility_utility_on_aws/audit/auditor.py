# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
HTML Accessibility Auditor.

This module provides functionality for auditing
HTML content against WCAG 2.1 accessibility standards.
"""

import os
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup


from content_accessibility_utility_on_aws.audit.checks import (
    HeadingHierarchyCheck,
    HeadingContentCheck,
    DocumentTitleCheck,
    DocumentLanguageCheck,
    MainLandmarkCheck,
    SkipLinkCheck,
    LandmarksCheck,
    AltTextCheck,
    FigureStructureCheck,
    LinkTextCheck,
    NewWindowLinkCheck,
    TableHeaderCheck,
    TableStructureCheck,
    ColorContrastCheck,
    FormLabelCheck,
    FormRequiredFieldCheck,
    FormFieldsetCheck,
)
from content_accessibility_utility_on_aws.utils.logging_helper import (
    setup_logger,
)
from content_accessibility_utility_on_aws.audit.standards import (
    SEVERITY_LEVELS,
    get_criterion_info,
)

# Set up module-level logger
logger = setup_logger(__name__)


class AccessibilityAuditor:
    """Class for auditing HTML content for WCAG 2.1 accessibility compliance issues."""

    def __init__(
        self,
        html_path: Optional[str] = None,
        html_content: Optional[str] = None,
        image_dir: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the accessibility auditor.

        Args:
            html_path: Path to the HTML file to audit.
            html_content: HTML content string to audit instead of a file.
            image_dir: Directory containing images referenced in the HTML.
            options: Auditing options:
                - severity_threshold (str): Minimum severity level to report ('critical', 'major', 'minor').
                - report_format (str): Format for the report ('json', 'html', 'text').
                - detailed (bool): Whether to include detailed context in the report.
                - include_remediated (bool): Whether to include remediated items in
                    report (default: True).
        """
        self.html_path = html_path
        self.html_content = html_content
        self.image_dir = image_dir
        self.soup = None
        self.images = []
        self.links = []
        self.html_files = []  # Initialize html_files as an empty list
        self.headings = []
        self.forms = []
        self.tables = []
        self.form_elements = []  # Initialize form_elements as an empty list

        # Set default options
        self.options = {
            "severity_threshold": "minor",  # Include all issues
            "report_format": "json",
            "detailed": True,
            "include_remediated": True,
        }

        # Update with user-provided options
        if options:
            self.options.update(options)

        # Initialize issues list
        self.issues: List[Dict[str, Any]] = []

    def load_html(self) -> bool:
        """
        Load and parse the HTML content.

        Returns:
            True if loading was successful, False otherwise.
        """
        try:
            # Case 1: HTML content is directly provided
            if self.html_content:
                self.soup = BeautifulSoup(self.html_content, "html.parser")
                return True

            # Case 2: HTML path is provided
            elif self.html_path and os.path.exists(self.html_path):
                # Check if the path is a directory (multi-page mode)
                if os.path.isdir(self.html_path):
                    logger.debug(
                        "HTML path is a directory, looking for HTML files in: %s",
                        self.html_path,
                    )
                    # Check for extracted_html subdirectory
                    extracted_html_dir = os.path.join(self.html_path, "extracted_html")
                    if os.path.isdir(extracted_html_dir):
                        logger.debug(
                            "Found extracted_html subdirectory: %s",
                            extracted_html_dir,
                        )
                        self.html_path = extracted_html_dir

                    # Find all HTML files in the directory
                    html_files = []
                    for file in os.listdir(self.html_path):
                        if file.endswith(".html"):
                            html_files.append(os.path.join(self.html_path, file))

                    if not html_files:
                        logger.error(
                            "No HTML files found in directory: %s", self.html_path
                        )
                        return False

                    # Sort HTML files (important for page order)
                    html_files.sort()
                    logger.debug("Found %d HTML files in directory", len(html_files))

                    # Use the first HTML file for initial parsing
                    # (We'll process all files during audit if multi-page option is set)
                    with open(html_files[0], "r", encoding="utf-8") as f:
                        self.html_content = f.read()
                    self.soup = BeautifulSoup(self.html_content, "html.parser")

                    # Store information about all files for multi-page processing
                    self.html_files = html_files
                    return True

                # Regular file handling
                else:
                    with open(self.html_path, "r", encoding="utf-8") as f:
                        self.html_content = f.read()
                    self.soup = BeautifulSoup(self.html_content, "html.parser")
                    return True
            else:
                logger.error("No HTML content or valid file path provided")
                return False

        except (FileNotFoundError, IsADirectoryError, IOError) as e:
            logger.error("Error loading HTML: %s", str(e))
            return False

    def extract_elements(self) -> None:
        """Extract key elements from the HTML for analysis."""
        if not self.soup:
            if not self.load_html():
                return

        # Extract images
        self.images = self.soup.find_all("img")

        # Extract links
        self.links = self.soup.find_all("a")

        # Extract headings
        self.headings = []
        for i in range(1, 7):
            self.headings.extend(self.soup.find_all(f"h{i}"))

        # Extract forms and form elements
        self.form_elements.clear()
        self.form_elements.extend(
            self.soup.find_all(["input", "select", "textarea", "button", "label"])
        )

        # Extract tables
        self.tables = self.soup.find_all("table")

    def audit(self) -> Dict[str, Any]:
        """
        Perform a comprehensive accessibility audit on the HTML content.

        Returns:
            Audit report containing identified issues.
        """
        self.issues = []

        if not self.soup:
            if not self.load_html():
                # Return an empty report if we couldn't load the HTML
                return self._generate_report()

        # Check if we're in multi-page mode (processing a directory of HTML files)
        if hasattr(self, "html_files") and self.html_files:
            logger.debug(
                "Multi-page mode: Processing %d HTML files", len(self.html_files)
            )

            # Process each HTML file separately
            for html_file in self.html_files:
                logger.debug("Processing HTML file: %s", html_file)
                try:
                    # Load the HTML content for this file
                    with open(html_file, "r", encoding="utf-8") as f:
                        html_content = f.read()

                    # Parse the HTML
                    page_soup = BeautifulSoup(html_content, "html.parser")

                    # Extract the page number from the filename if it follows the page-X.html pattern
                    page_num = None
                    file_name = os.path.basename(html_file)
                    match = re.search(r"page[_-]?(\d+)\.html$", file_name, re.IGNORECASE)
                    if match:
                        page_num = int(match.group(1))
                        logger.debug("Extracted page number %d from filename: %s", page_num, file_name)

                    # Run accessibility checks on this page
                    self._audit_page(page_soup, page_num, html_file, file_name)

                except Exception as e:
                    logger.error("Error processing HTML file %s: %s", html_file, str(e))
        else:
            # Single page mode - audit the already loaded HTML
            logger.info("Single page mode: Processing HTML content")
            # Pass the file path if available
            file_path = self.html_path if hasattr(self, "html_path") and self.html_path else None
            self._audit_page(self.soup, None, file_path)

        # Generate and return the report
        logger.info("Audit completed. Total issues found: %d", len(self.issues))
        
        # Ensure all issues have a valid location field
        for issue in self.issues:
            if "location" not in issue or issue["location"] is None:
                issue["location"] = {}
            
            # Ensure page_number exists in location
            if "page_number" not in issue["location"]:
                # Try to get page number from root level if available
                if "page_number" in issue:
                    issue["location"]["page_number"] = issue["page_number"]
                else:
                    issue["location"]["page_number"] = 0

        # Group issues by page
        issues_by_page = {}
        for issue in self.issues:
            page_num = issue["location"].get("page_number", 0)
            if page_num not in issues_by_page:
                issues_by_page[page_num] = []
            issues_by_page[page_num].append(issue)

        # Group issues by status
        issues_by_status = {
            "needs_remediation": [],
            "remediated": [],
            "auto_remediated": [],
            "compliant": [],
        }

        for issue in self.issues:
            status = issue.get("remediation_status", "needs_remediation")
            if status in issues_by_status:
                issues_by_status[status].append(issue)
                logger.debug("Added issue to %s group: %s", status, issue.get("type"))

        # Count issues by status
        needs_remediation_count = len(issues_by_status["needs_remediation"])
        remediated_count = len(issues_by_status["remediated"])
        auto_remediated_count = len(issues_by_status["auto_remediated"])
        compliant_count = len(issues_by_status["compliant"])

        logger.debug(
            "Issue counts - needs_remediation: %d, remediated: %d, auto_remediated: %d, compliant: %d",
            needs_remediation_count,
            remediated_count,
            auto_remediated_count,
            compliant_count,
        )

        # Group issues by severity
        severity_counts = {"critical": 0, "major": 0, "minor": 0, "info": 0}

        for issue in self.issues:
            severity = issue.get("severity", "info")
            if severity in severity_counts:
                severity_counts[severity] += 1

        report = {
            "summary": {
                "total_issues": len(self.issues),
                "needs_remediation": needs_remediation_count,
                "remediated": remediated_count,
                "auto_remediated": auto_remediated_count,
                "compliant": compliant_count,
                "severity_counts": severity_counts,
            },
            "by_page": {
                page: {
                    "total": len(page_issues),
                    "needs_remediation": len(
                        [
                            i
                            for i in page_issues
                            if i["remediation_status"] == "needs_remediation"
                        ]
                    ),
                    "remediated": len(
                        [
                            i
                            for i in page_issues
                            if i["remediation_status"] == "remediated"
                        ]
                    ),
                    "auto_remediated": len(
                        [
                            i
                            for i in page_issues
                            if i["remediation_status"] == "auto_remediated"
                        ]
                    ),
                    "compliant": len(
                        [
                            i
                            for i in page_issues
                            if i["remediation_status"] == "compliant"
                        ]
                    ),
                    "issues": page_issues,
                }
                for page, page_issues in issues_by_page.items()
            },
            "by_status": issues_by_status,
            "issues": self.issues,
        }

        logger.debug("Report summary: %s", report["summary"])
        return report

    def _audit_page(self, soup, page_num=None, file_path=None, file_name=None):
        """
        Audit a single HTML page.

        Args:
            soup: BeautifulSoup object for the HTML page
            page_num: Optional page number for multi-page documents
            file_path: Optional file path for reference
            file_name: Optional file name for reference
        """
        # Store the current soup and extract elements
        original_soup = self.soup
        self.soup = soup
        self.extract_elements()

        # Extract file name from file path if not provided
        if file_name is None and file_path:
            file_name = os.path.basename(file_path)
            
        # Try to extract page number from filename if not provided
        if page_num is None and file_name:
            match = re.search(r"page[_-]?(\d+)\.html$", file_name, re.IGNORECASE)
            if match:
                page_num = int(match.group(1))
                logger.info("Extracted page number %d from filename: %s", page_num, file_name)

        logger.debug(
            "Running accessibility checks on %s",
            f"page {page_num}" if page_num is not None else f"file {file_name}" if file_name else "(single page)",
        )

        # Track the number of issues before running checks on this page
        current_issues_count = len(self.issues)

        # Initialize and run all checks
        checks = [
            HeadingHierarchyCheck(self.soup, self._add_issue),
            HeadingContentCheck(self.soup, self._add_issue),
            DocumentTitleCheck(self.soup, self._add_issue),
            DocumentLanguageCheck(self.soup, self._add_issue),
            MainLandmarkCheck(self.soup, self._add_issue),
            SkipLinkCheck(self.soup, self._add_issue),
            LandmarksCheck(self.soup, self._add_issue),
            AltTextCheck(self.soup, self._add_issue),
            FigureStructureCheck(self.soup, self._add_issue),
            LinkTextCheck(self.soup, self._add_issue),
            NewWindowLinkCheck(self.soup, self._add_issue),
            TableHeaderCheck(self.soup, self._add_issue),
            TableStructureCheck(self.soup, self._add_issue),
            ColorContrastCheck(self.soup, self._add_issue),
            FormLabelCheck(self.soup, self._add_issue),
            FormRequiredFieldCheck(self.soup, self._add_issue),
            FormFieldsetCheck(self.soup, self._add_issue),
        ]

        for check in checks:
            try:
                logger.debug("Running check: %s", check.__class__.__name__)
                check.check()
                logger.debug(
                    "Completed check: %s, total issues: %d",
                    check.__class__.__name__,
                    len(self.issues),
                )
            except Exception as e:
                logger.error(
                    "Error running check %s: %s", check.__class__.__name__, str(e)
                )

        # Get only the new issues added during this page's checks
        new_issues = self.issues[current_issues_count:]

        for issue in new_issues:
            # Ensure location is always a dictionary, never None
            if "location" not in issue or issue["location"] is None:
                issue["location"] = {}

            # Always set file path if available
            if file_path:
                # Store both in location and at the root level for compatibility
                issue["location"]["file_path"] = file_path
                issue["file_path"] = file_path
                
                # Also store the file name for easier reference
                issue["location"]["file_name"] = file_name
                issue["file_name"] = file_name

            # Set page number if available (either provided or extracted from filename)
            if page_num is not None:
                issue["location"]["page_number"] = page_num
                issue["page_number"] = page_num  # Also store at root level for compatibility
                
                # Add a human-readable description that includes both file name and page number if available
                if file_name:
                    issue["location"]["description"] = f"File: {file_name} (Page {page_num})"
                else:
                    issue["location"]["description"] = f"Page {page_num}"
            else:
                # If no page number, just use the file name as the description
                if file_name:
                    issue["location"]["description"] = f"File: {file_name}"

        # Restore original soup
        self.soup = original_soup

    def _generate_report(self) -> Dict[str, Any]:
        """
        Generate a report based on the identified issues.

        Returns:
            Report containing identified issues and remediation status.
        """
        logger.debug("Generating report with %d total issues", len(self.issues))

        # Group issues by page
        issues_by_page = {}
        for issue in self.issues:
            # Ensure location is always a dictionary, never None
            if "location" not in issue or issue["location"] is None:
                issue["location"] = {}
                
            # Ensure page_number exists in location
            if "page_number" not in issue["location"]:
                # Try to get page number from root level if available
                if "page_number" in issue:
                    issue["location"]["page_number"] = issue["page_number"]
                else:
                    issue["location"]["page_number"] = 0
                    
            page_num = issue["location"].get("page_number", 0)
            if page_num not in issues_by_page:
                issues_by_page[page_num] = []
            issues_by_page[page_num].append(issue)

        # Group issues by status
        issues_by_status = {
            "needs_remediation": [],
            "remediated": [],
            "auto_remediated": [],
            "compliant": [],
        }

        for issue in self.issues:
            status = issue.get("remediation_status", "needs_remediation")
            if status in issues_by_status:
                issues_by_status[status].append(issue)
                logger.debug("Added issue to %s group: %s", status, issue.get("type"))

        # Count issues by status
        needs_remediation_count = len(issues_by_status["needs_remediation"])
        remediated_count = len(issues_by_status["remediated"])
        auto_remediated_count = len(issues_by_status["auto_remediated"])
        compliant_count = len(issues_by_status["compliant"])

        logger.debug(
            "Issue counts - needs_remediation: %d, remediated: %d, auto_remediated: %d, compliant: %d",
            needs_remediation_count,
            remediated_count,
            auto_remediated_count,
            compliant_count,
        )

        report = {
            "summary": {
                "total_issues": len(self.issues),
                "needs_remediation": needs_remediation_count,
                "remediated": remediated_count,
                "auto_remediated": auto_remediated_count,
                "compliant": compliant_count,
            },
            "by_page": {
                page: {
                    "total": len(page_issues),
                    "needs_remediation": len(
                        [
                            i
                            for i in page_issues
                            if i["remediation_status"] == "needs_remediation"
                        ]
                    ),
                    "remediated": len(
                        [
                            i
                            for i in page_issues
                            if i["remediation_status"] == "remediated"
                        ]
                    ),
                    "auto_remediated": len(
                        [
                            i
                            for i in page_issues
                            if i["remediation_status"] == "auto_remediated"
                        ]
                    ),
                    "compliant": len(
                        [
                            i
                            for i in page_issues
                            if i["remediation_status"] == "compliant"
                        ]
                    ),
                    "issues": page_issues,
                }
                for page, page_issues in issues_by_page.items()
            },
            "by_status": issues_by_status,
            "issues": self.issues,
        }

        logger.debug("Report summary: %s", report["summary"])
        return report

    def _add_issue(
        self,
        issue_type: str,
        wcag_criterion: str,
        severity: str,
        element=None,
        description=None,
        context=None,
        location=None,
        status="needs_remediation",
        remediation_source=None,
    ):
        """
        Add an issue to the issues list.

        Args:
            issue_type: Type of issue (e.g., 'missing-alt-text').
            wcag_criterion: WCAG criterion number (e.g., '1.1.1').
            severity: Severity level ('critical', 'major', 'minor', 'info').
            element: The HTML element with the issue.
            description: Description of the issue.
            context: HTML context around the issue.
            location: Location information.
            status: Remediation status ('needs_remediation', 'remediated', 'auto_remediated', 'compliant').
            remediation_source: Source of remediation ('manual', 'bda', None).
        """
        # Debug logging
        logger.debug(
            "Adding issue: %s, status: %s, severity: %s", issue_type, status, severity
        )

        # Always include compliant issues
        if status == "compliant":
            logger.debug("Including compliant issue: %s", issue_type)
            pass  # Always include compliant issues
        else:
            # Skip if below severity threshold and not remediated
            threshold = self.options.get("severity_threshold", "minor")
            min_severity = SEVERITY_LEVELS.get(threshold, 1)
            if SEVERITY_LEVELS.get(severity, 0) < min_severity:
                logger.debug("Skipping issue due to severity threshold: %s", issue_type)
                return

            # Skip remediated items if not included in options
            if (
                not self.options.get("include_remediated", True)
                and status != "needs_remediation"
            ):
                logger.debug("Skipping remediated issue: %s", issue_type)
                return

        # Create a unique ID for the issue
        issue_id = f"issue-{len(self.issues) + 1}"

        # Generate enhanced context if detailed option is enabled and element is provided
        if self.options.get("detailed", True) and element and context is None:
            try:
                from content_accessibility_utility_on_aws.audit.context_collector import (
                    ContextCollector,
                )

                context = ContextCollector(element).collect()
            except Exception as e:
                logger.error("Error collecting enhanced context: %s", str(e))
                context = {"error": f"Could not extract context: {str(e)}"}
                # Provide a basic context as fallback
                if element and hasattr(element, "name"):
                    context = {"element_name": element.name}
                    if hasattr(element, "attrs"):
                        context["attributes"] = element.attrs

        # Generate element string representation
        element_str = (
            element.name if element and hasattr(element, "name") else "unknown"
        )

        # Create location info if not provided
        if location is None and element:
            location = {
                "path": self._get_element_path(element),
                "page_number": self._get_page_number(element),
            }

        # Get criterion info
        criterion_info = get_criterion_info(wcag_criterion)

        # Create the issue object
        issue = {
            "id": issue_id,
            "type": issue_type,
            "wcag_criterion": wcag_criterion,
            "criterion_name": criterion_info.get("name", ""),
            "criterion_level": criterion_info.get("level", ""),
            "severity": severity,
            "element": element_str,
            "description": description or f"WCAG {wcag_criterion} issue: {issue_type}",
            "context": context if self.options.get("detailed", True) else None,
            "location": location,
            "remediation_status": status,
            "remediation_source": remediation_source,
            "remediation_date": (
                datetime.utcnow().isoformat()
                if status in ["remediated", "auto_remediated"]
                else None
            ),
        }

        # Add the issue to the list
        self.issues.append(issue)
        logger.debug(
            "Added issue to list: %s, status: %s, total issues: %d",
            issue_type,
            status,
            len(self.issues),
        )

    def _get_page_number(self, element) -> Optional[int]:
        """Get the page number for an element based on its location in the document."""
        if not element:
            return None

        # First check for data-page-number attribute
        page_num = element.get("data-page-number")
        if page_num and str(page_num).isdigit():
            return int(page_num)

        # Then check for page-specific container
        page_container = element.find_parent(
            lambda tag: tag.get("class")
            and any("page" in cls.lower() for cls in tag.get("class"))
        )
        if page_container:
            # Try to extract page number from class or id
            # Handle class attribute which could be a list
            classes = page_container.get("class", [])
            if classes:
                for cls in classes:
                    match = re.search(r"page[_-]?(\d+)", cls.lower())
                    if match:
                        return int(match.group(1))

            # Check id attribute
            element_id = page_container.get("id", "")
            if element_id:
                match = re.search(r"page[_-]?(\d+)", element_id.lower())
                if match:
                    return int(match.group(1))

        return None

    def _get_element_path(self, element) -> str:
        """
        Get the CSS selector path to an element.

        Args:
            element: The HTML element.

        Returns:
            CSS selector path.
        """
        try:
            path = []
            current = element
            while current and hasattr(current, "name"):
                # Check for ID
                if current.get("id"):
                    path.append(f"{current.name}#{current.get('id')}")
                    break
                # Check for classes
                elif current.get("class"):
                    # Handle class attribute which could be a list
                    classes = current.get("class", [])
                    if classes:
                        path.append(
                            f"{current.name}.{'.'.join(str(cls) for cls in classes)}"
                        )
                # Check for nth-of-type
                else:
                    siblings = current.find_previous_siblings(current.name)
                    if siblings:
                        path.append(f"{current.name}:nth-of-type({len(siblings) + 1})")
                    else:
                        path.append(current.name)
                current = current.parent

            # Reverse path to get correct order from root to element
            return " > ".join(reversed(path))
        except Exception as e:
            logger.error("Error generating element path: %s", str(e))
            return "Unknown path"

    def _check_text_alternatives(self):
        """Check for WCAG 1.1.1 - Text Alternatives compliance issues."""
        if not self.images:
            return

        for img in self.images:
            # Get figure context if image is part of a figure
            figure = img.find_parent("figure")
            figcaption = figure.find("figcaption") if figure else None

            # Check for missing alt attribute
            if not img.has_attr("alt"):
                self._add_issue(
                    "missing-alt-text",
                    "1.1.1",
                    "critical",
                    img,
                    "Image missing alternative text",
                    status="needs_remediation",
                )
            else:
                alt_text = img["alt"].strip()
                # Check if alt text was added by BDA
                if img.get("data-bda-generated-alt") == "true":
                    self._add_issue(
                        "alt-text-present",
                        "1.1.1",
                        "info",
                        img,
                        "Image has BDA-generated alt text",
                        status="auto_remediated",
                        remediation_source="bda",
                    )
                    # Still check if the BDA-generated alt text is generic
                    if re.search(
                        r"^image\s*\d*$|^photo\s*\d*$|^picture\s*\d*$|^graphic\s*\d*$|^IMAGE$|^ICON$|^FIGURE$|^DIAGRAM$",
                        alt_text,
                    ):
                        self._add_issue(
                            "generic-alt-text",
                            "1.1.1",
                            "major",
                            img,
                            f'BDA-generated alt text "{alt_text}" is generic and needs improvement',
                            status="needs_remediation",
                        )
                elif alt_text == "" and not self._is_decorative_image(img):
                    self._add_issue(
                        "empty-alt-text",
                        "1.1.1",
                        "major",
                        img,
                        "Non-decorative image has empty alternative text",
                        status="needs_remediation",
                    )
                elif re.search(
                    r"^image\s*\d*$|^photo\s*\d*$|^picture\s*\d*$|^graphic\s*\d*$|^IMAGE$|^ICON$|^FIGURE$|^DIAGRAM$",
                    alt_text,
                ):
                    issue_type = "generic-alt-text"
                    if alt_text in ["ICON", "DIAGRAM", "FIGURE", "IMAGE"]:
                        issue_type = f"generic-alt-text-{alt_text.lower()}"

                    self._add_issue(
                        issue_type,
                        "1.1.1",
                        "major",
                        img,
                        f'Image has generic alternative text "{alt_text}" that does not describe content',
                        context=self._get_image_context(img),
                        location={
                            "path": self._get_element_path(img),
                            "image_src": img.get("src", ""),
                            "element_id": img.get("data-bda-id", ""),
                            "alt_type": alt_text,
                        },
                        status="needs_remediation",
                    )
                elif len(alt_text) > 150:
                    self._add_issue(
                        "long-alt-text",
                        "1.1.1",
                        "minor",
                        img,
                        "Alternative text is too long (consider using aria-describedby for complex images)",
                        status="needs_remediation",
                    )
                else:
                    self._add_issue(
                        "alt-text-present",
                        "1.1.1",
                        "info",
                        img,
                        "Image has appropriate alt text",
                        status="remediated",
                        remediation_source="manual",
                    )

            # Check for proper figure structure
            if not figure and self._is_complex_figure(img):
                self._add_issue(
                    "improper-figure-structure",
                    "1.1.1",
                    "major",
                    img,
                    "Complex figure should be wrapped in <figure> element with <figcaption>",
                    context=self._get_image_context(img),
                    location={
                        "path": self._get_element_path(img),
                        "element_id": img.get("data-bda-id", ""),
                    },
                    status="needs_remediation",
                )
            elif figure and not figcaption:
                self._add_issue(
                    "missing-figcaption",
                    "1.1.1",
                    "major",
                    figure,
                    "Figure element missing <figcaption>",
                    context=self._get_image_context(img),
                    location={
                        "path": self._get_element_path(figure),
                        "element_id": img.get("data-bda-id", ""),
                    },
                    status="needs_remediation",
                )

    def _is_decorative_image(self, img) -> bool:
        """
        Determine if an image is likely decorative.

        Args:
            img: The image element.

        Returns:
            True if the image is likely decorative, False otherwise.
        """
        # Check for role="presentation" or aria-hidden="true"
        if img.get("role") == "presentation" or img.get("aria-hidden") == "true":
            return True

        # Check if it's a small image (likely decorative)
        width = img.get("width")
        height = img.get("height")
        if width and height and int(width) < 20 and int(height) < 20:
            return True

        # Check for common decorative image patterns
        src = img.get("src", "")
        if "separator" in src or "divider" in src or "spacer" in src or "bullet" in src:
            return True

        return False

    def _is_complex_figure(self, img) -> bool:
        """
        Determine if an image is likely a complex figure needing extended description.

        Args:
            img: The image element

        Returns:
            True if the image appears to be a complex figure, False otherwise
        """
        # Check for BDA identification
        if img.get("data-bda-id", ""):
            # Look for nearby text containing figure references
            next_p = img.find_next("p")
            if next_p and re.search(r"Figure\s+\d+", next_p.get_text()):
                return True

        # Check image filename patterns
        src = img.get("src", "").lower()
        if any(term in src for term in ["figure", "diagram", "chart", "graph"]):
            return True

        # Check for large dimensions suggesting complex content
        width = img.get("width")
        height = img.get("height")
        if width and height and int(width) > 300 and int(height) > 300:
            return True

        return False

    def _get_image_context(self, img) -> str:
        """
        Extract content around an image to provide context for alt text generation.

        Args:
            img: The image element.

        Returns:
            Surrounding content that provides context for the image.
        """
        context = []

        # Get the parent element
        parent = img.parent

        # Check if the image is inside a figure element with a figcaption
        if parent.name == "figure" or parent.find_parent("figure"):
            figure = parent if parent.name == "figure" else parent.find_parent("figure")
            figcaption = figure.find("figcaption")
            if figcaption and figcaption.get_text().strip():
                context.append(f"Caption: {figcaption.get_text().strip()}")

        # Get text in the same parent container
        if parent and parent.name != "body":
            # Get text before the image
            prev_text = "".join(
                str(s)
                for s in img.previous_siblings
                if isinstance(s, str) or s.name != "img"
            )
            if prev_text:
                soup_text = BeautifulSoup(prev_text, "html.parser")
                if soup_text.get_text().strip():
                    context.append(
                        f"Text before image: {soup_text.get_text().strip()[:200]}"
                    )

            # Get text after the image
            next_text = "".join(
                str(s)
                for s in img.next_siblings
                if isinstance(s, str) or s.name != "img"
            )
            if next_text:
                soup_text = BeautifulSoup(next_text, "html.parser")
                if soup_text.get_text().strip():
                    context.append(
                        f"Text after image: {soup_text.get_text().strip()[:200]}"
                    )

        # Look for nearby headings
        prev_heading = img.find_previous(["h1", "h2", "h3", "h4", "h5", "h6"])
        if prev_heading and prev_heading.get_text().strip():
            context.append(f"Nearest heading: {prev_heading.get_text().strip()}")

        # If it's in a paragraph
        p_parent = img.find_parent("p")
        if p_parent:
            p_text = "".join(str(s) for s in p_parent.contents if s != img)
            if p_text:
                soup_text = BeautifulSoup(p_text, "html.parser")
                if soup_text.get_text().strip():
                    context.append(
                        f"Paragraph text: {soup_text.get_text().strip()[:200]}"
                    )

        # Get alt text if it exists but is generic
        if img.has_attr("alt") and img["alt"].strip():
            context.append(f"Current alt text: {img['alt'].strip()}")

        # Include any ARIA attributes
        aria_attrs = [attr for attr in img.attrs if attr.startswith("aria-")]
        for attr in aria_attrs:
            context.append(f"ARIA {attr}: {img[attr]}")

        return "\n".join(context) if context else "No surrounding context found"
