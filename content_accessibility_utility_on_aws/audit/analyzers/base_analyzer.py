# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Base Accessibility Analyzer.

This module provides the base class for all accessibility analyzers.
"""

from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup

from content_accessibility_utility_on_aws.audit.standards import (
    SEVERITY_LEVELS,
    get_criterion_info,
)


class BaseAnalyzer:
    """Base class for accessibility analyzers."""

    def __init__(self, soup: BeautifulSoup, options: Dict[str, Any]):
        """
        Initialize the analyzer.

        Args:
            soup: BeautifulSoup object for the HTML content
            options: Analyzer options
        """
        self.soup = soup
        self.options = options
        self.issues: List[Dict[str, Any]] = []

    def analyze(self) -> List[Dict[str, Any]]:
        """
        Perform the accessibility analysis.

        Returns:
            List of identified accessibility issues
        """
        # This method should be overridden by subclasses
        raise NotImplementedError("Subclasses must implement analyze() method")

    def _add_issue(
        self,
        issue_type: str,
        wcag_criterion: str,
        severity: str,
        element: Optional[Any] = None,
        description: Optional[str] = None,
        context: Optional[str] = None,
        location: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Add an issue to the issues list.

        Args:
            issue_type: Type of issue (e.g., 'missing-alt-text')
            wcag_criterion: WCAG criterion number (e.g., '1.1.1')
            severity: Severity level ('critical', 'major', 'minor')
            element: The HTML element with the issue
            description: Description of the issue
            context: HTML context around the issue
            location: Location information
        """
        # Skip if below severity threshold
        threshold = self.options.get("severity_threshold", "minor")
        min_severity = SEVERITY_LEVELS.get(threshold, 1)
        if SEVERITY_LEVELS.get(severity, 0) < min_severity:
            return

        # Create a unique ID for the issue
        issue_id = f"issue-{len(self.issues) + 1}"

        # Generate context if detailed option is enabled and element is provided
        if self.options.get("detailed", True) and element and context is None:
            try:
                context = str(element)[:200]  # Limit context length
                if len(str(element)) > 200:
                    context += "..."
            except AttributeError:
                context = "Could not extract context"

        # Generate element string representation
        element_str = (
            element.name if element and hasattr(element, "name") else "unknown"
        )

        # Create location info if not provided
        if location is None and element:
            location = {"path": self._get_element_path(element)}

        # Get criterion info
        criterion_info = get_criterion_info(wcag_criterion)

        # Add the issue to the list
        self.issues.append(
            {
                "id": issue_id,
                "type": issue_type,
                "wcag_criterion": wcag_criterion,
                "criterion_name": criterion_info.get("name", ""),
                "criterion_level": criterion_info.get("level", ""),
                "severity": severity,
                "element": element_str,
                "description": description
                or f"WCAG {wcag_criterion} issue: {issue_type}",
                "context": context if self.options.get("detailed", True) else None,
                "location": location,
            }
        )

    def _get_element_path(self, element):
        """
        Get the CSS selector path to an element.

        Args:
            element: The HTML element.

        Returns:
            CSS selector path.
        """
        try:
            path = []
            while element and element.name:
                if element.get("id"):
                    path.append(f"{element.name}#{element.get('id')}")
                    break
                elif element.get("class"):
                    classes = ".".join(element.get("class"))
                    path.append(f"{element.name}.{classes}")
                else:
                    siblings = element.find_previous_siblings(element.name)
                    if siblings:
                        path.append(f"{element.name}:nth-of-type({len(siblings) + 1})")
                    else:
                        path.append(element.name)
                element = element.parent
            return " > ".join(reversed(path))
        except AttributeError:
            return "Unknown path"
