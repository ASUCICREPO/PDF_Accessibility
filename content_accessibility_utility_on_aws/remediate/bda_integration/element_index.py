# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Element Index module.

This module provides functionality for indexing and organizing BDA elements
and connecting them with accessibility issues.
"""

from typing import Dict, List, Any, Optional, Union
from content_accessibility_utility_on_aws.utils.logging_helper import setup_logger

# Set up module-level logger
logger = setup_logger(__name__)


class ElementIndex:
    """Indexes BDA elements and connects them with accessibility issues."""

    def __init__(
        self,
        elements_data: Union[Dict[str, Any], List[Dict[str, Any]]],
        issues: Optional[List[Dict[str, Any]]] = None,
    ):
        """
        Initialize the element index.

        Args:
            elements_data: Dictionary or list containing BDA element data
            issues: List of accessibility issues to connect with elements
        """
        # Convert list to dictionary if needed
        if isinstance(elements_data, list):
            self.elements_data = {
                element["id"]: element
                for element in elements_data
                if isinstance(element, dict) and "id" in element
            }
        else:
            self.elements_data = elements_data
        self.issues = issues or []

        # Initialize index structures
        self.elements_with_issues: Dict[str, List[Dict[str, Any]]] = {}
        self.issue_types: Dict[str, List[Dict[str, Any]]] = {}
        self.elements_by_page: Dict[int, List[Dict[str, Any]]] = {}
        self.element_order: List[str] = []  # List of element IDs in document order
        self.pages_with_issues: Dict[int, List[Dict[str, Any]]] = (
            {}
        )  # Track issues by page
        self.page_remediation_status: Dict[int, Dict[str, Any]] = (
            {}
        )  # Track remediation status by page

        # Build indexes
        self._build_indexes()

    def _build_indexes(self) -> None:
        """Build all index structures from the element data and issues."""
        try:
            # Reset indexes
            self.elements_with_issues = {}
            self.issue_types = {}
            self.elements_by_page = {}
            self.element_order = []
            self.pages_with_issues = {}
            self.page_remediation_status = {}

            # First, index elements by page and build element order
            for element_id, element in self.elements_data.items():
                # Add to page index
                for page_index in element.get("page_indices", []):
                    if page_index not in self.elements_by_page:
                        self.elements_by_page[page_index] = []
                    self.elements_by_page[page_index].append(element)

                    # Initialize page remediation status
                    if page_index not in self.page_remediation_status:
                        self.page_remediation_status[page_index] = {
                            "total_elements": 0,
                            "needs_remediation": 0,
                            "remediated": 0,
                            "auto_remediated": 0,
                        }
                    self.page_remediation_status[page_index]["total_elements"] += 1

                # Add to element order
                self.element_order.append(element_id)

            # Sort elements within each page by position
            for page_index in self.elements_by_page:
                self.elements_by_page[page_index].sort(
                    key=lambda x: (
                        x.get("bounding_box", {}).get("top", 0),
                        x.get("bounding_box", {}).get("left", 0),
                    )
                )

            # Sort element order based on page and position
            self.element_order.sort(
                key=lambda x: self._get_element_sort_key(self.elements_data[x])
            )

            # Then, connect issues with elements
            if self.issues:
                self._connect_issues_with_elements()

            logger.debug(
                f"Built indexes for {len(self.elements_data)} elements and {len(self.issues)} issues"
            )

        except Exception as e:
            logger.warning(f"Error building element indexes: {e}")
            raise

    def _connect_issues_with_elements(self) -> None:
        """Connect accessibility issues with their corresponding elements."""
        for issue in self.issues:
            element_id = self._get_element_id_from_issue(issue)
            if not element_id or element_id not in self.elements_data:
                continue

            # Add issue to element's issues list
            if element_id not in self.elements_with_issues:
                self.elements_with_issues[element_id] = []
            self.elements_with_issues[element_id].append(issue)

            # Add to issue type index
            issue_type = issue.get("type", "unknown")
            if issue_type not in self.issue_types:
                self.issue_types[issue_type] = []
            self.issue_types[issue_type].append(
                {"element_id": element_id, "issue": issue}
            )

            # Update page-based indexes
            element = self.elements_data[element_id]
            for page_index in element.get("page_indices", []):
                if page_index not in self.pages_with_issues:
                    self.pages_with_issues[page_index] = []
                self.pages_with_issues[page_index].append(issue)

                # Update page remediation status
                status = issue.get("remediation_status", "needs_remediation")
                if status == "needs_remediation":
                    self.page_remediation_status[page_index]["needs_remediation"] += 1
                elif status == "remediated":
                    self.page_remediation_status[page_index]["remediated"] += 1
                elif status == "auto_remediated":
                    self.page_remediation_status[page_index]["auto_remediated"] += 1

    def get_pages_with_issues(self) -> List[int]:
        """Get list of page numbers that have accessibility issues."""
        return sorted(self.pages_with_issues.keys())

    def get_page_issues(self, page_num: int) -> List[Dict[str, Any]]:
        """Get all issues for a specific page."""
        return self.pages_with_issues.get(page_num, [])

    def get_page_elements(self, page_num: int) -> List[Dict[str, Any]]:
        """Get all elements on a specific page."""
        return self.elements_by_page.get(page_num, [])

    def get_page_remediation_status(self, page_num: int) -> Dict[str, Any]:
        """Get remediation status for a specific page."""
        return self.page_remediation_status.get(
            page_num,
            {
                "total_elements": 0,
                "needs_remediation": 0,
                "remediated": 0,
                "auto_remediated": 0,
            },
        )

    def get_next_page_with_issues(
        self, current_page: Optional[int] = None
    ) -> Optional[int]:
        """Get the next page number that has issues needing remediation."""
        pages = sorted(self.pages_with_issues.keys())
        if not pages:
            return None

        if current_page is None:
            return pages[0]

        try:
            current_index = pages.index(current_page)
            if current_index + 1 < len(pages):
                return pages[current_index + 1]
        except ValueError:
            pass

        return None

    def get_previous_page_with_issues(self, current_page: int) -> Optional[int]:
        """Get the previous page number that has issues needing remediation."""
        pages = sorted(self.pages_with_issues.keys())
        if not pages:
            return None

        try:
            current_index = pages.index(current_page)
            if current_index > 0:
                return pages[current_index - 1]
        except ValueError:
            pass

        return None

    def update_issue_status(
        self,
        element_id: str,
        issue_type: str,
        new_status: str,
        source: Optional[str] = None,
    ) -> bool:
        """
        Update the remediation status of an issue.

        Args:
            element_id: The element's unique identifier
            issue_type: Type of issue being updated
            new_status: New remediation status
            source: Source of remediation (manual, bda, None)

        Returns:
            True if status was updated successfully
        """
        if element_id not in self.elements_with_issues:
            return False

        updated = False
        element = self.elements_data[element_id]

        for issue in self.elements_with_issues[element_id]:
            if issue["type"] == issue_type:
                old_status = issue.get("remediation_status", "needs_remediation")
                issue["remediation_status"] = new_status
                issue["remediation_source"] = source
                updated = True

                # Update page remediation status
                for page_index in element.get("page_indices", []):
                    if page_index in self.page_remediation_status:
                        if old_status == "needs_remediation":
                            self.page_remediation_status[page_index][
                                "needs_remediation"
                            ] -= 1
                        elif old_status == "remediated":
                            self.page_remediation_status[page_index]["remediated"] -= 1
                        elif old_status == "auto_remediated":
                            self.page_remediation_status[page_index][
                                "auto_remediated"
                            ] -= 1

                        if new_status == "needs_remediation":
                            self.page_remediation_status[page_index][
                                "needs_remediation"
                            ] += 1
                        elif new_status == "remediated":
                            self.page_remediation_status[page_index]["remediated"] += 1
                        elif new_status == "auto_remediated":
                            self.page_remediation_status[page_index][
                                "auto_remediated"
                            ] += 1

        return updated

    def _get_element_sort_key(self, element: Dict[str, Any]) -> tuple:
        """Get a sort key for an element based on its position in the document."""
        page_indices = element.get("page_indices", [0])
        first_page = min(page_indices)
        bbox = element.get("bounding_box", {})
        return (first_page, bbox.get("top", 0), bbox.get("left", 0))

    def _get_element_id_from_issue(self, issue: Dict[str, Any]) -> Optional[str]:
        """Extract element ID from an accessibility issue."""
        # Try to find element by location first
        if "location" in issue and isinstance(issue["location"], dict):
            page_number = issue["location"].get("page_number")
            path = issue["location"].get("path")

            if page_number is not None:
                # Find elements on this page
                page_elements = [
                    element
                    for element in self.elements_data.values()
                    if page_number in element.get("page_indices", [])
                ]

                # If we have a path, try to match by position in the page
                if path and ":nth-of-type(" in path:
                    try:
                        # Extract position from path (e.g., 'div#page-0 > img:nth-of-type(2)')
                        position = int(path.split(":nth-of-type(")[-1].rstrip(")"))
                        # Get elements of the same type on this page
                        matching_elements = [
                            element
                            for element in page_elements
                            if element.get("representation", {})
                            .get("html", "")
                            .startswith("<img")
                        ]
                        # Return the element at the specified position
                        if 0 < position <= len(matching_elements):
                            return matching_elements[position - 1].get("id")
                    except (ValueError, IndexError):
                        pass

                # Try to match by context if available
                if "context" in issue and isinstance(issue["context"], str):
                    import re

                    # Extract src and alt attributes from context
                    src_match = re.search(r'src=["\'](.*?)["\']', issue["context"])
                    alt_match = re.search(r'alt=["\'](.*?)["\']', issue["context"])

                    if src_match or alt_match:
                        src = src_match.group(1) if src_match else None
                        alt = alt_match.group(1) if alt_match else None

                        # Try to find matching element
                        for element in page_elements:
                            element_html = element.get("representation", {}).get(
                                "html", ""
                            )
                            if src and src in element_html:
                                return element.get("id")
                            elif alt and alt in element_html:
                                return element.get("id")

                # If only one element on the page, use it
                if len(page_elements) == 1:
                    return page_elements[0].get("id")

                # For long-alt-text issues, try to match by alt text content or by img tag
                if issue.get("type") == "long-alt-text":
                    logger.debug(f"Processing long-alt-text issue: {issue}")
                    # If context contains the full alt text
                    if "context" in issue:
                        alt_text = issue["context"]
                        # First try direct match with alt text
                        for element in page_elements:
                            element_html = element.get("representation", {}).get(
                                "html", ""
                            )
                            if alt_text and alt_text in element_html:
                                logger.debug(
                                    f"Found element by alt text: {element.get('id')}"
                                )
                                return element.get("id")

                        # If no direct match, try to find any image element on the page
                        img_elements = [
                            element
                            for element in page_elements
                            if element.get("representation", {})
                            .get("html", "")
                            .startswith("<img")
                        ]

                        if img_elements:
                            # Use the first image element that has alt text
                            for element in img_elements:
                                element_html = element.get("representation", {}).get(
                                    "html", ""
                                )
                                if "alt=" in element_html:
                                    logger.debug(
                                        f"Using image with alt text: {element.get('id')}"
                                    )
                                    return element.get("id")

                            # If none found with alt text, use the first image
                            logger.debug(
                                f"Using first image element: {img_elements[0].get('id')}"
                            )
                            return img_elements[0].get("id")

        return None

    def get_element_by_id(self, element_id: str) -> Optional[Dict[str, Any]]:
        """Get element data by ID."""
        return self.elements_data.get(element_id)

    def get_elements_with_issues(self) -> List[Dict[str, Any]]:
        """Get all elements that have accessibility issues."""
        result = []
        for element_id, issues in self.elements_with_issues.items():
            if element_id in self.elements_data:
                element = self.elements_data[element_id].copy()
                element["accessibility_issues"] = issues
                result.append(element)
        return result

    def get_issues_by_element_id(self, element_id: str) -> List[Dict[str, Any]]:
        """Get all accessibility issues for a specific element."""
        return self.elements_with_issues.get(element_id, [])

    def get_elements_by_issue_type(self, issue_type: str) -> List[Dict[str, Any]]:
        """Get all elements that have a specific type of issue."""
        result = []
        for item in self.issue_types.get(issue_type, []):
            element_id = item["element_id"]
            if element_id in self.elements_data:
                element = self.elements_data[element_id].copy()
                element["accessibility_issues"] = [item["issue"]]
                result.append(element)
        return result

    def get_elements_in_order(self) -> List[Dict[str, Any]]:
        """Get all elements in document order (by page and position)."""
        return [
            self.elements_data[element_id]
            for element_id in self.element_order
            if element_id in self.elements_data
        ]

    def get_next_element_with_issues(
        self, current_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get the next element with issues after the current element."""
        elements_with_issues = set(self.elements_with_issues.keys())
        if not elements_with_issues:
            return None

        if current_id is None:
            # Get first element with issues
            for element_id in self.element_order:
                if element_id in elements_with_issues:
                    element = self.elements_data[element_id].copy()
                    element["accessibility_issues"] = self.elements_with_issues[
                        element_id
                    ]
                    return element
        else:
            # Find current position and get next element with issues
            try:
                current_index = self.element_order.index(current_id)
                for element_id in self.element_order[current_index + 1 :]:
                    if element_id in elements_with_issues:
                        element = self.elements_data[element_id].copy()
                        element["accessibility_issues"] = self.elements_with_issues[
                            element_id
                        ]
                        return element
            except ValueError:
                return None

        return None

    def get_previous_element_with_issues(
        self, current_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get the previous element with issues before the current element."""
        elements_with_issues = set(self.elements_with_issues.keys())
        if not elements_with_issues:
            return None

        try:
            current_index = self.element_order.index(current_id)
            for element_id in reversed(self.element_order[:current_index]):
                if element_id in elements_with_issues:
                    element = self.elements_data[element_id].copy()
                    element["accessibility_issues"] = self.elements_with_issues[
                        element_id
                    ]
                    return element
        except ValueError:
            return None

        return None

    def add_issue(self, issue: Dict[str, Any]) -> None:
        """
        Add an accessibility issue to the index.

        Args:
            issue: Dictionary containing issue information:
                - type: Issue type
                - element_id: ID of the affected element
                - description: Issue description
                - location: Optional location information
        """
        element_id = issue.get("element_id")
        if not element_id or element_id not in self.elements_data:
            logger.warning(f"Cannot add issue for unknown element ID: {element_id}")
            return

        # Add to elements_with_issues
        if element_id not in self.elements_with_issues:
            self.elements_with_issues[element_id] = []
        self.elements_with_issues[element_id].append(issue)

        # Add to issue_types
        issue_type = issue.get("type", "unknown")
        if issue_type not in self.issue_types:
            self.issue_types[issue_type] = []
        self.issue_types[issue_type].append({"element_id": element_id, "issue": issue})

        # Update page-based indexes
        element = self.elements_data[element_id]
        for page_index in element.get("page_indices", []):
            if page_index not in self.pages_with_issues:
                self.pages_with_issues[page_index] = []
            self.pages_with_issues[page_index].append(issue)

            # Update page remediation status
            if page_index in self.page_remediation_status:
                self.page_remediation_status[page_index]["needs_remediation"] += 1

    def get_element_position_info(self, element_id: str) -> Dict[str, Any]:
        """Get position information for an element."""
        try:
            index = self.element_order.index(element_id)
            total_elements = len(self.element_order)
            elements_with_issues = len(self.elements_with_issues)

            # Count elements with issues before this one
            issues_before = sum(
                1
                for eid in self.element_order[:index]
                if eid in self.elements_with_issues
            )

            # Get page information
            element = self.elements_data[element_id]
            page_indices = element.get("page_indices", [])
            current_page = min(page_indices) if page_indices else None

            return {
                "index": index,
                "total_elements": total_elements,
                "total_with_issues": elements_with_issues,
                "issues_before": issues_before,
                "issues_remaining": elements_with_issues - issues_before,
                "page_number": current_page,
                "page_status": (
                    self.get_page_remediation_status(current_page)
                    if current_page is not None
                    else None
                ),
            }
        except ValueError:
            return {}
