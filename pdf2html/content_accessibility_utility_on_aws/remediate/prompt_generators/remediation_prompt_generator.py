# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Remediation Prompt Generator module.

This module provides functionality to generate prompts for AI models
to remediate accessibility issues in HTML.
"""

import os
import re
from typing import Dict, Any, Optional

from content_accessibility_utility_on_aws.utils.logging_helper import setup_logger

# Set up module-level logger
logger = setup_logger(__name__)


class RemediationPromptGenerator:
    """
    Class for generating prompts for AI models to remediate accessibility issues.
    """

    def __init__(self):
        """Initialize the prompt generator."""

    def generate_prompt(
        self,
        issue: Dict[str, Any],
        html_content: Optional[str] = None,
        element_html: Optional[str] = None,
        context: Optional[str] = None,
        image_path: Optional[str] = None,
        current_alt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a prompt for an AI model to remediate an accessibility issue.

        Args:
            issue: Issue data
            html_content: HTML content surrounding the issue
            element_html: HTML of the element with the issue
            context: Additional context for the issue
            image_path: Path to an image file (for image-related issues)
            current_alt: Current alt text (for long-alt-text issues)

        Returns:
            Dictionary with prompt data
        """
        issue_type = issue.get("type", "")
        issue_description = issue.get("description", "")

        # Base prompt template
        prompt = f"""You are an accessibility expert tasked with fixing HTML accessibility issues.

ISSUE TYPE: {issue_type}
ISSUE DESCRIPTION: {issue_description}

"""

        # Add element HTML if available
        if element_html:
            prompt += f"ELEMENT HTML:\n{element_html}\n\n"

        # Add context if available
        if context:
            prompt += f"CONTEXT:\n{context}\n\n"

        # Add current alt text for long-alt-text issues
        if current_alt and issue_type == "long-alt-text":
            prompt += f"CURRENT ALT TEXT: {current_alt}\n\n"

        # Add specific instructions based on issue type
        if "alt-text" in issue_type:
            prompt += """TASK: Generate a concise, descriptive alt text for this image.
The alt text should:
1. Be brief but descriptive (typically 125 characters or less)
2. Convey the essential information in the image
3. Not start with phrases like "image of" or "picture of"
4. Consider the context where the image appears

RESPONSE FORMAT:
```
alt="Your descriptive alt text here"
```
"""
        elif issue_type == "long-alt-text":
            prompt += """TASK: Shorten the existing alt text to be more concise while preserving essential information.
The alt text should:
1. Be brief but descriptive (typically 125 characters or less)
2. Convey the essential information in the image
3. Not start with phrases like "image of" or "picture of"
4. Consider the context where the image appears

RESPONSE FORMAT:
```
alt="Your shortened alt text here"
```
"""
        elif issue_type == "missing-heading-structure":
            prompt += """TASK: Determine the appropriate heading level for this content based on the context.

RESPONSE FORMAT:
```
<h1>Content here</h1>
```
(Use the appropriate heading level h1-h6 based on the content hierarchy)
"""
        elif issue_type == "table-missing-headers":
            prompt += """TASK: Add appropriate table headers to make this table accessible.

RESPONSE FORMAT:
```html
<table>
  <thead>
    <tr>
      <th>Header 1</th>
      <th>Header 2</th>
      <!-- Add more headers as needed -->
    </tr>
  </thead>
  <tbody>
    <!-- Original table rows here -->
  </tbody>
</table>
```
"""
        else:
            # Generic prompt for other issue types
            prompt += f"""TASK: Fix the accessibility issue in the HTML element.

RESPONSE FORMAT:
```html
<!-- Your fixed HTML here -->
```

Explain your fix:
"""

        # Add image analysis instructions if image path is provided
        if image_path and os.path.exists(image_path):
            prompt += (
                "\nPlease analyze the provided image to generate an appropriate fix.\n"
            )

        return {"prompt": prompt, "issue_type": issue_type}

    def parse_fix(
        self,
        model_response: str,
        issue_type: str,
        element_html: Optional[str] = None,
        current_alt_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Parse the model response to extract the fix.

        Args:
            model_response: Response from the AI model
            issue_type: Type of issue being fixed
            element_html: Original HTML of the element
            current_alt_text: Current alt text (for long-alt-text issues)

        Returns:
            Dictionary with fix data
        """
        try:
            # For alt text issues
            if "alt-text" in issue_type:
                # Extract alt text from response
                alt_match = re.search(r'alt="([^"]*)"', model_response)
                if alt_match:
                    alt_text = alt_match.group(1)
                    return {"type": "attribute", "attribute": "alt", "value": alt_text}
                else:
                    # Try alternative format
                    alt_match = re.search(r'```\s*alt="([^"]*)"\s*```', model_response)
                    if alt_match:
                        alt_text = alt_match.group(1)
                        return {
                            "type": "attribute",
                            "attribute": "alt",
                            "value": alt_text,
                        }

                    # Try to extract any text between triple backticks
                    code_match = re.search(
                        r"```(?:html)?\s*(.*?)\s*```", model_response, re.DOTALL
                    )
                    if code_match:
                        code = code_match.group(1)
                        alt_match = re.search(r'alt="([^"]*)"', code)
                        if alt_match:
                            alt_text = alt_match.group(1)
                            return {
                                "type": "attribute",
                                "attribute": "alt",
                                "value": alt_text,
                            }

                # If no alt text found, return error
                return {"error": "Could not extract alt text from model response"}

            # For heading structure issues
            elif issue_type == "missing-heading-structure":
                # Extract heading tag and content
                heading_match = re.search(
                    r"<(h[1-6])>(.*?)</\1>", model_response, re.DOTALL
                )
                if heading_match:
                    tag = heading_match.group(1)
                    content = heading_match.group(2)
                    return {
                        "type": "replace",
                        "element": {"tag": tag, "content": content},
                    }
                else:
                    # Try to extract any HTML between triple backticks
                    code_match = re.search(
                        r"```(?:html)?\s*(.*?)\s*```", model_response, re.DOTALL
                    )
                    if code_match:
                        code = code_match.group(1)
                        heading_match = re.search(
                            r"<(h[1-6])>(.*?)</\1>", code, re.DOTALL
                        )
                        if heading_match:
                            tag = heading_match.group(1)
                            content = heading_match.group(2)
                            return {
                                "type": "replace",
                                "element": {"tag": tag, "content": content},
                            }

                # If no heading found, return error
                return {"error": "Could not extract heading from model response"}

            # For table header issues
            elif issue_type == "table-missing-headers":
                # Extract table HTML
                table_match = re.search(
                    r"<table[^>]*>(.*?)</table>", model_response, re.DOTALL
                )
                if table_match:
                    table_html = table_match.group(0)
                    return {"type": "content", "content": table_html}
                else:
                    # Try to extract any HTML between triple backticks
                    code_match = re.search(
                        r"```(?:html)?\s*(.*?)\s*```", model_response, re.DOTALL
                    )
                    if code_match:
                        code = code_match.group(1)
                        table_match = re.search(
                            r"<table[^>]*>(.*?)</table>", code, re.DOTALL
                        )
                        if table_match:
                            table_html = table_match.group(0)
                            return {"type": "content", "content": table_html}

                # If no table found, return error
                return {"error": "Could not extract table from model response"}

            # For other issues, try to extract HTML
            else:
                # Try to extract any HTML between triple backticks
                code_match = re.search(
                    r"```(?:html)?\s*(.*?)\s*```", model_response, re.DOTALL
                )
                if code_match:
                    html = code_match.group(1)
                    return {"type": "content", "content": html}

                # If no HTML found, return error
                return {"error": "Could not extract HTML from model response"}

        except Exception as e:
            logger.error(f"Error parsing model response: {e}")
            return {"error": f"Error parsing model response: {str(e)}"}
