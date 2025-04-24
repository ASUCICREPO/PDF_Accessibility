# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
HTML Accessibility Standards.

This module provides constants and utilities for working with WCAG 2.1 accessibility standards.
"""

# Define severity levels for accessibility issues
# Higher value = more severe
SEVERITY_LEVELS = {
    "critical": 3,  # Must be fixed - causes accessibility barriers
    "major": 2,  # Should be fixed - significant accessibility issues
    "minor": 1,  # Good to fix - minor accessibility improvements
    "info": 0,  # Informational only - not necessarily an issue
}

# Define severity impact matrix for better classification
SEVERITY_MATRIX = {
    "critical": {
        "impact": "Prevents access",
        "scope": "Affects all users",
        "frequency": "Occurs on every page",
    },
    "major": {
        "impact": "Significantly hinders access",
        "scope": "Affects specific user groups",
        "frequency": "Occurs frequently",
    },
    "minor": {
        "impact": "Causes inconvenience",
        "scope": "Affects few users",
        "frequency": "Occurs occasionally",
    },
    "info": {
        "impact": "Informational only",
        "scope": "Best practice",
        "frequency": "Not an accessibility barrier",
    },
}

# WCAG 2.1 Success Criteria
WCAG_CRITERIA = {
    # Perceivable
    "1.1.1": {"name": "Non-text Content", "level": "A"},
    "1.2.1": {"name": "Audio-only and Video-only (Prerecorded)", "level": "A"},
    "1.2.2": {"name": "Captions (Prerecorded)", "level": "A"},
    "1.2.3": {"name": "Audio Description or Media Alternative", "level": "A"},
    "1.2.4": {"name": "Captions (Live)", "level": "AA"},
    "1.2.5": {"name": "Audio Description", "level": "AA"},
    "1.2.6": {"name": "Sign Language", "level": "AAA"},
    "1.2.7": {"name": "Extended Audio Description", "level": "AAA"},
    "1.2.8": {"name": "Media Alternative", "level": "AAA"},
    "1.2.9": {"name": "Audio-only (Live)", "level": "AAA"},
    "1.3.1": {"name": "Info and Relationships", "level": "A"},
    "1.3.2": {"name": "Meaningful Sequence", "level": "A"},
    "1.3.3": {"name": "Sensory Characteristics", "level": "A"},
    "1.3.4": {"name": "Orientation", "level": "AA"},
    "1.3.5": {"name": "Identify Input Purpose", "level": "AA"},
    "1.3.6": {"name": "Identify Purpose", "level": "AAA"},
    "1.4.1": {"name": "Use of Color", "level": "A"},
    "1.4.2": {"name": "Audio Control", "level": "A"},
    "1.4.3": {"name": "Contrast (Minimum)", "level": "AA"},
    "1.4.4": {"name": "Resize Text", "level": "AA"},
    "1.4.5": {"name": "Images of Text", "level": "AA"},
    "1.4.6": {"name": "Contrast (Enhanced)", "level": "AAA"},
    "1.4.7": {"name": "Low or No Background Audio", "level": "AAA"},
    "1.4.8": {"name": "Visual Presentation", "level": "AAA"},
    "1.4.9": {"name": "Images of Text (No Exception)", "level": "AAA"},
    "1.4.10": {"name": "Reflow", "level": "AA"},
    "1.4.11": {"name": "Non-text Contrast", "level": "AA"},
    "1.4.12": {"name": "Text Spacing", "level": "AA"},
    "1.4.13": {"name": "Content on Hover or Focus", "level": "AA"},
    # Operable
    "2.1.1": {"name": "Keyboard", "level": "A"},
    "2.1.2": {"name": "No Keyboard Trap", "level": "A"},
    "2.1.3": {"name": "Keyboard (No Exception)", "level": "AAA"},
    "2.1.4": {"name": "Character Key Shortcuts", "level": "A"},
    "2.2.1": {"name": "Timing Adjustable", "level": "A"},
    "2.2.2": {"name": "Pause, Stop, Hide", "level": "A"},
    "2.2.3": {"name": "No Timing", "level": "AAA"},
    "2.2.4": {"name": "Interruptions", "level": "AAA"},
    "2.2.5": {"name": "Re-authenticating", "level": "AAA"},
    "2.2.6": {"name": "Timeouts", "level": "AAA"},
    "2.3.1": {"name": "Three Flashes or Below Threshold", "level": "A"},
    "2.3.2": {"name": "Three Flashes", "level": "AAA"},
    "2.3.3": {"name": "Animation from Interactions", "level": "AAA"},
    "2.4.1": {"name": "Bypass Blocks", "level": "A"},
    "2.4.2": {"name": "Page Titled", "level": "A"},
    "2.4.3": {"name": "Focus Order", "level": "A"},
    "2.4.4": {"name": "Link Purpose (In Context)", "level": "A"},
    "2.4.5": {"name": "Multiple Ways", "level": "AA"},
    "2.4.6": {"name": "Headings and Labels", "level": "AA"},
    "2.4.7": {"name": "Focus Visible", "level": "AA"},
    "2.4.8": {"name": "Location", "level": "AAA"},
    "2.4.9": {"name": "Link Purpose (Link Only)", "level": "AAA"},
    "2.4.10": {"name": "Section Headings", "level": "AAA"},
    "2.5.1": {"name": "Pointer Gestures", "level": "A"},
    "2.5.2": {"name": "Pointer Cancellation", "level": "A"},
    "2.5.3": {"name": "Label in Name", "level": "A"},
    "2.5.4": {"name": "Motion Actuation", "level": "A"},
    "2.5.5": {"name": "Target Size", "level": "AAA"},
    "2.5.6": {"name": "Concurrent Input Mechanisms", "level": "AAA"},
    # Understandable
    "3.1.1": {"name": "Language of Page", "level": "A"},
    "3.1.2": {"name": "Language of Parts", "level": "AA"},
    "3.1.3": {"name": "Unusual Words", "level": "AAA"},
    "3.1.4": {"name": "Abbreviations", "level": "AAA"},
    "3.1.5": {"name": "Reading Level", "level": "AAA"},
    "3.1.6": {"name": "Pronunciation", "level": "AAA"},
    "3.2.1": {"name": "On Focus", "level": "A"},
    "3.2.2": {"name": "On Input", "level": "A"},
    "3.2.3": {"name": "Consistent Navigation", "level": "AA"},
    "3.2.4": {"name": "Consistent Identification", "level": "AA"},
    "3.2.5": {"name": "Change on Request", "level": "AAA"},
    "3.3.1": {"name": "Error Identification", "level": "A"},
    "3.3.2": {"name": "Labels or Instructions", "level": "A"},
    "3.3.3": {"name": "Error Suggestion", "level": "AA"},
    "3.3.4": {"name": "Error Prevention (Legal, Financial, Data)", "level": "AA"},
    "3.3.5": {"name": "Help", "level": "AAA"},
    "3.3.6": {"name": "Error Prevention (All)", "level": "AAA"},
    # Robust
    "4.1.1": {"name": "Parsing", "level": "A"},
    "4.1.2": {"name": "Name, Role, Value", "level": "A"},
    "4.1.3": {"name": "Status Messages", "level": "AA"},
}


def get_criterion_info(criterion_id):
    """
    Get information about a specific WCAG criterion.

    Args:
        criterion_id: The WCAG criterion ID (e.g., '1.1.1')

    Returns:
        Dictionary with criterion information, or empty dict if not found.
    """
    return WCAG_CRITERIA.get(criterion_id, {})


# Import issue types
