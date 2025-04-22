"""
WCAG standards and criteria information.

This module provides information about WCAG standards and criteria.
"""

# Severity levels (higher number = more severe)
SEVERITY_LEVELS = {
    "minor": 1,
    "major": 2,
    "critical": 3,
    "compliant": 0,  # Special case for compliant issues
}

# WCAG criteria information
WCAG_CRITERIA = {
    "1.1.1": {
        "name": "Non-text Content",
        "level": "A",
        "description": "All non-text content that is presented to the user has a text alternative that serves the equivalent purpose.",
    },
    "1.2.1": {
        "name": "Audio-only and Video-only (Prerecorded)",
        "level": "A",
        "description": "For prerecorded audio-only and prerecorded video-only media, alternatives are provided.",
    },
    "1.2.2": {
        "name": "Captions (Prerecorded)",
        "level": "A",
        "description": "Captions are provided for all prerecorded audio content in synchronized media.",
    },
    "1.3.1": {
        "name": "Info and Relationships",
        "level": "A",
        "description": "Information, structure, and relationships conveyed through presentation can be programmatically determined.",
    },
    "1.3.2": {
        "name": "Meaningful Sequence",
        "level": "A",
        "description": "When the sequence in which content is presented affects its meaning, a correct reading sequence can be programmatically determined.",
    },
    "1.4.1": {
        "name": "Use of Color",
        "level": "A",
        "description": "Color is not used as the only visual means of conveying information.",
    },
    "1.4.3": {
        "name": "Contrast (Minimum)",
        "level": "AA",
        "description": "The visual presentation of text and images of text has a contrast ratio of at least 4.5:1.",
    },
    "2.1.1": {
        "name": "Keyboard",
        "level": "A",
        "description": "All functionality is operable through a keyboard interface.",
    },
    "2.4.1": {
        "name": "Bypass Blocks",
        "level": "A",
        "description": "A mechanism is available to bypass blocks of content that are repeated on multiple Web pages.",
    },
    "2.4.2": {
        "name": "Page Titled",
        "level": "A",
        "description": "Web pages have titles that describe topic or purpose.",
    },
    "2.4.4": {
        "name": "Link Purpose (In Context)",
        "level": "A",
        "description": "The purpose of each link can be determined from the link text alone or from the link text together with its programmatically determined link context.",
    },
    "2.4.6": {
        "name": "Headings and Labels",
        "level": "AA",
        "description": "Headings and labels describe topic or purpose.",
    },
    "3.1.1": {
        "name": "Language of Page",
        "level": "A",
        "description": "The default human language of each Web page can be programmatically determined.",
    },
    "3.3.2": {
        "name": "Labels or Instructions",
        "level": "A",
        "description": "Labels or instructions are provided when content requires user input.",
    },
    "4.1.1": {
        "name": "Parsing",
        "level": "A",
        "description": "In content implemented using markup languages, elements have complete start and end tags.",
    },
    "4.1.2": {
        "name": "Name, Role, Value",
        "level": "A",
        "description": "For all user interface components, the name and role can be programmatically determined.",
    },
}


def get_criterion_info(criterion_id: str) -> dict:
    """
    Get information about a WCAG criterion.

    Args:
        criterion_id: WCAG criterion ID (e.g., '1.1.1')

    Returns:
        Dictionary with criterion information
    """
    return WCAG_CRITERIA.get(
        criterion_id,
        {
            "name": "Unknown Criterion",
            "level": "Unknown",
            "description": "No description available",
        },
    )
