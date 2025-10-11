# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Remediation strategies for common accessibility issues.

This module provides templates and strategies for remediating different types of accessibility issues.
"""

# Define remediation templates for different issue types
REMEDIATION_TEMPLATES = {
    # Content Alternatives
    "missing-alt-text": {
        "prompt": """
        This image is missing alternative text. Please provide appropriate alt text that:
        1. Describes the content and function of the image
        2. Is concise and meaningful
        3. Does not use phrases like "image of" or "picture of"
        
        Context information:
        {context}
        
        Respond with ONLY the alt text in the format:
        ```
        alt="your alternative text here"
        ```
        """,
        "fix_type": "attribute",
        "attribute": "alt",
    },
    "generic-alt-text": {
        "prompt": """
        This image has generic alternative text ("{current_alt}") that does not adequately describe the image. 
        Please provide appropriate alt text that:
        1. Describes the content and function of the image
        2. Is concise and meaningful
        3. Does not use phrases like "image of" or "picture of"
        
        Context information:
        {context}
        
        Respond with ONLY the alt text in the format:
        ```
        alt="your alternative text here"
        ```
        """,
        "fix_type": "attribute",
        "attribute": "alt",
    },
    "improper-figure-structure": {
        "prompt": """
        This image should be wrapped in a proper figure structure with a figcaption. 
        Please provide HTML that:
        1. Wraps the image in a <figure> element
        2. Includes the image with appropriate alt text
        3. Adds a <figcaption> with the caption text
        
        Current image: {element_html}
        
        Context information:
        {context}
        
        Respond with the complete HTML structure in the format:
        ```html
        <figure>
          <img src="..." alt="...">
          <figcaption>...</figcaption>
        </figure>
        ```
        
        Explain your fix:
        """,
        "fix_type": "content",
    },
    # Document Structure
    "improper-heading-structure": {
        "prompt": """
        There is an improper heading structure where heading levels are skipped. 
        Please fix the heading structure by:
        1. Ensuring heading levels are sequential (h1 followed by h2, etc.)
        2. Maintaining the same content and meaning
        
        Current heading: {element_html}
        
        Context information:
        {context}
        
        Respond with the corrected heading HTML:
        ```html
        <hX>Heading text</hX>
        ```
        
        Explain your fix:
        """,
        "fix_type": "content",
    },
    "missing-document-language": {
        "prompt": """
        The HTML document is missing a language attribute. 
        Please determine the appropriate language for this document based on the content.
        
        Document content excerpt:
        {context}
        
        Respond with the language code in the format:
        ```
        lang="en"
        ```
        (Replace "en" with the appropriate language code)
        """,
        "fix_type": "attribute",
        "attribute": "lang",
    },
    # Tables
    "missing-table-headers": {
        "prompt": """
        This table is missing proper header cells. Please provide HTML for a properly structured table with:
        1. Appropriate <th> elements for column/row headers
        2. Scope attributes on header cells
        
        Current table structure: {element_html}
        
        Context information:
        {context}
        
        Respond with the corrected table HTML:
        ```html
        <table>
          <tr>
            <th scope="col">Header 1</th>
            ...
          </tr>
          ...
        </table>
        ```
        
        Explain your fix:
        """,
        "fix_type": "content",
    },
    "missing-header-scope": {
        "prompt": """
        This table header is missing a scope attribute. Please add the appropriate scope attribute:
        - Use scope="col" for column headers
        - Use scope="row" for row headers
        
        Current header: {element_html}
        
        Context information:
        {context}
        
        Respond with ONLY the scope attribute in the format:
        ```
        scope="col"
        ```
        or
        ```
        scope="row"
        ```
        """,
        "fix_type": "attribute",
        "attribute": "scope",
    },
    # Forms
    "missing-form-label": {
        "prompt": """
        This form control is missing an accessible label. Please provide a solution by either:
        1. Adding a <label> element with a 'for' attribute matching the control's ID
        2. Adding an aria-label attribute directly to the control
        
        Current form control: {element_html}
        
        Context information:
        {context}
        
        If adding a label element, respond with the HTML in the format:
        ```html
        <label for="element-id">Label text</label>
        ```
        
        If adding an aria-label, respond with:
        ```
        aria-label="Label text"
        ```
        
        Explain your fix:
        """,
        "fix_type": "mixed",
    },
    # Links
    "empty-link": {
        "prompt": """
        This link has no text content, making it inaccessible to screen reader users.
        Please provide appropriate link text that:
        1. Describes the purpose or destination of the link
        2. Is concise and meaningful
        3. Makes sense out of context
        
        Current link: {element_html}
        
        Context information:
        {context}
        
        Respond with the link text in the format:
        ```
        Link text here
        ```
        """,
        "fix_type": "content",
    },
    "generic-link-text": {
        "prompt": """
        This link uses generic text ("{link_text}") that doesn't describe its purpose or destination.
        Please provide more descriptive link text that:
        1. Clearly describes the purpose or destination of the link
        2. Is concise and meaningful
        3. Makes sense out of context
        
        Current link: {element_html}
        
        Context information:
        {context}
        
        Respond with the improved link text in the format:
        ```
        Improved link text here
        ```
        """,
        "fix_type": "content",
    },
}


def get_remediation_template(issue_type):
    """
    Get the remediation template for a specific issue type.

    Args:
        issue_type: The type of accessibility issue

    Returns:
        Dictionary with remediation template information, or empty dict if not found.
    """
    return REMEDIATION_TEMPLATES.get(issue_type, {})


def format_remediation_prompt(template, issue_data):
    """
    Format a remediation prompt with issue-specific data.

    Args:
        template: The template string
        issue_data: Dictionary containing issue data

    Returns:
        Formatted prompt string
    """
    # Extract context information
    context = issue_data.get("context", {})
    if isinstance(context, dict):
        context_str = "\n".join([f"{k}: {v}" for k, v in context.items() if v])
    else:
        context_str = str(context)

    # Get element HTML if available
    element_html = issue_data.get("element_html", "Not available")

    # Get current alt text for generic alt text issues
    current_alt = ""
    if issue_data.get("location") and issue_data["location"].get("alt_type"):
        current_alt = issue_data["location"]["alt_type"]

    # Get link text for generic link text issues
    link_text = ""
    if issue_data.get("element") == "a" and issue_data.get("context"):
        if isinstance(issue_data["context"], dict) and issue_data["context"].get(
            "text"
        ):
            link_text = issue_data["context"]["text"]
        elif isinstance(issue_data["context"], str):
            link_text = issue_data["context"]

    # Format the template
    formatted_prompt = template.format(
        context=context_str,
        element_html=element_html,
        current_alt=current_alt,
        link_text=link_text,
    )

    return formatted_prompt
