# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
HTML Accessibility Issue Types.

This module defines the types of accessibility issues that can be detected and remediated.
"""

# Issue type definitions with their associated WCAG criteria and severity levels
ISSUE_TYPES = {
    # Content Alternatives
    "missing-alt-text": {
        "wcag": "1.1.1",
        "severity": "critical",
        "description": "Image missing alternative text",
        "remediation_type": "attribute",
        "element_types": ["img"],
    },
    "generic-alt-text": {
        "wcag": "1.1.1",
        "severity": "major",
        "description": "Image has generic or uninformative alternative text",
        "remediation_type": "attribute",
        "element_types": ["img"],
    },
    "decorative-image-with-alt": {
        "wcag": "1.1.1",
        "severity": "minor",
        "description": "Decorative image should have empty alt text",
        "remediation_type": "attribute",
        "element_types": ["img"],
    },
    # Document Structure
    "improper-heading-structure": {
        "wcag": "1.3.1",
        "severity": "major",
        "description": "Improper heading level structure (skipped levels)",
        "remediation_type": "structure",
        "element_types": ["h1", "h2", "h3", "h4", "h5", "h6"],
    },
    "missing-document-language": {
        "wcag": "3.1.1",
        "severity": "critical",
        "description": "Document language not specified",
        "remediation_type": "attribute",
        "element_types": ["html"],
    },
    "missing-page-title": {
        "wcag": "2.4.2",
        "severity": "major",
        "description": "Page missing title element",
        "remediation_type": "element",
        "element_types": ["title"],
    },
    "missing-main-landmark": {
        "wcag": "1.3.1",
        "severity": "major",
        "description": "No main landmark role identified",
        "remediation_type": "attribute",
        "element_types": ["main", '[role="main"]'],
    },
    # Tables
    "missing-table-headers": {
        "wcag": "1.3.1",
        "severity": "critical",
        "description": "Table missing header cells",
        "remediation_type": "structure",
        "element_types": ["table"],
    },
    "missing-header-scope": {
        "wcag": "1.3.1",
        "severity": "major",
        "description": "Table headers missing scope attribute",
        "remediation_type": "attribute",
        "element_types": ["th"],
    },
    "complex-table-no-ids": {
        "wcag": "1.3.1",
        "severity": "critical",
        "description": "Complex table missing header IDs and data cell headers",
        "remediation_type": "attribute",
        "element_types": ["table"],
    },
    # Forms
    "missing-form-label": {
        "wcag": "3.3.2",
        "severity": "critical",
        "description": "Form control missing label",
        "remediation_type": "structure",
        "element_types": ["input", "select", "textarea"],
    },
    "missing-fieldset-legend": {
        "wcag": "1.3.1",
        "severity": "major",
        "description": "Group of form controls missing fieldset/legend",
        "remediation_type": "structure",
        "element_types": ['input[type="radio"]', 'input[type="checkbox"]'],
    },
    "missing-aria-required": {
        "wcag": "3.3.2",
        "severity": "minor",
        "description": "Required form field missing aria-required",
        "remediation_type": "attribute",
        "element_types": ["input", "select", "textarea"],
    },
    # Links and Navigation
    "empty-link": {
        "wcag": "2.4.4",
        "severity": "critical",
        "description": "Link has no text content",
        "remediation_type": "content",
        "element_types": ["a"],
    },
    "generic-link-text": {
        "wcag": "2.4.4",
        "severity": "major",
        "description": 'Link text is generic (e.g., "click here")',
        "remediation_type": "content",
        "element_types": ["a"],
    },
    "missing-skip-link": {
        "wcag": "2.4.1",
        "severity": "major",
        "description": "No skip navigation link found",
        "remediation_type": "element",
        "element_types": ["a"],
    },
    # Interactive Elements
    "missing-button-role": {
        "wcag": "4.1.2",
        "severity": "major",
        "description": "Interactive element missing button role",
        "remediation_type": "attribute",
        "element_types": ["div", "span"],
    },
    "missing-aria-expanded": {
        "wcag": "4.1.2",
        "severity": "major",
        "description": "Expandable element missing aria-expanded state",
        "remediation_type": "attribute",
        "element_types": ["button", '[role="button"]'],
    },
    "missing-focus-indicator": {
        "wcag": "2.4.7",
        "severity": "major",
        "description": "Interactive element missing visible focus indicator",
        "remediation_type": "style",
        "element_types": ["a", "button", "input", "select", "textarea"],
    },
    # Media
    "missing-video-captions": {
        "wcag": "1.2.2",
        "severity": "critical",
        "description": "Video missing closed captions",
        "remediation_type": "element",
        "element_types": ["video"],
    },
    "missing-audio-transcript": {
        "wcag": "1.2.1",
        "severity": "critical",
        "description": "Audio missing transcript",
        "remediation_type": "content",
        "element_types": ["audio"],
    },
    "missing-media-controls": {
        "wcag": "2.1.1",
        "severity": "critical",
        "description": "Media missing keyboard-accessible controls",
        "remediation_type": "attribute",
        "element_types": ["video", "audio"],
    },
    # Color and Contrast
    "insufficient-color-contrast": {
        "wcag": "1.4.3",
        "severity": "major",
        "description": "Text has insufficient color contrast",
        "remediation_type": "style",
        "element_types": ["*"],
    },
    "color-only-indication": {
        "wcag": "1.4.1",
        "severity": "major",
        "description": "Information conveyed by color alone",
        "remediation_type": "content",
        "element_types": ["*"],
    },
}


def get_issue_info(issue_type):
    """
    Get information about a specific issue type.

    Args:
        issue_type: The type of accessibility issue

    Returns:
        Dictionary with issue information, or empty dict if not found.
    """
    return ISSUE_TYPES.get(issue_type, {})


def get_issues_by_wcag(criterion):
    """
    Get all issue types associated with a WCAG criterion.

    Args:
        criterion: The WCAG criterion ID (e.g., '1.1.1')

    Returns:
        List of issue types associated with the criterion.
    """
    return [
        issue_type
        for issue_type, info in ISSUE_TYPES.items()
        if info.get("wcag") == criterion
    ]


def get_issues_by_severity(severity):
    """
    Get all issue types of a specific severity level.

    Args:
        severity: The severity level ('critical', 'major', 'minor')

    Returns:
        List of issue types with the specified severity.
    """
    return [
        issue_type
        for issue_type, info in ISSUE_TYPES.items()
        if info.get("severity") == severity
    ]


def get_issues_by_element(element_type):
    """
    Get all issue types that can apply to a specific HTML element.

    Args:
        element_type: The HTML element type (e.g., 'img', 'a')

    Returns:
        List of issue types that can apply to the element.
    """
    return [
        issue_type
        for issue_type, info in ISSUE_TYPES.items()
        if element_type in info.get("element_types", [])
    ]
