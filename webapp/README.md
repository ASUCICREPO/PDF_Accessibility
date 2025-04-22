<!--
 Copyright 2025 Amazon.com, Inc. or its affiliates.
 SPDX-License-Identifier: Apache-2.0
-->

# Document Accessibility Streamlit Application

This is a modular Streamlit application for processing PDF documents through the accessibility pipeline. It provides a web interface for:
- Converting PDFs to HTML
- Auditing accessibility issues
- Remediating accessibility issues
- Generating comprehensive reports

## Architecture

The application has been designed with a modular structure for maintainability and extensibility:

```
streamlit/
├── app.py                   # Main application entry point
├── config.py                # Configuration management
├── utils/                   # Utility modules
│   ├── aws_utils.py         # AWS credential and service helpers
│   ├── file_utils.py        # File handling utilities
│   └── session_utils.py     # Streamlit session state management
├── components/              # UI components
│   └── sidebar.py           # Sidebar controls and options
├── views/                   # Display views
│   ├── audit_view.py        # Audit results display
│   ├── remediation_view.py  # Remediated output display
│   └── report_view.py       # Report generation and display
├── processors/              # File processing logic
│   ├── pdf_processor.py     # PDF specific processing
│   ├── html_processor.py    # HTML specific processing
│   └── zip_processor.py     # ZIP archive processing
└── ui_helpers/              # UI helper components
    ├── html_preview.py      # HTML content preview
    ├── charts.py            # Visualization components
    └── download_helpers.py  # Download button utilities
```

## Running the Application

From the project root directory:

```bash
streamlit run streamlit/app.py
```

## Features

### File Support
- **PDF**: Converts to HTML, audits for accessibility issues, and remediates them
- **HTML**: Directly audits and remediates accessibility issues
- **ZIP**: Process multiple HTML files in a single archive

### Processing Options
- **Processing Mode**: Choose between conversion only, audit only, or full processing
- **PDF to HTML Options**: Extract images, select image format, generate multiple HTML files
- **Audit Options**: Select which accessibility aspects to check and severity threshold
- **Remediation Options**: Choose which types of issues to fix

### Results Display
- **Audit Results**: Detailed breakdown of accessibility issues by type
- **Remediated Output**: Preview of the remediated HTML with embedded resources
- **Remediation Report**: Statistics on fixes applied and remaining issues

## AWS Requirements

PDF to HTML conversion requires the following environment variables to be set:
- `DOCUMENT_ACCESSIBILITY_S3_BUCKET`: S3 bucket for temporary storage
- `DOCUMENT_ACCESSIBILITY_BDA_PROJECT_ARN`: (Optional) BDA project ARN

HTML and ZIP files can be processed without AWS credentials.

## Development

To add new features or modify existing ones:

1. **Adding a new processor**: Create a new file in `processors/` following the pattern of existing processors
2. **Adding a new view**: Create a new file in `views/` and update `app.py` to include it
3. **Enhancing UI**: Modify files in `ui_helpers/` or `components/` as needed
