<!--
 Copyright 2025 Amazon.com, Inc. or its affiliates.
 SPDX-License-Identifier: Apache-2.0
-->

# Accessibility Remediation

This document explains the accessibility remediation capabilities of the PDF to HTML conversion library, which uses Bedrock models to automatically fix common accessibility issues in generated HTML.

## Overview

The accessibility remediation functionality:

1. Uses the accessibility audit results to identify WCAG 2.1 compliance issues
2. Creates specialized prompts for each issue type (alt text, page titles, ARIA attributes, etc.)
3. Sequentially processes issues through Bedrock models to generate fixes
4. Applies the fixes to the HTML directly
5. Produces a detailed report of successful and failed remediations

## Using the Remediation Functionality

### From the Command Line

You can remediate accessibility issues in two ways:

1. **As part of PDF conversion**:
   ```bash
   document-accessibility process --input path/to/input.pdf --output output/ --perform-remediation
   ```

2. **For an existing HTML file with an audit report**:
   ```bash
   document-accessibility remediate --input path/to/existing.html --output remediated.html
   ```

#### Available CLI Options

```
Accessibility remediation options:
  --auto-fix           Automatically fix issues where possible
  --max-issues MAX_ISSUES
                      Maximum number of issues to remediate
  --model-id MODEL_ID  Bedrock model ID to use for remediation
  --severity-threshold {critical,major,minor}
                      Minimum severity level to remediate. Default: minor
  --issue-types ISSUE_TYPES
                      Comma-separated list of specific issue types to remediate (e.g., missing-alt-text,empty-alt-text)
```

### From Python Code

```python
from document_accessibility.api import remediate_html_accessibility

# After performing an accessibility audit that generates an audit report:
remediation_result = remediate_html_accessibility(
    html_path='path/to/file.html',
    audit_report=audit_report,  # Dictionary from accessibility auditor
    image_dir='path/to/images_folder',  # For image-related issues
    output_path='path/to/output.html',  # Where to save remediated HTML
    options={
        'model_id': 'amazon.nova-lite-v1:0',
        'max_issues': 10,  # Limit number of issues to process
        'issue_types': ['missing-alt-text', 'empty-alt-text'],  # Only process specific issues
        'severity_threshold': 'major'  # Only 'major' and 'critical' issues
    }
)

print(f"Remediated {remediation_result['issues_remediated']} issues")
```

## Issue Types and Templates

The remediation process uses specialized templates for common accessibility issues. Currently supported issue types include:

| Issue Type | Description | WCAG Criterion |
|------------|-------------|----------------|
| `missing-alt-text` | Images missing alternative text | 1.1.1 |
| `empty-alt-text` | Non-decorative images with empty alt text | 1.1.1 |
| `missing-title` | Document missing a title element | 2.4.2 |
| `skipped-heading-level` | Heading levels that skip (e.g., h1 to h3) | 1.3.1 |
| `empty-heading` | Headings with no content | 1.3.1 |
| `table-missing-headers` | Tables without headers | 1.3.1 |
| `th-missing-scope` | Table headers missing scope attribute | 1.3.1 |
| Various ARIA issues | Improper ARIA attribute usage | 4.1.1, 4.1.2 |
| Various form issues | Form fields missing labels or accessible names | 1.3.1, 3.3.2 |

The system can process additional issue types using a generic remediation template, but specialized templates provide better results.

## Processing Order and Image Handling

Issues are processed sequentially, one by one, as required by some Bedrock models that have stateful processing. For image-related issues like missing alt text:

1. The system tries to locate the image file if available
2. If found, the image data is included in the prompt to the model
3. The model analyzes the image content to generate appropriate alternative text

## Example Workflow

A complete remediation workflow typically includes:

1. Converting a PDF to HTML (`convert_pdf_to_html`)
2. Auditing for accessibility issues (`audit_html_accessibility`)
3. Remediating the identified issues (`remediate_html_accessibility`)

See the `tests/test_accessibility_remediation.py` script for a complete example.

## Advanced Usage

### Custom Models

You can specify different Bedrock model IDs for remediation:

```bash
document-accessibility remediate --input document.html --output remediated.html --model-id amazon.nova-lite-v1:0
```

### Filtered Remediation

Process only specific issue types:

```bash
document-accessibility remediate --input document.html --output remediated.html --issue-types missing-alt-text,empty-alt-text
```

### Severity-Based Remediation

Focus on the most important issues:

```bash
document-accessibility remediate --input document.html --output remediated.html --severity-threshold critical
```

## Limitations

1. Some complex issues may not be successfully remediated
2. Image-based alt text generation requires the image files to be accessible
3. Context-dependent issues may have limited remediation success
4. The sequential processing can be slower for documents with many issues
