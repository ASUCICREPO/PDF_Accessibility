# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Remediation Manager module.

This module provides functionality for managing the remediation process
using BDA element data and accessibility issues.
"""

import os
import re
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup

from content_accessibility_utility_on_aws.utils.logging_helper import setup_logger
from content_accessibility_utility_on_aws.remediate.helpers.html_updater import HTMLUpdater
from .element_index import ElementIndex

# Set up module-level logger
logger = setup_logger(__name__)


class RemediationManager:
    """Manages the remediation process for accessibility issues."""

    def __init__(self, element_index: ElementIndex, html_updater: HTMLUpdater):
        """
        Initialize the remediation manager.

        Args:
            element_index: Index of BDA elements and issues
            html_updater: HTML updater instance for applying fixes
        """
        self.element_index = element_index
        self.html_updater = html_updater
        self.current_element_id: Optional[str] = None
        self.current_page: Optional[int] = None
        self.remediation_history: List[Dict[str, Any]] = []

    def start_remediation(self) -> Optional[Dict[str, Any]]:
        """
        Start the remediation process from the first element with issues.

        Returns:
            Dictionary containing the first element's context if found, None otherwise
        """
        # Get first element with issues
        first_element = self.element_index.get_next_element_with_issues()
        if not first_element:
            return None

        # Set as current element
        self.current_element_id = first_element["id"]

        # Get page number from element
        page_indices = first_element.get("page_indices", [])
        if page_indices:
            self.current_page = min(page_indices)

        return self.get_current_element_context()

    def start_page_remediation(
        self, page_num: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Start remediation process for a specific page or first page with issues.

        Args:
            page_num: Optional page number to start with

        Returns:
            Page context dictionary if successful, None otherwise
        """
        if page_num is None:
            pages_with_issues = self.element_index.get_pages_with_issues()
            if not pages_with_issues:
                return None
            page_num = pages_with_issues[0]

        self.current_page = page_num

        # Get elements with issues on this page
        elements = self.element_index.get_page_elements(page_num)
        self.element_index.get_page_issues(page_num)

        # Find first element with issues
        for element in elements:
            element_id = element.get("id")
            if element_id and self.element_index.get_issues_by_element_id(element_id):
                self.current_element_id = element_id
                break

        return self.get_page_context()

    def get_page_context(self) -> Optional[Dict[str, Any]]:
        """
        Get context information for the current page.

        Returns:
            Dictionary containing page data and context
        """
        if self.current_page is None:
            logger.debug("No current page is set, returning None")
            return None

        logger.debug("Getting context for page %s" % self.current_page)

        try:
            # Get elements for the current page
            elements = self.element_index.get_page_elements(self.current_page)
            logger.debug("Found %d elements on page %s" % (len(elements), self.current_page))

            # Get issues for the current page
            issues = self.element_index.get_page_issues(self.current_page)
            logger.debug("Found %d issues on page %s" % (len(issues), self.current_page))

            # Get remediation status for the page
            status = self.element_index.get_page_remediation_status(self.current_page)

            # Get current element context if available
            current_element_context = None
            if self.current_element_id:
                current_element_context = self.get_current_element_context()

            return {
                "page_number": self.current_page,
                "elements": elements,
                "issues": issues,
                "status": status,
                "remediation_history": self._get_page_history(self.current_page),
                "current_element": current_element_context,
                "current_element_id": self.current_element_id,
            }

        except Exception as e:
            logger.error("Error getting page context: %s" % e)
            return None

    def move_to_next_page(self) -> Optional[Dict[str, Any]]:
        """
        Move to the next page that needs remediation.

        Returns:
            Next page context or None if no more pages
        """
        if self.current_page is None:
            return self.start_page_remediation()

        next_page = self.element_index.get_next_page_with_issues(self.current_page)
        if next_page is not None:
            self.current_page = next_page

            # Reset current element ID
            self.current_element_id = None

            # Find first element with issues on the new page
            elements = self.element_index.get_page_elements(next_page)
            for element in elements:
                element_id = element.get("id")
                if element_id and self.element_index.get_issues_by_element_id(
                    element_id
                ):
                    self.current_element_id = element_id
                    break

            return self.get_page_context()
        return None

    def move_to_previous_page(self) -> Optional[Dict[str, Any]]:
        """
        Move to the previous page that was remediated.

        Returns:
            Previous page context or None if at the start
        """
        if self.current_page is None:
            return None

        prev_page = self.element_index.get_previous_page_with_issues(self.current_page)
        if prev_page is not None:
            self.current_page = prev_page

            # Reset current element ID
            self.current_element_id = None

            # Find first element with issues on the previous page
            elements = self.element_index.get_page_elements(prev_page)
            for element in elements:
                element_id = element.get("id")
                if element_id and self.element_index.get_issues_by_element_id(
                    element_id
                ):
                    self.current_element_id = element_id
                    break

            return self.get_page_context()
        return None

    def get_current_element_context(self) -> Optional[Dict[str, Any]]:
        """
        Get the current element and its context information.

        Returns:
            Dictionary containing element data and context
        """
        if not self.current_element_id:
            return None

        element = self.element_index.get_element_by_id(self.current_element_id)
        if not element:
            return None

        # Get position information
        position_info = self.element_index.get_element_position_info(
            self.current_element_id
        )

        # Get issues for this element
        issues = self.element_index.get_issues_by_element_id(self.current_element_id)

        # Get element context
        context = {
            "element": element,
            "issues": issues,
            "position": position_info,
            "original_html": element.get("representation", {}).get("html", ""),
            "page_context": element.get("page_context", {}),
            "remediation_history": self._get_element_history(self.current_element_id),
        }

        return context

    def apply_fix(
        self, fix_data: Dict[str, Any], issue: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Apply a remediation fix to the current element.

        Args:
            fix_data: Dictionary containing fix information:
                - type: Type of fix (attribute_update, content_update, etc.)
                - value: New value to apply
                - attribute: Attribute name for attribute updates
                - structure: Optional structure updates for figures
            issue: Optional accessibility issue data for better element location

        Returns:
            True if fix was applied successfully, False otherwise
        """
        if not self.current_element_id:
            logger.error("No current element selected for remediation")
            return False

        try:
            element = self.element_index.get_element_by_id(self.current_element_id)
            if not element:
                logger.error("Element not found: %s" % self.current_element_id)
                return False

            # Log important details for debugging
            logger.debug(
                "Applying fix for element %s - Fix type: %s" 
                % (self.current_element_id, fix_data.get('type'))
            )
            logger.debug(
                "Element data: %s, Page: %s" 
                % (element.get('type'), self.current_page)
            )

            # Get original HTML from BDA data
            original_html = element.get("representation", {}).get("html", "")
            if not original_html:
                logger.error(
                    "No HTML representation for element %s" 
                    % self.current_element_id
                )
                return False

            # Get location information from issue if available
            location = issue.get("location") if issue else None

            # Special handling for long-alt-text issues
            if (
                issue
                and issue.get("type") == "long-alt-text"
                and fix_data.get("type") == "attribute_update"
            ):
                logger.debug(
                    "Processing long-alt-text fix: %s..." 
                    % fix_data.get('value')[:50]
                )
                return self._apply_attribute_fix(original_html, fix_data, location)

            # Apply fix based on type
            success = False
            if fix_data["type"] == "attribute_update":
                logger.debug(
                    "Applying attribute update for %s = %s" 
                    % (fix_data.get('attribute'), fix_data.get('value'))
                )
                success = self._apply_attribute_fix(original_html, fix_data, location)
            elif fix_data["type"] == "content_update":
                logger.debug(
                    "Applying content update with %d characters" 
                    % len(fix_data.get('content', ''))
                )
                success = self._apply_content_fix(original_html, fix_data, location)
            elif fix_data["type"] == "replace_html":
                logger.debug(
                    "Applying HTML replacement with %d characters" 
                    % len(fix_data.get('html', ''))
                )
                success = self._apply_html_replacement(
                    original_html, fix_data, location
                )
            elif fix_data["type"] == "figure_structure":
                logger.debug("Applying figure structure fix")
                success = self._apply_figure_structure_fix(element, fix_data, location)
            else:
                logger.error("Unknown fix type: %s" % fix_data['type'])
                return False

            if success:
                # Record the fix in history
                self._record_fix(fix_data)
                # Update issue status using the fix's element ID if provided
                element_id = fix_data.get("element_id", self.current_element_id)
                issue_type = fix_data.get("issue_type", "unknown")

                # Update issue status
                self.element_index.update_issue_status(
                    element_id, issue_type, "remediated", "manual"
                )

                logger.debug(
                    "✅ Successfully applied %s fix for element %s" 
                    % (fix_data['type'], self.current_element_id)
                )
                return True
            else:
                logger.warning(
                    "❌ Failed to apply %s fix for element %s" 
                    % (fix_data['type'], self.current_element_id)
                )
                return False

        except Exception as e:
            logger.error("Error applying fix: %s" % str(e), exc_info=True)
            return False

    def _apply_attribute_fix(
        self,
        original_html: str,
        fix_data: Dict[str, Any],
        location: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Apply an attribute update fix."""
        try:
            # Import BeautifulSoup here to ensure it's available in this method's scope
            from bs4 import BeautifulSoup

            # Parse the original HTML
            soup = BeautifulSoup(original_html, "html.parser")
            element = soup.find()  # Get the first element

            if not element:
                logger.warning("No element found in original HTML")
                return False

            # Update the attribute
            element[fix_data["attribute"]] = fix_data["value"]

            # Apply fix using enhanced element selection
            element_id = fix_data.get("element_id", self.current_element_id)

            # For long-alt-text issues, use more aggressive matching
            is_long_alt_fix = (
                fix_data.get("issue_type") == "long-alt-text"
                and fix_data["attribute"] == "alt"
            )

            # Try with BDA ID first
            success = self.html_updater.apply_fix(
                selector=f'[data-bda-id="{element_id}"]',
                attribute_updates={fix_data["attribute"]: fix_data["value"]},
                element_html=original_html,
                location=location,
            )

            # If that fails, try with bda-data-id (alternate format)
            if not success:
                success = self.html_updater.apply_fix(
                    selector=f'[bda-data-id="{element_id}"]',
                    attribute_updates={fix_data["attribute"]: fix_data["value"]},
                    element_html=original_html,
                    location=location,
                )

            # If that fails, try with just location info
            if not success and location:
                success = self.html_updater.apply_fix(
                    attribute_updates={fix_data["attribute"]: fix_data["value"]},
                    element_html=original_html,
                    location=location,
                )

            # Special handling for long-alt-text issues - try direct image selection
            if not success and is_long_alt_fix:
                # First try by path in location if available
                if location and "path" in location:
                    success = self.html_updater.apply_fix(
                        selector=location["path"],
                        attribute_updates={fix_data["attribute"]: fix_data["value"]},
                        element_html=original_html,
                    )

                # If that fails, try finding all images on the page and selecting by partial alt match
                if not success:
                    logger.debug("Trying to find image by existing alt text pattern")

                    # Extract current alt text from original HTML
                    from bs4 import BeautifulSoup

                    orig_soup = BeautifulSoup(original_html, "html.parser")
                    orig_img = orig_soup.find("img")

                    if (
                        orig_img
                        and orig_img.has_attr("alt")
                        and len(orig_img["alt"]) > 20
                    ):
                        # Find images with alt text containing at least part of the original
                        alt_pattern = orig_img["alt"][
                            :20
                        ]  # First 20 chars should be distinctive enough

                        # Try to apply fix to all img elements with matching alt pattern
                        global_selector = f'img[alt*="{alt_pattern}"]'
                        logger.debug(
                            "Trying global selector for partial alt match: %s"
                            % global_selector
                        )

                        success = self.html_updater.apply_fix(
                            selector=global_selector,
                            attribute_updates={
                                fix_data["attribute"]: fix_data["value"]
                            },
                        )

                # Last resort: find all images and try the first one with similar length alt text
                if not success:
                    logger.debug("Trying to find any image with long alt text")
                    soup = BeautifulSoup(
                        self.html_updater.get_html_content(), "html.parser"
                    )
                    images = soup.find_all("img")

                    # Look for images with long alt text (characteristic of long-alt-text issues)
                    long_alt_images = [
                        img
                        for img in images
                        if img.has_attr("alt") and len(img["alt"]) > 125
                    ]

                    if long_alt_images:
                        # Try the first one
                        img_to_fix = long_alt_images[0]
                        success = self.html_updater.apply_fix(
                            selector=f'img[src="{img_to_fix["src"]}"]',
                            attribute_updates={
                                fix_data["attribute"]: fix_data["value"]
                            },
                        )

            # Last resort for any type: try using direct image selection if this is an alt text update
            if (
                not success
                and fix_data["attribute"] == "alt"
                and location
                and "context" in location
            ):
                # Try to extract image src from context
                src_match = re.search(r'src=["\'](.*?)["\']', location["context"])
                if src_match:
                    img_src = src_match.group(1)
                    success = self.html_updater.apply_fix(
                        selector=f'img[src*="{os.path.basename(img_src)}"]',
                        attribute_updates={fix_data["attribute"]: fix_data["value"]},
                        element_html=original_html,
                        location=location,
                    )

            return success
        except Exception as e:
            logger.error("Error applying attribute fix: %s" % e, exc_info=True)
            return False

    def _apply_content_fix(
        self,
        original_html: str,
        fix_data: Dict[str, Any],
        location: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Apply a content update fix."""
        try:
            # Parse the content to check for img tags
            soup = BeautifulSoup(fix_data["content"], "html.parser")
            img_tags = soup.find_all("img")

            # Set both BDA ID formats on all img tags found
            element_id = fix_data.get("element_id", self.current_element_id)
            for img_tag in img_tags:
                img_tag["bda-data-id"] = element_id
                img_tag["data-bda-id"] = element_id

            # Update the content with the modified img tags
            fix_data["content"] = str(soup)

            # Try with BDA ID first
            success = self.html_updater.apply_fix(
                selector=f'[data-bda-id="{element_id}"]',
                content_updates=fix_data["content"],
                element_html=original_html,
                location=location,
            )

            # If that fails, try with just location info
            if not success and location:
                success = self.html_updater.apply_fix(
                    content_updates=fix_data["content"],
                    element_html=original_html,
                    location=location,
                )

            return success
        except Exception as e:
            logger.error("Error applying content fix: %s" % e)
            return False

    def _apply_html_replacement(
        self,
        original_html: str,
        fix_data: Dict[str, Any],
        location: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Apply a complete HTML replacement fix."""
        try:
            # Parse the HTML content to check for img tags
            soup = BeautifulSoup(fix_data["html"], "html.parser")
            img_tags = soup.find_all("img")

            # Set both BDA ID formats on all img tags found
            element_id = fix_data.get("element_id", self.current_element_id)
            for img_tag in img_tags:
                img_tag["bda-data-id"] = element_id
                img_tag["data-bda-id"] = element_id

            # Update the HTML content with the modified img tags
            fix_data["html"] = str(soup)

            # Create new element structure
            new_element = {
                "tag": soup.find().name,  # Get tag name from first element
                "attributes": {},
                "content": fix_data["html"],
            }

            # Try with BDA ID first
            success = self.html_updater.apply_fix(
                selector=f'[data-bda-id="{element_id}"]',
                new_element=new_element,
                replace_element=True,
                element_html=original_html,
                location=location,
            )

            # If that fails, try with just location info
            if not success and location:
                success = self.html_updater.apply_fix(
                    new_element=new_element,
                    replace_element=True,
                    element_html=original_html,
                    location=location,
                )

            return success
        except Exception as e:
            logger.error("Error applying HTML replacement: %s" % e)
            return False

    def _apply_figure_structure_fix(
        self,
        element: Dict[str, Any],
        fix_data: Dict[str, Any],
        location: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Apply structural fixes for figures."""
        try:
            # Get original HTML
            original_html = element.get("representation", {}).get("html", "")
            if not original_html:
                return False

            # Parse the HTML
            soup = BeautifulSoup(original_html, "html.parser")
            img = soup.find("img")
            if not img:
                return False

            # Create figure structure
            figure = soup.new_tag("figure")
            img.wrap(figure)

            # Find all img tags in the figure
            img_tags = soup.find_all("img")
            element_id = fix_data.get("element_id", self.current_element_id)
            for img in img_tags:
                # Update alt text if provided and set both BDA ID formats
                if "alt_text" in fix_data:
                    img["alt"] = fix_data["alt_text"]
                img["bda-data-id"] = element_id
                img["data-bda-id"] = element_id

            # Add figcaption if caption text is provided
            if "caption_text" in fix_data:
                figcaption = soup.new_tag("figcaption")
                figcaption.string = fix_data["caption_text"]
                figure.append(figcaption)

            # Create new element structure
            new_element = {
                "tag": "figure",
                "attributes": {},
                "content": (
                    str(figure.decode()) if hasattr(figure, "decode") else str(figure)
                ),
            }

            # Try with BDA ID first
            success = self.html_updater.apply_fix(
                selector=f'[data-bda-id="{element_id}"]',
                new_element=new_element,
                replace_element=True,
                element_html=original_html,
                location=location,
            )

            # If that fails, try with just location info
            if not success and location:
                success = self.html_updater.apply_fix(
                    new_element=new_element,
                    replace_element=True,
                    element_html=original_html,
                    location=location,
                )

            return success

        except Exception as e:
            logger.error("Error applying figure structure fix: %s" % e)
            return False

    def _record_fix(self, fix_data: Dict[str, Any]) -> None:
        """Record a fix in the remediation history."""
        if self.current_element_id:
            self.remediation_history.append(
                {
                    "element_id": self.current_element_id,
                    "page_number": self.current_page,
                    "timestamp": self.html_updater.get_timestamp(),
                    "fix": fix_data,
                }
            )

    def _get_element_history(self, element_id: str) -> List[Dict[str, Any]]:
        """Get remediation history for a specific element."""
        return [
            entry
            for entry in self.remediation_history
            if entry["element_id"] == element_id
        ]

    def _get_page_history(self, page_num: int) -> List[Dict[str, Any]]:
        """Get remediation history for a specific page."""
        return [
            entry
            for entry in self.remediation_history
            if entry["page_number"] == page_num
        ]

    def get_remediation_status(self) -> Dict[str, Any]:
        """Get the current status of the remediation process."""
        total_elements = len(self.element_index.get_elements_with_issues())
        fixed_elements = len(
            set(entry["element_id"] for entry in self.remediation_history)
        )

        # Get page-specific status
        page_status = None
        if self.current_page is not None:
            page_status = self.element_index.get_page_remediation_status(
                self.current_page
            )

        return {
            "total_elements": total_elements,
            "fixed_elements": fixed_elements,
            "remaining_elements": total_elements - fixed_elements,
            "current_element": self.current_element_id,
            "current_page": self.current_page,
            "page_status": page_status,
            "fixes_applied": len(self.remediation_history),
        }

    def move_to_next_element(self) -> Optional[Dict[str, Any]]:
        """
        Move to the next element with issues.

        Returns:
            Dictionary containing the next element's context if found, None otherwise
        """
        if not self.current_element_id:
            return None

        # Get next element with issues
        next_element = self.element_index.get_next_element_with_issues(
            self.current_element_id
        )
        if not next_element:
            return None

        # Update current element
        self.current_element_id = next_element["id"]

        # Update current page if needed
        page_indices = next_element.get("page_indices", [])
        if page_indices:
            self.current_page = min(page_indices)

        return self.get_current_element_context()

    def get_element_fixes(self, element_id: str) -> List[Dict[str, Any]]:
        """Get all fixes applied to a specific element."""
        return [
            entry["fix"]
            for entry in self.remediation_history
            if entry["element_id"] == element_id
        ]

    def undo_last_fix(self) -> Optional[Dict[str, Any]]:
        """
        Undo the last fix applied to the current element.

        Returns:
            Updated element context or None if no fixes to undo
        """
        if not self.current_element_id:
            return None

        # Get fixes for current element in reverse order
        element_fixes = self._get_element_history(self.current_element_id)
        if not element_fixes:
            return None

        # Remove the last fix from history
        last_fix = element_fixes[-1]
        self.remediation_history.remove(last_fix)

        # Get original element HTML from BDA data
        element = self.element_index.get_element_by_id(self.current_element_id)
        if element and "representation" in element:
            # Reapply all fixes except the last one
            for fix in element_fixes[:-1]:
                self.apply_fix(fix["fix"])

            # Update issue status back to needs_remediation
            self.element_index.update_issue_status(
                self.current_element_id,
                last_fix["fix"].get("issue_type", "unknown"),
                "needs_remediation",
                None,
            )

            return self.get_current_element_context()

        return None
