# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
BDA Element Parser module.

This module provides functionality for parsing and organizing elements from BDA result data.
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from bs4 import BeautifulSoup
from content_accessibility_utility_on_aws.utils.logging_helper import setup_logger

# Set up module-level logger
logger = setup_logger(__name__)


class BDAElementParser:
    """Parser for BDA result data that extracts and organizes elements."""

    def __init__(
        self,
        result_json_path: Optional[str] = None,
        result_data: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the BDA element parser.

        Args:
            result_json_path: Path to the BDA result.json file
            result_data: Direct BDA result data as dictionary
        """
        self.result_json_path = result_json_path
        self.result_data = result_data
        self.elements_by_id: Dict[str, Dict[str, Any]] = {}
        self.elements_by_page: Dict[int, List[Dict[str, Any]]] = {}
        self.elements_by_type: Dict[str, List[Dict[str, Any]]] = {}
        self.auto_remediated_elements: Dict[str, Dict[str, Any]] = (
            {}
        )  # Track BDA auto-remediated elements

        # Load data if provided
        if result_json_path:
            self.load_from_file(result_json_path)
        elif result_data:
            self.load_from_data(result_data)

    def load_from_file(self, file_path: str) -> bool:
        """
        Load and parse BDA result data from a file.

        Args:
            file_path: Path to the result.json file

        Returns:
            True if loading was successful, False otherwise
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                self.result_data = json.load(f)
            return self.parse_result()
        except Exception as e:
            logger.error(f"Error loading BDA result file: {e}")
            return False

    def load_from_data(self, data: Dict[str, Any]) -> bool:
        """
        Load and parse BDA result data from a dictionary.

        Args:
            data: BDA result data dictionary

        Returns:
            True if loading was successful, False otherwise
        """
        try:
            self.result_data = data
            return self.parse_result()
        except Exception as e:
            logger.error(f"Error loading BDA result data: {e}")
            return False

    def parse_result(self) -> bool:
        """
        Parse the loaded BDA result data and organize elements.

        Returns:
            True if parsing was successful, False otherwise
        """
        if not self.result_data:
            logger.error("No result data available to parse")
            return False

        try:
            # Reset collections
            self.elements_by_id = {}
            self.elements_by_page = {}
            self.elements_by_type = {}
            self.auto_remediated_elements = {}

            # Process pages from BDA result
            if isinstance(self.result_data, dict) and "pages" in self.result_data:
                for page in self.result_data["pages"]:
                    # Create an element for the page
                    page_element = {
                        "id": page.get("id"),
                        "page_index": page.get("page_index"),
                        "representation": page.get("representation", {}),
                        "type": "PAGE",
                        "page_indices": [page.get("page_index")],
                    }
                    self._process_element(page_element)
                    self._process_page(page)

                    # Extract img elements from the page HTML
                    if "representation" in page and "html" in page["representation"]:
                        soup = BeautifulSoup(
                            page["representation"]["html"], "html.parser"
                        )
                        img_tags = soup.find_all("img")
                        for img in img_tags:
                            img_element = {
                                "id": f"{page['id']}-img-{hash(str(img))}",
                                "page_index": page.get("page_index"),
                                "representation": {"html": str(img)},
                                "type": "IMAGE",
                                "page_indices": [page.get("page_index")],
                            }
                            self._process_element(img_element)

            logger.debug(f"Successfully parsed {len(self.elements_by_id)} elements")
            return True

        except Exception as e:
            logger.error(f"Error parsing BDA result data: {e}")
            return False

    def _process_element(self, element: Dict[str, Any]) -> None:
        """
        Process a single element from the BDA result.

        Args:
            element: Element data dictionary
        """
        element_id = element.get("id")
        if not element_id:
            return

        # Process HTML representation if present
        if "representation" in element and "html" in element["representation"]:
            html = element["representation"]["html"]
            soup = BeautifulSoup(html, "html.parser")

            # Process img tags
            img_tags = soup.find_all("img")
            for img in img_tags:
                # Set bda-data-id
                img["bda-data-id"] = element_id
                img["data-bda-id"] = element_id  # Add both formats for compatibility

                # Check for BDA-generated alt text
                if img.get("alt") and not img.get("data-bda-generated-alt"):
                    img["data-bda-generated-alt"] = "true"
                    # Track as auto-remediated
                    self.auto_remediated_elements[element_id] = {
                        "element": element,
                        "remediation_type": "alt_text",
                        "remediation_date": datetime.utcnow().isoformat(),
                        "original_value": "",
                        "new_value": img["alt"],
                    }

            # Update the HTML representation
            element["representation"]["html"] = str(soup)

            # Add data-bda-id to the root element if it doesn't have one
            root_element = soup.find()
            if root_element and not root_element.get("data-bda-id"):
                root_element["data-bda-id"] = element_id
                element["representation"]["html"] = str(soup)

        # Store by ID
        self.elements_by_id[element_id] = element

        # Store by type
        element_type = element.get("type", "UNKNOWN")
        if element_type not in self.elements_by_type:
            self.elements_by_type[element_type] = []
        self.elements_by_type[element_type].append(element)

        # Store by page
        page_indices = element.get("page_indices", [])
        for page_index in page_indices:
            if page_index not in self.elements_by_page:
                self.elements_by_page[page_index] = []
            self.elements_by_page[page_index].append(element)

    def _process_page(self, page: Dict[str, Any]) -> None:
        """
        Process a page from the BDA result for additional context.

        Args:
            page: Page data dictionary
        """
        page_index = page.get("page_index")
        if page_index is None:
            return

        # Store page-specific data that might be useful for remediation
        if "representation" in page and "html" in page["representation"]:
            # Process page HTML and add to elements on this page for context
            if page_index in self.elements_by_page:
                page_html = page["representation"]["html"]

                # Process any img tags in the page HTML
                soup = BeautifulSoup(page_html, "html.parser")
                img_tags = soup.find_all("img")
                if img_tags:
                    # Set bda-data-id on all img tags using the containing element's ID
                    for img in img_tags:
                        # Find the closest ancestor that has either data-bda-id or bda-data-id
                        parent = img.find_parent(
                            attrs={"data-bda-id": True}
                        ) or img.find_parent(attrs={"bda-data-id": True})
                        if parent:
                            element_id = parent.get("data-bda-id") or parent.get(
                                "bda-data-id"
                            )
                            img["bda-data-id"] = element_id
                            img["data-bda-id"] = element_id

                            # Check for BDA-generated alt text
                            if img.get("alt") and not img.get("data-bda-generated-alt"):
                                img["data-bda-generated-alt"] = "true"
                                # Track as auto-remediated
                                self.auto_remediated_elements[element_id] = {
                                    "element": self.elements_by_id.get(element_id),
                                    "remediation_type": "alt_text",
                                    "remediation_date": datetime.utcnow().isoformat(),
                                    "original_value": "",
                                    "new_value": img["alt"],
                                }

                    page_html = str(soup)

                # Add processed HTML to elements
                for element in self.elements_by_page[page_index]:
                    if "page_context" not in element:
                        element["page_context"] = {}
                    element["page_context"][page_index] = {"html": page_html}

    def get_element_by_id(self, element_id: str) -> Optional[Dict[str, Any]]:
        """Get element data by ID."""
        return self.elements_by_id.get(element_id)

    def get_elements_by_page(self, page_index: int) -> List[Dict[str, Any]]:
        """Get all elements on a specific page."""
        return self.elements_by_page.get(page_index, [])

    def get_elements_by_type(self, element_type: str) -> List[Dict[str, Any]]:
        """Get all elements of a specific type."""
        return self.elements_by_type.get(element_type, [])

    def get_all_elements(self) -> List[Dict[str, Any]]:
        """Get all parsed elements."""
        return list(self.elements_by_id.values())

    def get_auto_remediated_elements(self) -> Dict[str, Dict[str, Any]]:
        """Get all elements that were auto-remediated by BDA."""
        return self.auto_remediated_elements

    def get_element_context(self, element_id: str) -> Dict[str, Any]:
        """
        Get context information for a specific element.

        Args:
            element_id: The element's unique identifier

        Returns:
            Dictionary containing context information including associated captions for figures
        """
        element = self.get_element_by_id(element_id)
        if not element:
            return {}

        context = {
            "element": element,
            "pages": [],
            "surrounding_elements": [],
            "associated_elements": [],
            "auto_remediated": element_id in self.auto_remediated_elements,
            "remediation_info": self.auto_remediated_elements.get(element_id),
        }

        # For figures, try to find associated caption
        if element.get("type") == "FIGURE":
            caption = self._find_associated_caption(element)
            if caption:
                context["associated_elements"].append(
                    {"type": "caption", "element": caption}
                )

        # Add page context
        for page_index in element.get("page_indices", []):
            if page_index in self.elements_by_page:
                page_elements = self.elements_by_page[page_index]
                try:
                    element_index = page_elements.index(element)
                    # Get surrounding elements
                    start = max(0, element_index - 2)
                    end = min(len(page_elements), element_index + 3)
                    context["surrounding_elements"].extend(page_elements[start:end])
                except ValueError:
                    pass

                # Add page context if available
                if "page_context" in element and page_index in element["page_context"]:
                    context["pages"].append(
                        {
                            "index": page_index,
                            "html": element["page_context"][page_index]["html"],
                        }
                    )

        return context

    def _find_associated_caption(
        self, figure_element: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Find the caption associated with a figure element.

        Args:
            figure_element: The figure element data

        Returns:
            Associated caption element if found, None otherwise
        """
        # Get all text elements on the same page
        page_indices = figure_element.get("page_indices", [])
        if not page_indices:
            return None

        page_index = page_indices[0]  # Use first page if multiple
        page_elements = self.get_elements_by_page(page_index)

        # Find text elements that appear after the figure
        text_elements = [
            e
            for e in page_elements
            if e.get("type") == "TEXT"
            and e.get("reading_order", 0) > figure_element.get("reading_order", 0)
        ]

        # Look for the first text element that contains "Figure" and appears immediately after
        for text_element in text_elements:
            html = text_element.get("representation", {}).get("html", "")
            if "Figure" in html:
                return text_element

        return None
