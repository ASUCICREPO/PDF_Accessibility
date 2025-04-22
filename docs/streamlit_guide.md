<!--
 Copyright 2025 Amazon.com, Inc. or its affiliates.
 SPDX-License-Identifier: Apache-2.0
-->

# Document Accessibility Streamlit Interface Guide

This guide provides instructions for setting up and using the Document Accessibility web interface powered by Streamlit.

## Table of Contents
- [Overview](#overview)
- [Installation & Setup](#installation--setup)
- [Configuration](#configuration)
- [Using the Interface](#using-the-interface)
- [Processing Options](#processing-options)
- [Viewing Results](#viewing-results)
- [Usage Tracking & Cost Analysis](#usage-tracking--cost-analysis)
- [Troubleshooting](#troubleshooting)

## Overview

The Document Accessibility Streamlit interface provides a user-friendly web application for converting, auditing, and remediating PDF documents. It offers the following features:

- PDF file upload and processing
- HTML file direct upload for audit and remediation
- ZIP archive processing for batch operations
- Configurable processing options
- Interactive results display with tabbed interface
- Accessibility audit result visualization
- Remediated HTML preview
- Detailed remediation reports
- Download options for processed files

## Installation & Setup

### Prerequisites

- **AWS Account**: Ensure you have an AWS account with appropriate permissions.
- **S3 Bucket**: Create an S3 bucket for storing input and output files.
  ```bash
  aws s3 mb s3://my-accessibility-bucket
  ```
- **BDA Project**: Set up an AWS Bedrock Data Automation (BDA) project.
  ```bash
  aws bedrock-data-automation create-data-automation-project \
      --project-name my-accessibility-project \
      --standard-output-configuration '{"document":{"outputFormat":{"textFormat":{"types":["HTML"]}}}}'
  ```
  Note the `projectArn` from the output.

- **AWS CLI Configuration**: Configure AWS credentials and default region.
  ```bash
  aws configure
  ```

- Python 3.11 or higher
- AWS credentials
- An S3 bucket for storage
- AWS Bedrock Data Automation (BDA) project for PDF processing
- Access to AWS Bedrock models for remediation



### Installation

1. Install the Document Accessibility package:
   ```bash
   pip install document-accessibility
   pip install streamlit
   ```

2. Configure AWS credentials:
   ```bash
   aws configure
   ```

### Starting the Application

Run the Streamlit interface:

```bash
streamlit run /path/to/content-accessibility-with-aws/streamlit_app.py
```

This will launch a local web server and open the application in your default browser.

## Configuration

### Environment Variables

The Streamlit app uses the following environment variables:

| Variable | Description | Required for PDF Processing |
|----------|-------------|:--------------------------:|
| `BDA_S3_BUCKET` or `DOCUMENT_ACCESSIBILITY_S3_BUCKET` | S3 bucket name | Yes |
| `BDA_PROJECT_ARN` or `DOCUMENT_ACCESSIBILITY_BDA_PROJECT_ARN` | BDA project ARN | No (Optional) |
| `AWS_PROFILE` | AWS profile name | No (Optional) |
| `CONTENT_ACCESSIBILITY_WORK_DIR` | Directory for temporary files | No (Default: system temp) |

Example setup:

```bash
# Set required environment variables
export BDA_S3_BUCKET=my-accessibility-bucket
export BDA_PROJECT_ARN=arn:aws:bedrock:us-west-2:123456789012:project/my-bda-project
export CONTENT_ACCESSIBILITY_WORK_DIR=/path/to/work/directory
```

### Debug Mode

Enable debug mode through the AWS Configuration panel in the sidebar for troubleshooting.

## Using the Interface

### File Upload

1. Use the file uploader in the sidebar to upload documents:
   - PDF files (.pdf): For full conversion, audit, and remediation
   - HTML files (.html): For direct audit and remediation
   - ZIP archives (.zip): For batch processing of multiple HTML files

2. Select the appropriate processing mode based on your file type:
   - For PDFs: 
     - Convert Only
     - Convert + Audit
     - Full Processing (convert, audit, remediate)
   - For HTML/ZIP:
     - Audit Only
     - Audit + Remediate

### Processing Options

The sidebar contains expandable sections for configuring different aspects of processing:

#### AWS Configuration

- Displays current S3 bucket and BDA project settings
- Shows configuration status indicators
- Allows enabling debug mode for troubleshooting

#### PDF to HTML Options
- Extract images: Enable/disable image extraction
- Image format: Choose between PNG, JPG, and WebP formats
- Generate multiple HTML files: Toggle between single file and multi-file output

#### Audit Options
- Content type checks: Enable/disable specific check categories
- Severity threshold: Set minimum severity level (minor, major, critical)

#### Remediation Options
- Fix categories: Select which issue types to remediate
- Auto-fix: Enable automatic remediation
- Model ID: Select Bedrock model to use for remediation
- Severity threshold: Set minimum severity level for remediation

## Viewing Results

After processing, results are displayed in a tabbed interface:

### Audit Results Tab

Displays accessibility issues found in the document:
- Summary statistics showing total issues, compliant elements, and issues needing remediation
- Issues organized by type in expandable sections
- Detailed information for each issue:
  - Severity level (with color coding)
  - Element type affected
  - Page number
  - WCAG criterion and description
  - HTML snippet (expandable)
  - Remediation help text

### Remediated Output Tab

Displays the remediated HTML content:
- Interactive HTML preview of the remediated document
- Page selector for multi-page documents
- Expandable HTML code view
- Download button for remediated files

### Remediation Report Tab

Shows detailed information about the remediation process:
- Remediation statistics
- Success rate progress bar
- Severity breakdown
- Issue type breakdown
- Detailed issue list with filters for:
  - Status (All, Remediated, Failed)
  - Severity (All, Critical, Major, Minor)
- Before/After HTML comparison for each remediated issue
- Download options for HTML and JSON reports

### Usage Data Tab

Provides comprehensive analysis of resource usage and costs:
- Processing metrics summary (duration, documents, pages)
- BDA usage statistics and visualizations
- Bedrock API usage by model and purpose
- Cost analysis based on configurable rates
- Interactive charts showing token distribution and cost breakdown

## Usage Tracking & Cost Analysis

The Document Accessibility tool now includes comprehensive usage tracking and cost analysis features:

### Cost Calculation Options

In the sidebar, you'll find a "Cost Calculation Options" section where you can configure:
- Cost per page in BDA ($): Price per page processed through Bedrock Data Automation
- Cost per 1K input tokens ($): Price per 1,000 input tokens for Bedrock models
- Cost per 1K output tokens ($): Price per 1,000 output tokens for Bedrock models

These rates are used to calculate the estimated cost of processing documents, which is displayed in the Usage Data tab.

### Usage Metrics Tracked

The system tracks multiple usage metrics:
- **BDA Usage**:
  - Total pages processed
  - Number of documents processed
  - Processing time and BDA project ARN
  
- **Bedrock API Usage**:
  - Input and output token counts
  - API calls categorized by purpose (alt text generation, table remediation, etc.)
  - Model-specific usage statistics
  - Processing time per call

### Visualization and Analysis

The Usage Data tab provides multiple views of your usage data:
1. **Summary**: High-level overview of usage metrics and estimated costs
2. **BDA Usage**: Detailed breakdown of document and page processing
3. **Bedrock Usage**: Token usage by model and purpose with visualizations
4. **Cost Analysis**: Comprehensive cost breakdown with charts showing distribution by service and purpose

### Data Storage and Access

Usage data is automatically saved as `usage_data.json` in your output directory. This data can also be saved to an S3 bucket for centralized storage and analysis by configuring the appropriate parameters in the API.

## Troubleshooting

### Common Issues

#### AWS Configuration Errors

If you see an error about S3 bucket not being configured:
1. Set the required environment variables
2. Restart the Streamlit application
3. Verify the configuration status in the AWS Configuration panel

#### PDF Processing Failures

If PDF processing fails:
1. Check AWS credentials and permissions
2. Verify S3 bucket exists and is accessible
3. Enable debug mode to see detailed error messages
4. Consider uploading HTML directly if PDF processing continues to fail

#### Memory Issues with Large Documents

For large documents:
1. Set `CONTENT_ACCESSIBILITY_WORK_DIR` to a location with ample disk space
2. Process the document in smaller chunks if possible
3. Increase available memory for the Streamlit process

### Getting Help

If you encounter persistent issues:
1. Enable debug mode to capture detailed logs
2. Check the terminal window where Streamlit is running for error messages
3. Refer to the [project documentation](https://github.com/yourusername/document-accessibility) for further assistance
