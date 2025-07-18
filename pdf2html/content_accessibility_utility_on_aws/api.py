# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Web Content Accessibility with AWS API.

This module provides the primary entry points for the document accessibility package,
including PDF to HTML conversion, accessibility auditing, and accessibility remediation.
"""

import os
from typing import Dict, Any, Optional

from content_accessibility_utility_on_aws.utils.logging_helper import (
    setup_logger,
    handle_exception,
    DocumentAccessibilityError,
    AccessibilityAuditError,
    AccessibilityRemediationError,
)
from content_accessibility_utility_on_aws.utils.config import config_manager
from content_accessibility_utility_on_aws.utils.resources import ensure_directory
from content_accessibility_utility_on_aws.utils.usage_tracker import SessionUsageTracker

# Set up module-level logger
logger = setup_logger(__name__, level="INFO")


def process_pdf_accessibility(
    pdf_path: str,
    output_dir: Optional[str] = None,
    conversion_options: Optional[Dict[str, Any]] = None,
    audit_options: Optional[Dict[str, Any]] = None,
    remediation_options: Optional[Dict[str, Any]] = None,
    perform_audit: bool = True,
    perform_remediation: bool = False,
    usage_data_bucket: Optional[str] = None,
    usage_data_bucket_prefix: Optional[str] = None,
    profile: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Process a PDF document through the full accessibility pipeline.

    Args:
        pdf_path: Path to the PDF file.
        output_dir: Directory to save output files.
        conversion_options: Options for PDF to HTML conversion.
        audit_options: Options for accessibility auditing.
        remediation_options: Options for accessibility remediation.
        perform_audit: Whether to perform accessibility audit.
        perform_remediation: Whether to perform accessibility remediation.
        usage_data_bucket: S3 bucket to store usage data
        usage_data_bucket_prefix: Optional prefix for the S3 key path
        profile: AWS profile name to use for credentials

    Returns:
        Dictionary containing processing results:
            - 'conversion_result': Results from PDF to HTML conversion.
            - 'audit_result': Results from accessibility audit (if performed).
            - 'remediation_result': Results from accessibility remediation (if performed).

    Raises:
        FileNotFoundError: If the PDF file doesn't exist.
        DocumentAccessibilityError: If there's an error during processing.
    """
    try:
        # Verify PDF file exists
        if not os.path.isfile(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        # Create output directory if needed
        if output_dir:
            ensure_directory(output_dir)

        # Initialize result dictionary
        result = {}

        # Step 1: Convert PDF to HTML
        logger.debug(f"Converting PDF to HTML: {pdf_path}")
        conversion_result = convert_pdf_to_html(
            pdf_path=pdf_path, output_dir=output_dir, options=conversion_options
        )
        result["conversion_result"] = conversion_result

        # Get the main HTML file path from conversion result
        html_path = conversion_result.get("html_path")
        if not html_path or not os.path.exists(html_path):
            raise DocumentAccessibilityError(
                f"HTML output not found after conversion: {html_path}"
            )

        # Step 2: Perform accessibility audit if requested
        if perform_audit:
            # Determine if we should use single-page or multi-page mode
            if not audit_options:
                audit_options = {}

            # Check if explicit mode flags are set
            is_single_page = audit_options.get("single_page", False)
            is_multi_page = audit_options.get("multi_page", False)

            # Determine image directory
            image_dir = None
            if conversion_result.get("image_dir"):
                image_dir = conversion_result["image_dir"]
            elif (
                conversion_result.get("image_files")
                and len(conversion_result["image_files"]) > 0
            ):
                image_dir = os.path.dirname(conversion_result["image_files"][0])

            # Get the extracted_html directory
            html_dir = os.path.dirname(html_path)

            # Check for extracted_html directory
            extracted_html_dir = os.path.join(output_dir, "extracted_html")
            if os.path.isdir(extracted_html_dir):
                # If we have an extracted_html directory, use it as the image_dir
                image_dir = extracted_html_dir
                logger.debug(
                    f"Using extracted_html directory for images: {extracted_html_dir}"
                )

            # If multi-page mode is set, use the directory for audit
            if is_multi_page:
                if os.path.isdir(html_dir):
                    html_path = html_dir
                    logger.debug(f"Using directory for multi-page mode: {html_dir}")
            # If no explicit mode is set, auto-detect based on conversion output
            elif not is_single_page:
                if len(conversion_result.get("html_files", [])) > 1:
                    # If we have multiple HTML files, use the directory as html_path
                    html_path = html_dir
                    audit_options["multi_page"] = True
                    logger.debug(
                        f"Auto-detected multi-page mode for audit with directory: {html_dir}"
                    )

            # Set output path for audit report
            audit_output_path = None
            if output_dir:
                audit_output_path = os.path.join(output_dir, "accessibility_audit.json")

            # Run the audit
            logger.debug(f"Auditing HTML for accessibility: {html_path}")
            audit_result = audit_html_accessibility(
                html_path=html_path,
                image_dir=image_dir,
                options=audit_options,
                output_path=audit_output_path,
            )
            result["audit_result"] = audit_result

            # Step 3: Perform accessibility remediation if requested
            if perform_remediation:
                logger.debug(f"Remediating HTML accessibility: {html_path}")

                # If no explicit remediation options are set, copy from audit options
                if not remediation_options:
                    remediation_options = {}

                # Copy mode flags from audit options if not explicitly set
                if (
                    audit_options.get("single_page")
                    and "single_page" not in remediation_options
                ):
                    remediation_options["single_page"] = True
                if (
                    audit_options.get("multi_page")
                    and "multi_page" not in remediation_options
                ):
                    remediation_options["multi_page"] = True

                # Determine page mode based on flags
                if remediation_options.get("multi_page", False):
                    # For multi-page mode, use the directory of HTML files
                    if os.path.isdir(html_dir):
                        html_path = html_dir
                    remediation_output_path = os.path.join(
                        output_dir, "remediated_html"
                    )
                    ensure_directory(remediation_output_path)
                    logger.debug(f"Using multi-page mode with directory: {html_dir}")
                elif remediation_options.get("single_page", False):
                    # Handle single-page mode by combining all HTML files into one
                    from content_accessibility_utility_on_aws.utils.html_utils import (
                        combine_html_files,
                    )

                    # Get all HTML files from the extracted_html directory
                    html_files = []
                    if os.path.isdir(html_dir):
                        for file in os.listdir(html_dir):
                            if file.lower().endswith(".html"):
                                html_files.append(os.path.join(html_dir, file))

                    # Sort the HTML files to ensure correct order
                    html_files.sort()

                    if html_files:
                        # Create a combined HTML file
                        combined_html_path = os.path.join(
                            output_dir, "combined_document.html"
                        )
                        logger.debug(
                            f"Combining {len(html_files)} HTML files into a single document for single-page mode"
                        )
                        combine_html_files(html_files, combined_html_path)

                        # Update the html_path to use the combined file
                        html_path = combined_html_path
                        remediation_output_path = os.path.join(
                            output_dir, "remediated_combined_document.html"
                        )
                else:
                    # Default to multi-page mode if neither flag is set
                    if os.path.isdir(html_dir):
                        html_path = html_dir
                    remediation_output_path = os.path.join(
                        output_dir, "remediated_html"
                    )
                    ensure_directory(remediation_output_path)
                    logger.debug("Defaulting to multi-page mode")

                # Run the remediation
                from content_accessibility_utility_on_aws.remediate.api import (
                    remediate_html_accessibility as remediate_impl,
                )

                # Ensure we're using the extracted_html directory for images
                extracted_html_dir = os.path.join(output_dir, "extracted_html")
                if os.path.isdir(extracted_html_dir):
                    image_dir = extracted_html_dir
                    logger.debug(
                        f"Using extracted_html directory for remediation images: {extracted_html_dir}"
                    )

                # Filter the audit report to only include issues that need remediation
                filtered_audit_report = None
                if audit_result:
                    filtered_audit_report = {
                        "issues": [
                            issue
                            for issue in audit_result.get("issues", [])
                            if issue.get("remediation_status") == "needs_remediation"
                        ],
                        "summary": audit_result.get("summary", {}),
                    }
                    logger.debug(
                        f"Filtered audit report to {len(filtered_audit_report['issues'])} issues that need remediation"
                    )

                remediation_result = remediate_impl(
                    html_path=html_path,
                    audit_report=filtered_audit_report,
                    options=remediation_options,
                    output_path=remediation_output_path,
                    image_dir=image_dir,
                )
                result["remediation_result"] = remediation_result

                # Generate remediation report if remediation was performed
                if remediation_result:
                    remediation_report_path = os.path.join(
                        output_dir,
                        f"remediation_report.{remediation_options.get('format', 'html')}",
                    )
                    logger.debug(
                        f"Generating remediation report: {remediation_report_path}"
                    )

                    # Generate the remediation report
                    generate_remediation_report(
                        remediation_data=remediation_result,
                        output_path=remediation_report_path,
                        report_format=remediation_options.get("format", "html"),
                    )

                    # Add report path to result
                    result["remediation_report_path"] = remediation_report_path

        # Save usage data locally or to S3
        try:
            # Default to saving in the output directory if one is provided
            local_path = None
            if output_dir:
                local_path = os.path.join(output_dir, "usage_data.json")
                
            # Save data and get the path
            usage_data_path = save_usage_data(
                output_path=local_path,
                usage_data_bucket=usage_data_bucket,
                usage_data_bucket_prefix=usage_data_bucket_prefix,
                profile=profile
            )
            
            if usage_data_path:
                if usage_data_bucket and usage_data_path.startswith("s3://"):
                    result["usage_data_s3_uri"] = usage_data_path
                elif local_path:
                    result["usage_data_path"] = usage_data_path
                    
                logger.info(f"Usage data saved to {usage_data_path}")
        except Exception as e:
            logger.warning(f"Failed to save usage data: {e}")
            # Continue with the normal return - don't fail if usage tracking fails

        return result

    except FileNotFoundError:
        raise
    except Exception as e:
        handle_exception(
            e,
            logger,
            custom_message=f"Error processing PDF accessibility: {pdf_path}",
            custom_exception=DocumentAccessibilityError,
        )


def convert_pdf_to_html(
    pdf_path: str,
    output_dir: Optional[str] = None,
    options: Optional[Dict[str, Any]] = None,
    bda_project_arn: Optional[str] = None,
    create_bda_project: bool = False,
    s3_bucket: Optional[str] = None,
    profile: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Convert a PDF document to HTML using Bedrock Data Automation.

    Args:
        pdf_path: Path to the PDF file.
        output_dir: Directory to save HTML files. If None, a temporary
            directory will be used and the path will be returned.
        options: Conversion options. Available options:
            - extract_images (bool): Whether to extract and embed images. Default: True.
            - image_format (str): Format for extracted images ('jpg', 'png'). Default: 'png'.
            - embed_fonts (bool): Whether to embed fonts. Default: False.
            - page_range (tuple): Range of pages to convert (start, end). Default: All pages.
            - multiple_documents (bool): Generate multiple HTML files (one per page). Default: False.
            - continuous (bool): For single document mode, use continuous scrolling. Default: True.
            - inline_css (bool): Use inline styling instead of external stylesheet. Default: False.
            - embed_images (bool): Embed images as data URIs in HTML. Default: False.
            - exclude_images (bool): Do not include images in the output. Default: False.
            - bda_project_name (str): Name for new BDA project if created. Default: Auto-generated.
            - bda_profile_name (str): Name for new BDA profile if created. Default: Auto-generated.
            - audit_accessibility (bool): Whether to perform an accessibility audit. Default: False.
            - audit_options (dict): Options for accessibility auditing. Default: {}.
            - cleanup_bda_output (bool): Whether to remove BDA output files after processing. Default: False.
        bda_project_arn: ARN of an existing BDA project to use.
        create_bda_project: Whether to create a new BDA project.
        s3_bucket: Name of an existing S3 bucket to use for file uploads.
        profile: AWS profile name to use for credentials.

    Returns:
        Dictionary containing conversion results:
            - 'html_path': Path to the main HTML file.
            - 'html_files': List of paths to all generated HTML files.
            - 'image_files': List of paths to all generated image files.
            - 'is_image_only': Whether the PDF is image-only.
            - 'temp_dir': Path to the temporary directory if output_dir was None.

    Raises:
        FileNotFoundError: If the PDF file doesn't exist.
        DocumentAccessibilityError: If there's an error during conversion.
    """
    from content_accessibility_utility_on_aws.pdf2html.api import (
        convert_pdf_to_html as pdf2html_convert,
    )

    return pdf2html_convert(
        pdf_path=pdf_path,
        output_dir=output_dir,
        options=options,
        bda_project_arn=bda_project_arn,
        create_bda_project=create_bda_project,
        s3_bucket=s3_bucket,
        profile=profile,
    )


def audit_html_accessibility(
    html_path: str,
    image_dir: Optional[str] = None,
    options: Optional[Dict[str, Any]] = None,
    output_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Audit an HTML document for accessibility issues.

    Args:
        html_path: Path to the HTML file.
        image_dir: Directory containing images referenced in the HTML.
        options: Audit options including:
            - check_images (bool): Whether to check images for accessibility. Default: True.
            - check_headings (bool): Whether to check heading structure. Default: True.
            - check_links (bool): Whether to check link text and targets. Default: True.
            - check_tables (bool): Whether to check table structure. Default: True.
            - check_forms (bool): Whether to check form controls. Default: True.
            - check_color_contrast (bool): Whether to check color contrast. Default: True.
            - check_landmarks (bool): Whether to check ARIA landmarks. Default: True.
            - check_keyboard_nav (bool): Whether to check keyboard navigation. Default: True.
            - check_alt_text (bool): Whether to check alt text quality. Default: True.
            - check_pdf_tags (bool): Whether to check PDF tag structure. Default: True.
            - severity_threshold (str): Minimum severity level to report. Default: 'warning'.
            - max_issues (int): Maximum number of issues to report. Default: None (all).
            - include_help (bool): Whether to include remediation help. Default: True.
            - include_code (bool): Whether to include code snippets. Default: True.
            - include_context (bool): Whether to include surrounding context. Default: True.
            - single_page (bool): Force treating html_path as a single file. Default: None (auto-detect).
            - multi_page (bool): Force treating html_path as a directory. Default: None (auto-detect).
        output_path: Path to save the audit report JSON file.

    Returns:
        Dictionary containing audit results:
            - 'issues': List of accessibility issues found.
            - 'summary': Summary of audit results.
            - 'report_path': Path to the saved report file.

    Raises:
        FileNotFoundError: If the HTML file doesn't exist.
        AccessibilityAuditError: If there's an error during auditing.
    """
    try:
        # Verify HTML file or directory exists
        if not os.path.exists(html_path):
            raise FileNotFoundError(f"HTML path not found: {html_path}")

        # Get configuration with user options merged
        audit_config = config_manager.get_config(user_options=options, section="audit")

        # Create output directory if needed
        if output_path:
            ensure_directory(os.path.dirname(output_path))

        # Call the implementation function
        from content_accessibility_utility_on_aws.audit.api import (
            audit_html_accessibility as audit_impl,
        )

        result = audit_impl(
            html_path=html_path,
            image_dir=image_dir,
            options=audit_config,
            output_path=output_path,
        )

        return result

    except FileNotFoundError:
        raise
    except Exception as e:
        handle_exception(
            e,
            logger,
            custom_message="Error auditing HTML accessibility",
            custom_exception=AccessibilityAuditError,
        )


def remediate_html_accessibility(
    html_path: str,
    audit_report: Optional[Dict[str, Any]] = None,
    options: Optional[Dict[str, Any]] = None,
    output_path: Optional[str] = None,
    image_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Remediate accessibility issues in an HTML document.

    Args:
        html_path: Path to the HTML file or directory of HTML files.
        audit_report: Optional audit report from audit_html_accessibility().
        options: Remediation options including:
            - auto_fix (bool): Whether to automatically fix issues. Default: True.
            - fix_images (bool): Whether to fix image issues. Default: True.
            - fix_headings (bool): Whether to fix heading structure. Default: True.
            - fix_links (bool): Whether to fix link issues. Default: True.
            - fix_tables (bool): Whether to fix table issues. Default: True.
            - fix_forms (bool): Whether to fix form issues. Default: True.
            - fix_landmarks (bool): Whether to fix landmark issues. Default: True.
            - fix_keyboard_nav (bool): Whether to fix keyboard nav issues. Default: True.
            - fix_alt_text (bool): Whether to fix alt text issues. Default: True.
            - fix_pdf_tags (bool): Whether to fix PDF tag issues. Default: True.
            - severity_threshold (str): Minimum severity to fix. Default: 'warning'.
            - max_fixes (int): Maximum number of fixes to apply. Default: None (all).
            - interactive (bool): Whether to prompt for confirmation. Default: False.
            - single_page (bool): Force treating html_path as a single file. Default: None (auto-detect).
            - multi_page (bool): Force treating html_path as a directory. Default: None (auto-detect).
        output_path: Path to save the remediated HTML file.
        image_dir: Directory containing images referenced in the HTML.

    Returns:
        Dictionary containing remediation results:
            - 'fixed_issues': List of issues that were fixed.
            - 'remaining_issues': List of issues that couldn't be fixed.
            - 'summary': Summary of remediation results.
            - 'output_path': Path to the remediated HTML file.

    Raises:
        FileNotFoundError: If the HTML file doesn't exist.
        AccessibilityRemediationError: If there's an error during remediation.
    """
    try:
        # Verify HTML file or directory exists
        if not os.path.exists(html_path):
            raise FileNotFoundError(f"HTML path not found: {html_path}")

        # Get configuration with user options merged
        remediation_config = config_manager.get_config(
            user_options=options, section="remediation"
        )

        # Create output directory if needed
        if output_path:
            ensure_directory(os.path.dirname(output_path))

        # Call the implementation function
        from content_accessibility_utility_on_aws.remediate.api import (
            remediate_html_accessibility as remediate_impl,
        )

        result = remediate_impl(
            html_path=html_path,
            audit_report=audit_report,
            options=remediation_config,
            output_path=output_path,
            image_dir=image_dir,
        )

        return result

    except FileNotFoundError:
        raise
    except Exception as e:
        handle_exception(
            e,
            logger,
            custom_message="Error remediating HTML accessibility",
            custom_exception=AccessibilityRemediationError,
        )


def save_usage_data(
    output_path: Optional[str] = None,
    usage_data_bucket: Optional[str] = None,
    usage_data_bucket_prefix: Optional[str] = None,
    profile: Optional[str] = None,
) -> Optional[str]:
    """
    Save the current session usage data to a file or S3 bucket.
    
    If both output_path and usage_data_bucket are provided, data will be saved to both locations.

    Args:
        output_path: Local path to save the usage data JSON file
        usage_data_bucket: S3 bucket to store usage data
        usage_data_bucket_prefix: Optional prefix for the S3 key path
        profile: AWS profile name to use for credentials

    Returns:
        Path to the saved file (local or S3 URI) or None if no output location is provided

    Raises:
        DocumentAccessibilityError: If there's an error saving usage data
    """
    try:
        # If no output location is specified, don't save
        if not output_path and not usage_data_bucket:
            return None

        # Finalize the session
        usage_tracker = SessionUsageTracker.get_instance()
        usage_tracker.finalize_session()
        
        result_path = None

        # Save to local file if output_path is provided
        if output_path:
            try:
                file_path = usage_tracker.save_to_file(output_path)
                logger.info(f"Usage data saved to local file: {file_path}")
                result_path = file_path
            except Exception as e:
                logger.warning(f"Failed to save usage data to local file: {e}")
                # Continue with S3 upload if requested, don't fail completely

        # Save to S3 if bucket is provided
        if usage_data_bucket:
            try:
                s3_uri = usage_tracker.save_to_s3(
                    bucket_name=usage_data_bucket,
                    prefix=usage_data_bucket_prefix,
                    profile=profile
                )
                logger.info(f"Usage data saved to S3: {s3_uri}")
                result_path = s3_uri
            except Exception as e:
                logger.warning(f"Failed to save usage data to S3: {e}")
                # If we already saved locally, don't fail completely
                if output_path is None:
                    raise
        
        return result_path
        
    except Exception as e:
        handle_exception(
            e,
            logger,
            custom_message="Error saving usage data",
            custom_exception=DocumentAccessibilityError,
        )


def generate_remediation_report(
    remediation_data: Dict[str, Any], output_path: str, report_format: str = "html"
) -> Dict[str, Any]:
    """
    Generate a report from remediation results.

    Args:
        remediation_data: Dictionary containing remediation results
        output_path: Path to save the report
        report_format: Format of the report ('html', 'json', or 'text')

    Returns:
        Dictionary containing the report data or text content

    Raises:
        FileNotFoundError: If the output directory doesn't exist and can't be created
        ValueError: If the report format is not supported
        DocumentAccessibilityError: If there's an error generating the report
    """
    try:
        # Create output directory if needed
        if output_path:
            ensure_directory(os.path.dirname(output_path))

        # Call the implementation function
        from content_accessibility_utility_on_aws.remediate.remediation_report_generator import (
            generate_remediation_report as generate_remediation_report_impl,
        )

        result = generate_remediation_report_impl(
            remediation_data=remediation_data,
            output_path=output_path,
            report_format=report_format,
        )

        return result

    except ValueError:
        raise
    except FileNotFoundError:
        raise
    except Exception as e:
        handle_exception(
            e,
            logger,
            custom_message="Error generating remediation report",
            custom_exception=DocumentAccessibilityError,
        )
