# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0


"""
Form-related accessibility checks.

This module provides checks for proper form accessibility.
"""

from typing import List, Dict
from bs4 import Tag

from content_accessibility_utility_on_aws.audit.base_check import AccessibilityCheck


class FormLabelCheck(AccessibilityCheck):
    """Check for proper form labels (WCAG 1.3.1, 3.3.2)."""

    def check(self) -> None:
        """
        Check if form controls have proper labels.

        Issues:
            - form-control-missing-label: When a form control has no associated label
            - form-control-missing-name: When a form control has no name attribute
            - form-label-empty: When a label element has no text content
        """
        # Check input elements
        input_elements = self.soup.find_all("input")
        for input_elem in input_elements:
            # Skip hidden inputs and submit/reset buttons
            input_type = input_elem.get("type", "").lower()
            if input_type in ["hidden", "submit", "reset", "button"]:
                continue

            # Check for name attribute
            if not input_elem.has_attr("name"):
                self.add_issue(
                    "form-control-missing-name",
                    "1.3.1",
                    "major",
                    element=input_elem,
                    description=f"Form control ({input_type}) missing name attribute",
                )

            # Check for associated label
            has_label = self._has_associated_label(input_elem)

            if not has_label:
                self.add_issue(
                    "form-control-missing-label",
                    "1.3.1",
                    "critical",
                    element=input_elem,
                    description=f"Form control ({input_type}) has no associated label",
                )

        # Check select elements
        select_elements = self.soup.find_all("select")
        for select_elem in select_elements:
            # Check for name attribute
            if not select_elem.has_attr("name"):
                self.add_issue(
                    "form-control-missing-name",
                    "1.3.1",
                    "major",
                    element=select_elem,
                    description="Select control missing name attribute",
                )

            # Check for associated label
            has_label = self._has_associated_label(select_elem)

            if not has_label:
                self.add_issue(
                    "form-control-missing-label",
                    "1.3.1",
                    "critical",
                    element=select_elem,
                    description="Select control has no associated label",
                )

        # Check textarea elements
        textarea_elements = self.soup.find_all("textarea")
        for textarea_elem in textarea_elements:
            # Check for name attribute
            if not textarea_elem.has_attr("name"):
                self.add_issue(
                    "form-control-missing-name",
                    "1.3.1",
                    "major",
                    element=textarea_elem,
                    description="Textarea control missing name attribute",
                )

            # Check for associated label
            has_label = self._has_associated_label(textarea_elem)

            if not has_label:
                self.add_issue(
                    "form-control-missing-label",
                    "1.3.1",
                    "critical",
                    element=textarea_elem,
                    description="Textarea control has no associated label",
                )

        # Check label elements for content
        label_elements = self.soup.find_all("label")
        for label_elem in label_elements:
            label_text = self.get_element_text(label_elem)

            if not label_text:
                self.add_issue(
                    "form-label-empty",
                    "3.3.2",
                    "major",
                    element=label_elem,
                    description="Label element has no text content",
                )

    def _has_associated_label(self, form_control: Tag) -> bool:
        """
        Check if a form control has an associated label.

        Args:
            form_control: The form control element to check

        Returns:
            True if the form control has an associated label, False otherwise
        """
        # Check for id attribute
        if form_control.has_attr("id"):
            # Look for label with matching for attribute
            matching_label = self.soup.find("label", attrs={"for": form_control["id"]})
            if matching_label:
                return True

        # Check if the control is wrapped in a label
        parent_label = form_control.find_parent("label")
        if parent_label:
            return True

        # Check for aria-labelledby
        if form_control.has_attr("aria-labelledby"):
            label_ids = form_control["aria-labelledby"].split()
            for label_id in label_ids:
                label_elem = self.soup.find(id=label_id)
                if label_elem and self.get_element_text(label_elem):
                    return True

        # Check for aria-label
        if form_control.has_attr("aria-label") and form_control["aria-label"].strip():
            return True

        # Check for title attribute
        if form_control.has_attr("title") and form_control["title"].strip():
            return True

        # Check for placeholder (not sufficient for accessibility, but better than nothing)
        if form_control.has_attr("placeholder") and form_control["placeholder"].strip():
            return False  # We'll still report this as an issue

        return False


class FormRequiredFieldCheck(AccessibilityCheck):
    """Check for proper indication of required form fields (WCAG 3.3.2)."""

    def check(self) -> None:
        """
        Check if required form fields are properly indicated.

        Issues:
            - form-required-field-not-indicated: When a required field is not visually indicated
            - form-required-field-missing-aria: When a required field doesn't have aria-required
        """
        # Find all form controls
        form_controls = self.soup.find_all(["input", "select", "textarea"])

        for control in form_controls:
            # Skip hidden inputs and submit/reset buttons
            if control.name == "input":
                input_type = control.get("type", "").lower()
                if input_type in ["hidden", "submit", "reset", "button"]:
                    continue

            # Check if the field is required
            is_required = (
                control.has_attr("required") or control.get("aria-required") == "true"
            )

            if is_required:
                # Check for visual indication in label
                has_visual_indication = False

                # Check associated label
                if control.has_attr("id"):
                    label = self.soup.find("label", attrs={"for": control["id"]})
                    if label:
                        label_text = self.get_element_text(label)
                        if "*" in label_text or "required" in label_text.lower():
                            has_visual_indication = True

                # Check parent label
                parent_label = control.find_parent("label")
                if parent_label:
                    label_text = self.get_element_text(parent_label)
                    if "*" in label_text or "required" in label_text.lower():
                        has_visual_indication = True

                # Check for aria-required attribute
                if not control.has_attr("aria-required"):
                    self.add_issue(
                        "form-required-field-missing-aria",
                        "3.3.2",
                        "minor",
                        element=control,
                        description="Required form field missing aria-required='true' attribute",
                    )

                # Report if no visual indication
                if not has_visual_indication:
                    self.add_issue(
                        "form-required-field-not-indicated",
                        "3.3.2",
                        "major",
                        element=control,
                        description="Required form field not visually indicated as required",
                    )


