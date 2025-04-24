# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Form accessibility remediation strategies.

This module provides remediation strategies for form-related accessibility issues.
"""

from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup
import re

from content_accessibility_utility_on_aws.utils.logging_helper import setup_logger

# Set up module-level logger
logger = setup_logger(__name__)


def remediate_missing_form_labels(
    soup: BeautifulSoup, issue: Dict[str, Any], *args
) -> Optional[str]:
    """
    Remediate form inputs missing labels.

    Args:
        soup: The BeautifulSoup object representing the HTML document
        issue: The accessibility issue to remediate

    Returns:
        A message describing the remediation, or None if no remediation was performed
    """
    # Extract element path from the issue
    path = issue.get("location", {}).get("path")
    if not path:
        logger.warning("No element path provided in issue")
        return None

    # Find the form control with missing label
    form_control = None
    for control in soup.find_all(["input", "select", "textarea"]):
        # This is a simplified selector match - in practice we would need more robust matching
        if path.lower() in str(control).lower():
            form_control = control
            break

    if not form_control:
        logger.warning(f"Could not find form control with path: {path}")
        return None

    # Check if it already has an associated label
    control_id = form_control.get("id")

    if control_id:
        existing_label = soup.find("label", attrs={"for": control_id})
        if existing_label:
            logger.debug(f"Form control already has a label")
            return None

    # Generate an ID if one doesn't exist
    if not control_id:
        control_type = form_control.name
        input_type = (
            form_control.get("type", "text")
            if control_type == "input"
            else control_type
        )

        # Generate a unique ID
        siblings = len(list(form_control.find_previous_siblings(control_type)))
        control_id = f"{input_type}-{siblings + 1}"
        form_control["id"] = control_id

    # Generate appropriate label text
    label_text = "Label"

    # Try to derive label text from attributes
    if form_control.get("placeholder"):
        label_text = form_control["placeholder"]
    elif form_control.get("name"):
        # Convert name to label text (e.g., "user_email" -> "User Email")
        name = form_control["name"]
        label_text = " ".join(word.capitalize() for word in re.split(r"[_\-]", name))
    elif form_control.get("type"):
        label_text = form_control["type"].capitalize()

    # Create and insert label
    label = soup.new_tag("label")
    label["for"] = control_id
    label.string = label_text
    form_control.insert_before(label)

    return f"Added label '{label_text}' for form control"


def remediate_missing_required_indicators(
    soup: BeautifulSoup, issue: Dict[str, Any], *args
) -> Optional[str]:
    """
    Remediate form fields missing required field indicators.

    Args:
        soup: The BeautifulSoup object representing the HTML document
        issue: The accessibility issue to remediate

    Returns:
        A message describing the remediation, or None if no remediation was performed
    """
    # Extract element path from the issue
    path = issue.get("location", {}).get("path")
    if not path:
        logger.warning("No element path provided in issue")
        return None

    # Find the form control
    form_control = None
    for control in soup.find_all(["input", "select", "textarea"]):
        # This is a simplified selector match - in practice we would need more robust matching
        if path.lower() in str(control).lower():
            form_control = control
            break

    if not form_control:
        logger.warning(f"Could not find form control with path: {path}")
        return None

    # Check if it's a required field
    if form_control.get("required") or form_control.get("aria-required") == "true":
        # Find associated label
        label = None
        if form_control.get("id"):
            label = soup.find("label", attrs={"for": form_control["id"]})

        # Add visual indicator to label
        if label:
            # Check if label already has an asterisk
            if "*" not in label.get_text():
                # Add required indicator
                if label.string:
                    label.string = f"{label.string} *"
                else:
                    label.append(" *")

                # Add explanation of asterisk if not already present
                form = form_control.find_parent("form")
                if form:
                    # Look for existing required field explanation
                    has_explanation = False
                    for p in form.find_all("p"):
                        if "*" in p.get_text() and (
                            "required" in p.get_text().lower()
                            or "mandatory" in p.get_text().lower()
                        ):
                            has_explanation = True
                            break

                    # Add explanation if not present
                    if not has_explanation:
                        explanation = soup.new_tag("p")
                        explanation["class"] = "form-required-explanation"
                        explanation.string = "* indicates required fields"
                        form.append(explanation)

            # Ensure aria-required is set
            if not form_control.get("aria-required"):
                form_control["aria-required"] = "true"

            return "Added required field indicator"

    return None


def remediate_missing_fieldsets(
    soup: BeautifulSoup, issue: Dict[str, Any], *args
) -> Optional[str]:
    """
    Remediate form groups missing fieldset and legend elements.

    Args:
        soup: The BeautifulSoup object representing the HTML document
        issue: The accessibility issue to remediate

    Returns:
        A message describing the remediation, or None if no remediation was performed
    """
    # Extract element path from the issue
    form_path = issue.get("location", {}).get("path")
    if not form_path:
        logger.warning("No form path provided in issue")
        return None

    # Find the form
    form = None
    for f in soup.find_all("form"):
        # This is a simplified selector match - in practice we would need more robust matching
        if form_path.lower() in str(f).lower():
            form = f
            break

    if not form:
        logger.warning(f"Could not find form with path: {form_path}")
        return None

    # Check for existing fieldsets
    if form.find("fieldset"):
        logger.debug("Form already has fieldset elements")
        return None

    # Identify logical groups of form elements based on structure or common prefixes
    # Strategy 1: Look for div containers with multiple inputs
    input_groups = []
    for div in form.find_all("div"):
        inputs = div.find_all(["input", "select", "textarea"])
        if len(inputs) >= 2:
            input_groups.append((div, inputs, None))

    # If no clear grouping by divs, group by input types/names
    if not input_groups:
        all_inputs = form.find_all(["input", "select", "textarea"])

        # Group by common name prefixes (e.g., address_line1, address_city)
        name_groups = {}
        for input_elem in all_inputs:
            name = input_elem.get("name", "")
            if name:
                prefix = name.split("_")[0] if "_" in name else name
                if prefix not in name_groups:
                    name_groups[prefix] = []
                name_groups[prefix].append(input_elem)

        # Add groups with multiple inputs
        for prefix, inputs in name_groups.items():
            if len(inputs) >= 2:
                # Find common parent
                parent = inputs[0].parent
                input_groups.append((parent, inputs, prefix.capitalize()))

    # Add fieldsets for each group
    added_count = 0
    for parent, inputs, legend_text in input_groups:
        # Create fieldset
        fieldset = soup.new_tag("fieldset")

        # Create legend if we have text
        if legend_text:
            legend = soup.new_tag("legend")
            legend.string = legend_text
            fieldset.append(legend)
        else:
            # Try to derive legend text from labels or parent element
            labels = []
            for inp in inputs:
                if inp.get("id"):
                    label = soup.find("label", attrs={"for": inp["id"]})
                    if label:
                        labels.append(label.get_text(strip=True))

            if labels:
                common_text = find_common_prefix(labels)
                if common_text and len(common_text) > 3:
                    legend = soup.new_tag("legend")
                    legend.string = common_text.strip()
                    fieldset.append(legend)

        # Extract content to move to fieldset
        content = parent.decode_contents()
        parent.clear()

        # Add content to fieldset
        fieldset.append(BeautifulSoup(content, "html.parser"))

        # Add fieldset to parent
        parent.append(fieldset)
        added_count += 1

    if added_count > 0:
        return f"Added {added_count} fieldset elements to form"

    return None


def find_common_prefix(strings: List[str]) -> str:
    """Helper function to find common text prefix among strings."""
    if not strings:
        return ""

    # Normalize strings
    strings = [s.lower() for s in strings]

    # Find common prefix
    prefix = strings[0]
    for s in strings[1:]:
        while s[: len(prefix)] != prefix and prefix:
            prefix = prefix[:-1]
        if not prefix:
            break

    return prefix if len(prefix) > 3 else ""
