# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Remediation strategies for accessibility issues.

This package contains strategies for remediating different types of accessibility issues.
"""

# Import remediation strategies for easier access









# Define functions needed by remediator.py
def get_remediation_template(issue_type: str) -> str:
    """
    Get the remediation template for a specific issue type.

    Args:
        issue_type: The type of accessibility issue

    Returns:
        Template string for remediation prompt
    """
    templates = {
        # Table remediation templates
        "table-missing-scope": {
            "prompt": """
            You are an accessibility expert tasked with adding scope attributes to table headers.
            
            Each table header (th) should have a scope attribute that identifies whether it's a header for a row or column:
            - scope="col" for column headers (usually in the first row)
            - scope="row" for row headers (usually in the first column)
            
            Table structure:
            {element_html}
            
            RESPONSE FORMAT:
            For column headers:
            ```
            scope="col"
            ```
            
            For row headers:
            ```
            scope="row"
            ```
            """,
            "fix_type": "attribute",
            "attribute": "scope",
        },
        "table-missing-thead": {
            "prompt": """
            You are an accessibility expert tasked with adding a proper thead element to a table.
            
            Please determine which rows should be in the table header (thead) based on:
            1. Content of the cells (headers vs. data)
            2. Presence of th elements
            3. Position in the table
            
            Table structure:
            {element_html}
            
            RESPONSE FORMAT:
            Return a JSON array with zero-based indices of rows that should be in the thead:
            ```
            [0]
            ```
            or for multiple header rows:
            ```
            [0, 1]
            ```
            """,
            "fix_type": "row_structure",
            "container": "thead",
        },
        "table-missing-tbody": {
            "prompt": """
            You are an accessibility expert tasked with adding proper tbody structure to a table.
            
            Please determine:
            1. Which rows should be in the table body (tbody)
            2. If any rows should be in the table footer (tfoot), like totals or summaries
            
            Table structure:
            {element_html}
            
            RESPONSE FORMAT:
            Return a JSON array with zero-based indices of rows that should be in the tfoot (if any):
            ```
            []
            ```
            or for tables with footer rows:
            ```
            [5]
            ```
            or for multiple footer rows:
            ```
            [5, 6]
            ```
            (All other rows not in thead will automatically go into tbody)
            """,
            "fix_type": "row_structure",
            "container": "tbody",
        },
        # Heading remediation templates
        "skipped_heading_level": """
        You are an accessibility expert tasked with fixing skipped heading levels.
        
        A proper heading structure should not skip levels (e.g., h1 to h3 without h2).
        Please provide HTML for an appropriate intermediate heading that:
        1. Maintains document outline structure
        2. Provides meaningful context
        3. Bridges the gap between heading levels
        
        RESPONSE FORMAT:
        ```html
        <h2>Your appropriate heading text here</h2>
        ```
        """,
        "empty_heading_content": """
        You are an accessibility expert tasked with improving empty or generic heading content.
        
        Please generate appropriate heading text that:
        1. Is descriptive and meaningful
        2. Fits within the document context
        3. Properly represents the section content
        4. Follows heading best practices
        
        RESPONSE FORMAT:
        ```
        Your descriptive heading text here
        ```
        """,
        # Document structure templates
        "missing_document_title": """
        You are an accessibility expert tasked with creating a document title.
        
        Please generate a title that:
        1. Clearly describes the document's content
        2. Is concise but informative
        3. Matches the main heading when appropriate
        4. Follows title best practices
        
        RESPONSE FORMAT:
        ```html
        <title>Your document title here</title>
        ```
        """,
        # Form remediation templates
        "missing_form_label": """
        You are an accessibility expert tasked with adding proper form labels.
        
        Please generate a label that:
        1. Clearly describes the form control's purpose
        2. Is concise but descriptive
        3. Uses natural language
        4. Follows form labeling best practices
        
        RESPONSE FORMAT:
        ```html
        <label for="input-id">Your label text here</label>
        ```
        """,
        "missing_fieldset": """
        You are an accessibility expert tasked with grouping form controls.
        
        Please provide fieldset and legend markup that:
        1. Logically groups related form controls
        2. Has a descriptive legend
        3. Follows form grouping best practices
        
        RESPONSE FORMAT:
        ```html
        <fieldset>
            <legend>Your legend text here</legend>
            [form controls will be wrapped here]
        </fieldset>
        ```
        """,
        "improper_figure_structure": """
        You are an accessibility expert tasked with fixing figure structure.
        
        Please provide figure markup that:
        1. Properly wraps the image
        2. Includes a descriptive figcaption
        3. Maintains semantic meaning
        4. Follows figure element best practices
        
        RESPONSE FORMAT:
        ```html
        <figure>
            [image will be placed here]
            <figcaption>Your caption text here</figcaption>
        </figure>
        ```
        """,
        # Existing templates
        "missing_alt_text": """
        You are an accessibility expert tasked with generating alt text for an image.
        
        Please generate concise, descriptive alt text for this image that:
        1. Describes the essential content and function of the image
        2. Is typically under 125 characters
        3. Does not begin with "image of" or "picture of"
        4. Considers the context where the image appears
        
        RESPONSE FORMAT:
        ```
        alt="Your descriptive alt text here"
        ```
        """,
        "empty_alt_text": """
        You are an accessibility expert tasked with determining if an image is decorative or informative.
        
        For this image with empty alt text:
        1. If the image appears to be decorative (not conveying content), confirm it should remain with empty alt text
        2. If the image conveys information, generate appropriate alt text
        
        RESPONSE FORMAT:
        If decorative:
        ```
        role="presentation"
        ```
        
        If informative:
        ```
        alt="Your descriptive alt text here"
        ```
        """,
        "generic_alt_text": """
        You are an accessibility expert tasked with improving generic alt text.
        
        The current alt text is too generic. Please generate more specific, descriptive alt text that:
        1. Describes the essential content and function of the image
        2. Is typically under 125 characters
        3. Does not begin with "image of" or "picture of"
        4. Considers the context where the image appears
        
        RESPONSE FORMAT:
        ```
        alt="Your improved alt text here"
        ```
        """,
        "long_alt_text": """
        You are an accessibility expert tasked with making alt text more concise.
        
        The current alt text is too long. Please create a shorter version that:
        1. Preserves the essential information
        2. Is under 125 characters
        3. Is clear and descriptive
        
        RESPONSE FORMAT:
        ```
        alt="Your concise alt text here"
        ```
        """,
    }

    return templates.get(issue_type, "")


def format_remediation_prompt(template: str, issue: dict, context: str = "") -> str:
    """
    Format a remediation prompt with issue-specific information.

    Args:
        template: The template string
        issue: The accessibility issue data
        context: Additional context information

    Returns:
        Formatted prompt string
    """
    prompt = template.strip()

    # Add issue description
    if "description" in issue:
        prompt += f"\n\nISSUE: {issue['description']}"

    # Add element HTML
    if "element" in issue:
        prompt += f"\n\nELEMENT HTML:\n{issue['element']}"

    # Add context if provided
    if context:
        prompt += f"\n\nCONTEXT:\n{context}"

    return prompt