class FormFieldsetCheck(AccessibilityCheck):
    """Check for proper use of fieldset and legend (WCAG 1.3.1)."""

    def check(self) -> None:
        """
        Check if related form controls are grouped with fieldset and legend.

        Issues:
            - form-fieldset-missing-legend: When a fieldset has no legend
            - form-related-controls-no-fieldset: When related controls are not grouped in a fieldset
        """
        # Check fieldsets for legends
        fieldsets = self.soup.find_all("fieldset")
        for fieldset in fieldsets:
            legend = fieldset.find("legend")
            if not legend or not self.get_element_text(legend).strip():
                self.add_issue(
                    "form-fieldset-missing-legend",
                    "1.3.1",
                    "major",
                    element=fieldset,
                    description="Fieldset missing legend element or legend has no content",
                )

        # Check for related controls that should be in fieldsets
        forms = self.soup.find_all("form")
        for form in forms:
            # Check for groups of radio buttons
            self._check_radio_groups(form)

            # Check for groups of checkboxes
            self._check_checkbox_groups(form)

    def _check_radio_groups(self, form: Tag) -> None:
        """
        Check for groups of radio buttons that should be in fieldsets.

        Args:
            form: The form element to check
        """
        # Group radio buttons by name
        radio_groups: Dict[str, List[Tag]] = {}

        for radio in form.find_all("input", attrs={"type": "radio"}):
            if radio.has_attr("name"):
                name = radio["name"]
                if name not in radio_groups:
                    radio_groups[name] = []
                radio_groups[name].append(radio)

        # Check each group
        for name, radios in radio_groups.items():
            # If there are multiple radios with the same name
            if len(radios) > 1:
                # Check if they're in a fieldset
                in_fieldset = False
                for radio in radios:
                    if radio.find_parent("fieldset"):
                        in_fieldset = True
                        break

                if not in_fieldset:
                    self.add_issue(
                        "form-related-controls-no-fieldset",
                        "1.3.1",
                        "major",
                        element=radios[0],
                        description=f"Group of {len(radios)} radio buttons should"
                        + "be wrapped in fieldset with legend",
                    )

    def _check_checkbox_groups(self, form: Tag) -> None:
        """
        Check for groups of checkboxes that should be in fieldsets.

        Args:
            form: The form element to check
        """
        # Find all checkboxes
        checkboxes = form.find_all("input", attrs={"type": "checkbox"})

        # If there are multiple checkboxes, check if they're related
        if len(checkboxes) > 2:
            # Group checkboxes by proximity in the DOM
            checkbox_groups = []
            current_group = []

            for checkbox in checkboxes:
                if not current_group:
                    current_group.append(checkbox)
                else:
                    # Check if this checkbox is close to the previous one
                    prev_checkbox = current_group[-1]

                    # If they share a common parent within 3 levels, consider them related
                    if self._share_close_parent(checkbox, prev_checkbox, max_levels=3):
                        current_group.append(checkbox)
                    else:
                        if len(current_group) > 1:
                            checkbox_groups.append(current_group)
                        current_group = [checkbox]

            # Add the last group if it has multiple checkboxes
            if len(current_group) > 1:
                checkbox_groups.append(current_group)

            # Check each group
            for group in checkbox_groups:
                # Check if they're in a fieldset
                in_fieldset = False
                for checkbox in group:
                    if checkbox.find_parent("fieldset"):
                        in_fieldset = True
                        break

                if not in_fieldset:
                    self.add_issue(
                        "form-related-controls-no-fieldset",
                        "1.3.1",
                        "minor",
                        element=group[0],
                        description=f"Group of {len(group)} checkboxes should be wrapped in fieldset with legend",
                    )

    def _share_close_parent(self, elem1: Tag, elem2: Tag, max_levels: int = 3) -> bool:
        """
        Check if two elements share a common parent within a certain number of levels.

        Args:
            elem1: The first element
            elem2: The second element
            max_levels: The maximum number of levels to check

        Returns:
            True if the elements share a close parent, False otherwise
        """
        # Get parents of elem1
        elem1_parents = []
        parent = elem1.parent
        for _ in range(max_levels):
            if parent:
                elem1_parents.append(parent)
                parent = parent.parent
            else:
                break

        # Check if any parent of elem2 is in elem1_parents
        parent = elem2.parent
        for _ in range(max_levels):
            if parent:
                if parent in elem1_parents:
                    return True
                parent = parent.parent
            else:
                break

        return False
