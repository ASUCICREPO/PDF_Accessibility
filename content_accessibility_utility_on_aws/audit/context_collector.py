# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Context collector for accessibility issues.

This module provides functionality for collecting context information around accessibility issues.
"""


from typing import Dict, Any
from bs4 import Tag

from ..utils.logging_helper import setup_logger
# Set up module-level logger
logger = setup_logger(__name__)


class ContextCollector:
    """Class for collecting context information around an element."""

    def __init__(self, element: Tag):
        """
        Initialize the context collector.

        Args:
            element: The HTML element to collect context for.
        """
        self.element = element

    def collect(self) -> Dict[str, Any]:
        """
        Collect context information around the element.

        Returns:
            Dictionary containing context information.
        """
        context = {}

        if not self.element or not hasattr(self.element, "name"):
            return {"error": "Invalid element"}

        # Basic element info
        context["element_name"] = self.element.name
        context["attributes"] = (
            self.element.attrs if hasattr(self.element, "attrs") else {}
        )

        # Get element text content
        try:
            context["text_content"] = self.element.get_text(strip=True)
        except Exception:
            context["text_content"] = ""

        # Get parent element info
        parent = self.element.parent
        if parent and hasattr(parent, "name"):
            context["parent"] = {
                "element_name": parent.name,
                "attributes": parent.attrs if hasattr(parent, "attrs") else {},
            }

        # Get HTML snippet
        try:
            context["html_snippet"] = str(self.element)[:500]  # Limit to 500 chars
        except Exception:
            context["html_snippet"] = ""

        # Get position info
        context["position"] = self._get_position()

        return context

    def _get_position(self) -> Dict[str, Any]:
        """
        Get position information for the element.

        Returns:
            Dictionary containing position information.
        """
        position = {}

        try:
            # Find all elements of the same type
            if self.element.name:
                all_elements = self.element.find_all_previous(self.element.name) + [
                    self.element
                ]
                position["index"] = len(all_elements) - 1
                position["total"] = len(all_elements) + len(
                    self.element.find_all_next(self.element.name)
                )
        except Exception:
            position["index"] = -1
            position["total"] = -1

        return position
