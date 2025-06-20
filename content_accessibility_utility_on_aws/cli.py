# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Command-line interface for the document_accessibility package.

This module provides a command-line interface for PDF to HTML conversion,
accessibility auditing, and accessibility remediation.
"""

import os
import sys
import argparse
import logging
import json
import tempfile
import zipfile
from typing import Dict, Any

from content_accessibility_utility_on_aws import __version__
from content_accessibility_utility_on_aws.api import generate_remediation_report
from content_accessibility_utility_on_aws.remediate.remediation_strategies.table_remediation_direct import (
    ensure_table_structure,
)
from content_accessibility_utility_on_aws.remediate.remediation_strategies.table_detection import (
    preprocess_tables,
)
from content_accessibility_utility_on_aws.api import (
    convert_pdf_to_html,
    audit_html_accessibility,
    remediate_html_accessibility,
)
from content_accessibility_utility_on_aws.utils.logging_helper import setup_logger
from content_accessibility_utility_on_aws.utils.config import config_manager, load_config_file, ConfigurationError

# Set up module-level logger
logger = setup_logger(__name__)


def get_default_output_path(
    input_path: str, command: str, output_format: str = None
) -> str:
    """Generate default output path based on input path and command."""
    input_base = os.path.splitext(os.path.basename(input_path))[0]

    if command == "convert":
        return os.path.join(".", f"{input_base}_converted")
    elif command == "audit":
        # Use the appropriate extension for the audit report format
        ext = output_format if output_format in ["json", "html", "text"] else "json"
        return os.path.join(".", f"audit_report.{ext}")
    elif command == "remediate":
        return os.path.join(".", f"{input_base}_remediated.html")
    elif command == "process":
        return os.path.join(".", f"{input_base}_processed")

    return os.path.join(".", f"{input_base}_output")


def configure_logging(debug: bool = False, quiet: bool = False) -> None:
    """Configure logging based on debug and quiet flags."""
    if quiet:
        logging.basicConfig(level=logging.ERROR)
    elif debug:
        logging.basicConfig(level=logging.DEBUG)
        # Force DEBUG level on all document_accessibility loggers
        for name in logging.Logger.manager.loggerDict:
            if name.startswith("document_accessibility"):
                logger_obj = logging.getLogger(name)
                logger_obj.setLevel(logging.DEBUG)
                for handler in logger_obj.handlers:
                    handler.setLevel(logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)


def _add_standardized_arguments(parser: argparse.ArgumentParser) -> None:
    """Add standardized arguments that are common across all commands."""
    # Input/Output arguments
    parser.add_argument(
        "--input", "-i", required=True, help="Input file or directory path"
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output file or directory path. If not provided, uses default based on command",
    )

    # Common options
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Only output reports, suppress other output",
    )
    parser.add_argument("--config", "-c", help="Path to configuration file")
    # Add save-config parameter to save current configuration
    parser.add_argument(
        "--save-config", 
        metavar="CONFIG_PATH",
        help="Save current configuration to the specified file path"
    )
    # Add AWS profile parameter
    parser.add_argument("--profile", help="AWS profile name to use for credentials")
    # Add S3 bucket parameter as a standardized parameter
    parser.add_argument("--s3-bucket", help="Name of an existing S3 bucket to use")

    # AWS/BDA options
    parser.add_argument(
        "--bda-project-arn", help="ARN of an existing BDA project to use"
    )
    parser.add_argument(
        "--create-bda-project",
        action="store_true",
        help="Create a new BDA project if needed",
    )


def _add_convert_arguments(parser: argparse.ArgumentParser) -> None:
    """Add PDF conversion arguments to the convert command parser."""
    # Add standardized arguments
    _add_standardized_arguments(parser)

    # Convert-specific options
    parser.add_argument(
        "--format",
        "-f",
        choices=["html", "md"],
        default="html",
        help="Output format for conversion",
    )
    parser.add_argument(
        "--single-file", action="store_true", help="Generate a single output file"
    )
    parser.add_argument(
        "--single-page",
        action="store_true",
        help="Combine all pages into a single HTML document",
    )
    parser.add_argument(
        "--multi-page", action="store_true", help="Keep pages as separate HTML files"
    )
    parser.add_argument(
        "--continuous",
        action="store_true",
        default=True,
        help="Use continuous scrolling in single file mode",
    )

    # Image options
    parser.add_argument(
        "--extract-images",
        action="store_true",
        default=True,
        help="Extract and include images from the PDF",
    )
    parser.add_argument(
        "--image-format",
        choices=["png", "jpg", "webp"],
        default="png",
        help="Format for extracted images",
    )
    parser.add_argument(
        "--embed-images", action="store_true", help="Embed images as data URIs in HTML"
    )
    parser.add_argument(
        "--exclude-images",
        action="store_true",
        help="Do not include images in the output",
    )


def _add_audit_arguments(parser: argparse.ArgumentParser) -> None:
    """Add accessibility audit arguments to the audit command parser."""
    # Add standardized arguments
    _add_standardized_arguments(parser)

    # Audit-specific options
    parser.add_argument(
        "--format",
        "-f",
        choices=["json", "html", "text"],
        default="json",
        help="Output format for audit report",
    )
    parser.add_argument("--checks", help="Comma-separated list of checks to run")
    parser.add_argument(
        "--severity",
        choices=["minor", "major", "critical"],
        default="minor",
        help="Minimum severity level to include in report",
    )
    parser.add_argument(
        "--detailed",
        action="store_true",
        default=True,
        help="Include detailed context information in report",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Only include summary information in report",
    )


def _add_remediate_arguments(parser: argparse.ArgumentParser) -> None:
    """Add accessibility remediation arguments to the remediate command parser."""
    # Add standardized arguments
    _add_standardized_arguments(parser)

    # Remediate-specific options
    parser.add_argument(
        "--auto-fix",
        action="store_true",
        help="Automatically fix issues where possible",
    )
    parser.add_argument(
        "--max-issues",
        type=int,
        help="Maximum number of issues to remediate (default: all)",
    )
    parser.add_argument(
        "--single-page",
        action="store_true",
        help="Combine all pages into a single HTML document",
    )
    parser.add_argument(
        "--multi-page", action="store_true", help="Keep pages as separate HTML files"
    )
    parser.add_argument(
        "--model-id",
        default="us.amazon.nova-lite-v1:0",
        help="Bedrock model ID to use for remediation",
    )
    parser.add_argument(
        "--severity-threshold",
        choices=["minor", "major", "critical"],
        default="minor",
        help="Minimum severity level of issues to remediate",
    )
    parser.add_argument(
        "--audit-report", help="Path to audit report JSON file to use for remediation"
    )
    parser.add_argument(
        "--generate-report",
        action="store_true",
        default=True,
        help="Generate a remediation report after remediation",
    )
    parser.add_argument(
        "--report-format",
        choices=["html", "json", "text"],
        default="html",
        help="Format for the remediation report",
    )
    # Unified reports are now the default, no need for a flag


def _add_process_arguments(parser: argparse.ArgumentParser) -> None:
    """Add arguments for the full processing pipeline command."""
    # Add standardized arguments
    _add_standardized_arguments(parser)

    # Process-specific options
    parser.add_argument("--skip-audit", action="store_true", help="Skip the audit step")
    parser.add_argument(
        "--skip-remediation", action="store_true", help="Skip the remediation step"
    )
    parser.add_argument(
        "--single-page",
        action="store_true",
        help="Combine all pages into a single HTML document",
    )
    parser.add_argument(
        "--multi-page", action="store_true", help="Keep pages as separate HTML files"
    )
    parser.add_argument(
        "--audit-format",
        choices=["json", "html", "text"],
        default="json",
        help="Format for the audit report",
    )

    # Add conversion options
    parser.add_argument(
        "--format",
        "-f",
        choices=["html", "md", "json"],
        default="html",
        help="Output format for conversion",
    )
    parser.add_argument(
        "--single-file", action="store_true", help="Generate a single output file"
    )
    parser.add_argument(
        "--continuous",
        action="store_true",
        default=True,
        help="Use continuous scrolling in single file mode",
    )
    parser.add_argument(
        "--extract-images",
        action="store_true",
        default=True,
        help="Extract and include images from the PDF",
    )
    parser.add_argument(
        "--image-format",
        choices=["png", "jpg", "webp"],
        default="png",
        help="Format for extracted images",
    )
    parser.add_argument(
        "--embed-images", action="store_true", help="Embed images as data URIs in HTML"
    )
    parser.add_argument(
        "--exclude-images",
        action="store_true",
        help="Do not include images in the output",
    )

    # Add audit options
    parser.add_argument(
        "--checks", help="Comma-separated list of checks to run for audit"
    )
    parser.add_argument(
        "--detailed",
        action="store_true",
        default=True,
        help="Include detailed context information in audit report",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Only include summary information in audit report",
    )

    # Add remediation options
    parser.add_argument(
        "--max-issues",
        type=int,
        help="Maximum number of issues to remediate (default: all)",
    )
    parser.add_argument(
        "--model-id",
        default="us.amazon.nova-lite-v1:0",
        help="Bedrock model ID to use for remediation",
    )

    # Shared options
    parser.add_argument(
        "--severity",
        choices=["minor", "major", "critical"],
        default="minor",
        help="Minimum severity level for audit and remediation",
    )
    parser.add_argument(
        "--auto-fix",
        action="store_true",
        help="Automatically fix issues where possible",
    )
    parser.add_argument(
        "--unified-report",
        action="store_true",
        help="Generate a unified report that combines audit and remediation data",
    )


def create_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Convert PDF documents to accessible HTML and remediate accessibility issues.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Convert command
    convert_parser = subparsers.add_parser(
        "convert",
        help="Convert PDF to HTML",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    _add_convert_arguments(convert_parser)

    # Audit command
    audit_parser = subparsers.add_parser(
        "audit",
        help="Audit HTML for accessibility issues",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    _add_audit_arguments(audit_parser)

    # Remediate command
    remediate_parser = subparsers.add_parser(
        "remediate",
        help="Remediate accessibility issues in HTML",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    _add_remediate_arguments(remediate_parser)

    # Process command
    process_parser = subparsers.add_parser(
        "process",
        help="Full workflow: convert PDF, audit, and remediate",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    _add_process_arguments(process_parser)

    # Version information
    parser.add_argument(
        "--version", action="store_true", help="Show version information"
    )

    return parser


def parse_arguments() -> Dict[str, Any]:
    """Parse command-line arguments and prepare configuration dictionaries."""
    parser = create_parser()
    args = parser.parse_args()

    # Show version if requested
    if args.version:
        print(f"Document Accessibility v{__version__}")
        sys.exit(0)

    # If no command specified, show help and exit
    if args.command is None and not args.version:
        parser.print_help()
        sys.exit(0)

    # Configure logging based on debug and quiet flags
    configure_logging(debug=args.debug, quiet=args.quiet)

    # Convert namespace to dictionary
    args_dict = vars(args)
    
    # Load configuration from file if specified
    if args_dict.get("config"):
        config_path = args_dict["config"]
        try:
            # Load configuration from file
            logger.info(f"Loading configuration from {config_path}")
            config_data = load_config_file(config_path)
            
            # Update configuration for each section
            for section in ["pdf", "audit", "remediate", "aws"]:
                if section in config_data:
                    config_manager.set_user_config(config_data[section], section)
                    logger.debug(f"Applied configuration for section: {section}")
            
            # Handle top-level configuration (not in a section)
            top_level = {k: v for k, v in config_data.items() 
                         if k not in ["pdf", "audit", "remediate", "aws"]}
            if top_level:
                config_manager.set_user_config(top_level)
                logger.debug("Applied top-level configuration")
                
        except ConfigurationError as e:
            logger.error(f"Configuration error: {e}")
            print(f"Error: {e}")
            sys.exit(1)

    # Set default output path if not provided
    if args.command and not args_dict.get("output"):
        args_dict["output"] = get_default_output_path(
            args_dict["input"], args.command, args_dict.get("format")
        )

    return args_dict


def save_configuration_from_args(args_dict: Dict[str, Any]) -> None:
    """
    Save configuration to file based on command-line arguments.
    
    Args:
        args_dict: Dictionary of command-line arguments
    """
    from content_accessibility_utility_on_aws.utils.config import save_config, config_manager
    
    # Get the configuration file path
    config_path = args_dict.get("save_config")
    if not config_path:
        return
        
    # Determine format based on file extension
    file_format = "yaml"
    if config_path.lower().endswith(".json"):
        file_format = "json"
    
    # Organize parameters into appropriate sections
    config = {
        "pdf": {},
        "audit": {},
        "remediate": {},
        "aws": {}
    }
    
    # PDF conversion parameters
    pdf_params = [
        "extract_images", "image_format", "single_file", "single_page", 
        "multi_page", "continuous", "embed_images", "exclude_images", 
        "embed_fonts", "inline_css", "cleanup_bda_output"
    ]
    
    for param in pdf_params:
        if param in args_dict and args_dict[param] is not None:
            config["pdf"][param] = args_dict[param]
    
    # Audit parameters
    audit_params = [
        "severity", "detailed", "summary_only", "checks", "skip_automated_checks"
    ]
    
    for param in audit_params:
        if param in args_dict and args_dict[param] is not None:
            # Rename parameters for consistency with config structure
            if param == "severity":
                config["audit"]["severity_threshold"] = args_dict[param]
            elif param == "detailed":
                config["audit"]["detailed_context"] = args_dict[param]
            elif param == "checks":
                # Convert comma-separated checks to list
                if args_dict[param]:
                    config["audit"]["issue_types"] = [
                        t.strip() for t in args_dict[param].split(",")
                    ]
            else:
                config["audit"][param] = args_dict[param]
    
    # Remediation parameters
    remediate_params = [
        "severity_threshold", "auto_fix", "max_issues", "model_id", 
        "issue_types", "report_format"
    ]
    
    for param in remediate_params:
        if param in args_dict and args_dict[param] is not None:
            # Special handling for severity if using the shared parameter
            if param == "severity" and "severity_threshold" not in args_dict:
                config["remediate"]["severity_threshold"] = args_dict[param]
            else:
                config["remediate"][param] = args_dict[param]
    
    # AWS parameters
    aws_params = [
        "s3_bucket", "bda_project_arn", "create_bda_project", 
        "bda_project_name", "profile"
    ]
    
    for param in aws_params:
        if param in args_dict and args_dict[param] is not None:
            config["aws"][param] = args_dict[param]
    
    # Apply the config manager's defaults to empty sections
    for section in config:
        if not config[section]:
            config[section] = config_manager.get_config(section=section)
        else:
            # Merge with defaults for the section
            section_defaults = config_manager.get_config(section=section)
            for key, value in section_defaults.items():
                if key not in config[section]:
                    config[section][key] = value
    
    # Save the configuration
    try:
        save_config(config, config_path, file_format=file_format)
        print(f"Configuration saved to {config_path}")
    except Exception as e:
        logger.error(f"Error saving configuration: {e}")
        print(f"Error saving configuration: {e}")


def run_convert_command(args: Dict[str, Any]) -> int:
    """Run the PDF conversion command."""
    try:
        # Prepare options
        options = {
            "extract_images": args.get("extract_images", True),
            "image_format": args.get("image_format", "png"),
            "single_file": args.get("single_file", False),
            "single_page": args.get("single_page", False),
            "multi_page": args.get("multi_page", False),
            "continuous": args.get("continuous", True),
            "embed_images": args.get("embed_images", False),
            "exclude_images": args.get("exclude_images", False),
        }

        if not args.get("quiet"):
            logger.info("Converting PDF to HTML: %s", args["input"])

        result = convert_pdf_to_html(
            pdf_path=args["input"],
            output_dir=args["output"],
            options=options,
            bda_project_arn=args.get("bda_project_arn"),
            create_bda_project=args.get("create_bda_project", False),
            s3_bucket=args.get("s3_bucket"),
        )

        if not args.get("quiet"):
            print("\nConversion Results:")
            print(f"  Main HTML: {result['html_path']}")
            print(f"  Total HTML files: {len(result.get('html_files', []))}")
            print(f"  Total image files: {len(result.get('image_files', []))}")

        return 0

    except Exception as e:
        logger.error(f"Error in PDF conversion: {e}")
        if not args.get("quiet"):
            print(f"Error: {e}")
        return 1


def run_audit_command(args: Dict[str, Any]) -> int:
    """Run the accessibility audit command."""
    try:
        # Get report format
        report_format = args.get("format", "json")

        # Prepare options
        options = {
            "severity_threshold": args.get("severity", "minor"),
            "detailed": args.get("detailed", True),
            "report_format": report_format,
            "summary_only": args.get("summary_only", False),
        }

        if args.get("checks"):
            options["issue_types"] = [t.strip() for t in args["checks"].split(",")]

        if not args.get("quiet"):
            logger.info(f"Auditing HTML for accessibility: {args['input']}")

        # Normalize and validate output path
        output_path = args["output"]
        if not output_path:
            output_path = get_default_output_path(args["input"], "audit")

        # Ensure output path has the correct extension
        if os.path.isdir(output_path):
            output_path = os.path.join(output_path, f"audit_report.{report_format}")
        else:
            # Strip any existing extension and add the correct one
            base_name = os.path.splitext(output_path)[0]
            output_path = f"{base_name}.{report_format}"

        # Create output directory if needed
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        logger.debug(f"Will save audit report to: {output_path}")

        # Run the audit
        result = audit_html_accessibility(
            html_path=args["input"], options=options, output_path=output_path
        )

        if not args.get("quiet"):
            print("\nAudit Results:")
            print(result["report"])

        return 0

    except Exception as e:
        logger.error(f"Error in accessibility audit: {e}")
        if not args.get("quiet"):
            print(f"Error: {e}")
        return 1


def run_remediate_command(args: Dict[str, Any]) -> int:
    """Run the accessibility remediation command."""
    try:
        # Prepare options
        options = {
            "severity_threshold": args.get("severity_threshold", "minor"),
            "auto_fix": args.get("auto_fix", True),  # Set auto_fix to True by default
            "max_issues": args.get("max_issues"),
            "model_id": args.get("model_id"),
            "single_page": args.get("single_page", False),
            "multi_page": args.get("multi_page", False),
            "profile": args.get("profile"),  # Pass the profile parameter
        }

        if not args.get("quiet"):
            logger.info("Remediating HTML: %s", args["input"])

        # Load audit report if provided or look for default location
        audit_report = None
        audit_report_path = None

        # Use the specified audit report path if provided
        if args.get("audit_report"):
            audit_report_path = args["audit_report"]
            logger.debug(f"Using specified audit report path: {audit_report_path}")
        else:
            # Otherwise, try to find the default audit report
            input_path = args["input"]
            input_dir = (
                os.path.dirname(input_path)
                if os.path.isfile(input_path)
                else input_path
            )

            # Look for audit_report.json in the input directory
            default_report_path = os.path.join(input_dir, "audit_report.json")
            if os.path.exists(default_report_path):
                audit_report_path = default_report_path
                logger.debug(f"Found default audit report at: {audit_report_path}")

                # Also look for the standard output directory structure from the process command
                if not os.path.exists(default_report_path):
                    parent_dir = os.path.dirname(input_dir)
                    if os.path.exists(os.path.join(parent_dir, "audit_report.json")):
                        audit_report_path = os.path.join(
                            parent_dir, "audit_report.json"
                        )
                        logger.debug(
                            f"Found audit report in parent directory: {audit_report_path}"
                        )

        # Load the audit report if a path was found
        if audit_report_path:
            try:
                with open(audit_report_path, "r", encoding="utf-8") as f:
                    audit_report = json.load(f)
                # Filter audit report to only include issues that need remediation
                if audit_report:
                    audit_report = {
                        "issues": [
                            issue
                            for issue in audit_report.get("issues", [])
                            if issue.get("remediation_status") == "needs_remediation"
                        ],
                        "summary": audit_report.get("summary", {}),
                    }
                    if not args.get("quiet"):
                        logger.debug(
                            "Loaded audit report from %s with "
                            + "%s remediable issues",
                            audit_report_path,
                            len(audit_report["issues"]),
                        )
            except Exception as e:
                logger.error(
                    f"Error loading audit report from {audit_report_path}: {e}"
                )
                if not args.get("quiet"):
                    print(f"Error loading audit report: {e}")

        result = remediate_html_accessibility(
            html_path=args["input"],
            output_path=args["output"],
            audit_report=audit_report,
            options=options,
        )

        # Generate remediation report if requested
        if args.get("generate_report", True):

            # Determine report path
            output_dir = os.path.dirname(args["output"])
            report_path = os.path.join(output_dir, "remediation_report")

            # Add appropriate extension based on format
            report_format = args.get("report_format", "html")
            if report_format == "html":
                report_path += ".html"
            elif report_format == "json":
                report_path += ".json"
            elif report_format == "text":
                report_path += ".txt"

            if not args.get("quiet"):
                logger.info(f"Generating remediation report: {report_path}")

            # Generate the report
            generate_remediation_report(
                remediation_data=result,
                output_path=report_path,
                report_format=report_format,
            )

            # Add report path to result
            result["report_path"] = report_path

        if not args.get("quiet"):
            print("\nRemediation Results:")
            print(f"  Issues processed: {result.get('issues_processed', 0)}")
            print(f"  Issues remediated: {result.get('issues_remediated', 0)}")
            print(f"  Issues failed: {result.get('issues_failed', 0)}")
            print(f"  Remediated HTML: {result['remediated_html_path']}")
            if result.get("report_path"):
                print(f"  Remediation report: {result['report_path']}")

        return 0

    except Exception as e:
        logger.error(f"Error in accessibility remediation: {e}")
        if not args.get("quiet"):
            print(f"Error: {e}")
        return 1


def run_process_command(args: Dict[str, Any]) -> int:
    """Run the full processing pipeline command."""
    try:
        # Extract profile if provided
        profile = args.get("profile")

        # Create a temporary directory for processing
        import tempfile
        temp_output_dir = tempfile.mkdtemp(prefix="accessibility_")
        logger.debug(f"Created temporary directory for processing: {temp_output_dir}")
        
        # Store the original output directory for later
        final_output_dir = args["output"]
        
        # Use the temporary directory for processing
        args["output"] = temp_output_dir
        output_dir = temp_output_dir
        
        os.makedirs(output_dir, exist_ok=True)

        # Step 1: Convert PDF to HTML
        if not args.get("quiet"):
            logger.info("Step 1/3: Converting PDF to HTML: %s", args["input"])

        convert_options = {
            "extract_images": args.get("extract_images", True),
            "image_format": args.get("image_format", "png"),
            "single_file": args.get("single_file", False),
            "single_page": args.get("single_page", False),
            "multi_page": args.get("multi_page", False),
            "continuous": args.get("continuous", True),
            "embed_images": args.get("embed_images", False),
            "exclude_images": args.get("exclude_images", False),
            "profile": profile,  # Add profile to conversion options
        }

        convert_result = convert_pdf_to_html(
            pdf_path=args["input"],
            output_dir=os.path.join(output_dir, "html"),
            options=convert_options,
            bda_project_arn=args.get("bda_project_arn"),
            create_bda_project=args.get("create_bda_project", False),
            s3_bucket=args.get("s3_bucket"),
            profile=profile,
        )

        html_path = convert_result["html_path"]

        if not args.get("quiet"):
            print("\nConversion Results:")
            print(f"  Main HTML: {html_path}")
            print(f"  Total HTML files: {len(convert_result.get('html_files', []))}")
            print(f"  Total image files: {len(convert_result.get('image_files', []))}")

        # Step 2: Audit HTML (unless skipped)
        if not args.get("skip_audit"):
            if not args.get("quiet"):
                logger.info("Step 2/3: Auditing HTML for accessibility")

            # Use the same options as the standalone audit command
            audit_format = args.get("audit_format", "json")
            audit_options = {
                "severity_threshold": args.get("severity", "minor"),
                "detailed": args.get("detailed", True),
                "report_format": audit_format,
                "summary_only": args.get("summary_only", False),
            }

            # Add issue types if specified
            if args.get("checks"):
                audit_options["issue_types"] = [
                    t.strip() for t in args["checks"].split(",")
                ]

            # Save the audit report with the appropriate file extension
            audit_output = os.path.join(output_dir, f"audit_report.{audit_format}")

            audit_result = audit_html_accessibility(
                html_path=html_path, options=audit_options, output_path=audit_output
            )

            if not args.get("quiet"):
                print("\nAudit Results:")
                print(audit_result["report"])
        else:
            audit_result = None
            if not args.get("quiet"):
                logger.info("Audit step skipped as requested")

        # Step 3: Remediate HTML (unless skipped)
        remediate_result = {}
        if not args.get("skip_remediation") and audit_result:

            if not args.get("quiet"):
                logger.info("Step 3/3: Remediating HTML")

            # Use the same options as the standalone remediate command
            remediate_options = {
                "severity_threshold": args.get("severity", "minor"),
                "auto_fix": args.get(
                    "auto_fix", True
                ),  # Set auto_fix to True by default
                "max_issues": args.get("max_issues"),
                "model_id": args.get("model_id"),
                "single_page": args.get("single_page", False),
                "multi_page": args.get("multi_page", False),
                "profile": profile,  # Add profile to remediation options
            }

            if args.get("multi_page", False):
                remediate_output = os.path.join(output_dir, "remediated_html")
            else:
                base_name = os.path.splitext(os.path.basename(html_path))[0]
                remediate_output = (
                    os.path.join(output_dir, "remediated_document.html")
                    if args.get("single_page", False)
                    else os.path.join(output_dir, f"remediated_{base_name}.html")
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
                logger.info(
                    "Filtered audit report to %d issues that need remediation",
                    len(filtered_audit_report["issues"]),
                )

            remediate_result = remediate_html_accessibility(
                html_path=html_path,
                audit_report=filtered_audit_report,
                output_path=remediate_output,
                options=remediate_options,
            )

        # Apply enhanced table remediation

        if not args.get("skip_remediation", False):
            # Get the path to the remediated HTML
            remediated_path = remediate_result.get("remediated_html_path", "")
            if remediated_path and os.path.exists(remediated_path):
                if not args.get("quiet"):
                    logger.info(
                        "Applying enhanced table remediation to fix common issues"
                    )

                if os.path.isfile(remediated_path):
                    # For single file output
                    try:
                        with open(remediated_path, "r", encoding="utf-8") as f:
                            html_content = f.read()

                        # First preprocess tables to identify and convert header-like cells
                        html_content = preprocess_tables(html_content)

                        # Then apply direct table structure fixes
                        fixed_html = ensure_table_structure(html_content)

                        with open(remediated_path, "w", encoding="utf-8") as f:
                            f.write(fixed_html)

                        if not args.get("quiet"):
                            logger.info(
                                f"Enhanced table structure fixes applied to {remediated_path}"
                            )
                    except Exception as e:
                        logger.error(f"Error applying enhanced table remediation: {e}")

                elif os.path.isdir(remediated_path):
                    # For multi-page output
                    for root, _, files in os.walk(remediated_path):
                        for file in files:
                            if file.lower().endswith(".html"):
                                file_path = os.path.join(root, file)
                                try:
                                    with open(file_path, "r", encoding="utf-8") as f:
                                        html_content = f.read()

                                    # First preprocess tables to identify
                                    # and convert header-like cells
                                    html_content = preprocess_tables(html_content)

                                    # Then apply direct table structure fixes
                                    fixed_html = ensure_table_structure(html_content)

                                    with open(file_path, "w", encoding="utf-8") as f:
                                        f.write(fixed_html)

                                    if not args.get("quiet"):
                                        logger.debug(
                                            f"Enhanced table structure fixes applied to {file}"
                                        )
                                except Exception as e:
                                    logger.error(
                                        f"Error applying enhanced table remediation to {file}: {e}"
                                    )

            # Use the format parameter to determine the report format, defaulting to html
            report_format = args.get("format", "html")
            if (
                report_format == "md"
            ):  # If markdown was selected, use html for the report
                report_format = "html"

            # Determine report path with the appropriate extension
            report_path = os.path.join(
                output_dir, f"remediation_report.{report_format}"
            )

            if not args.get("quiet"):
                logger.info(f"Generating remediation report: {report_path}")

            # Generate the report
            generate_remediation_report(
                remediation_data=remediate_result,
                output_path=report_path,
                report_format=report_format,
            )

            # Add report path to result
            remediate_result["report_path"] = report_path

            if not args.get("quiet"):
                print("\nRemediation Results:")
                print(
                    f"  Issues processed: {remediate_result.get('issues_processed', 0)}"
                )
                print(
                    f"  Issues remediated: {remediate_result.get('issues_remediated', 0)}"
                )
                print(f"  Issues failed: {remediate_result.get('issues_failed', 0)}")

                # Add detailed information about which issue types were processed
                if remediate_result.get("file_results"):
                    issue_types_remediated = set()
                    for file_result in remediate_result.get("file_results", []):
                        for detail in file_result.get("details", []):
                            if detail.get("remediated"):
                                issue_types_remediated.add(detail.get("type"))

                    if issue_types_remediated:
                        print(
                            f"  Issue types remediated: {', '.join(sorted(issue_types_remediated))}"
                        )

                # Show failed issue types if any
                if remediate_result.get("failed_issue_types"):
                    print(
                        "  Failed issue types:"
                        + f"{', '.join(sorted(remediate_result.get('failed_issue_types')))}"
                    )

                print(
                    f"  Remediated HTML: {remediate_result.get('remediated_html_path', 'N/A')}"
                )
        elif not args.get("skip_remediation"):
            if not args.get("quiet"):
                logger.info("Remediation step skipped (no audit result available)")
        else:
            if not args.get("quiet"):
                logger.info("Remediation step skipped as requested")

        # Zip all output files into a single zip file
        from content_accessibility_utility_on_aws.utils.path_utils import zip_output_files
        try:
            # Get the input filename without extension
            input_filename = os.path.splitext(os.path.basename(args["input"]))[0]
            zip_filename = os.path.join(final_output_dir, f"{input_filename}.zip")
            
            # Collect all output files and folders to include in the zip
            output_files = []
            
            # Add the HTML folder
            html_dir = os.path.join(output_dir, "html")
            if os.path.exists(html_dir):
                output_files.append(html_dir)
            
            # Add the remediated HTML folder or file
            remediated_path = remediate_result.get("remediated_html_path", "")
            if remediated_path and os.path.exists(remediated_path):
                output_files.append(remediated_path)
                
                # Always upload remediated HTML to S3 if a bucket is available
                # (either from args or environment variable)
                try:
                    import tempfile
                    import zipfile
                    from content_accessibility_utility_on_aws.batch.common import upload_to_s3
                    
                    # Get S3 bucket from args or environment variable
                    s3_bucket = args.get("s3_bucket")
                    if not s3_bucket:
                        s3_bucket = os.environ.get("BDA_S3_BUCKET")
                        if s3_bucket:
                            logger.debug(f"Using S3 bucket from environment variable: {s3_bucket}")
                    
                    if s3_bucket:
                        # Create a temporary zip file for the remediated content
                        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_zip_file:
                            temp_zip_path = temp_zip_file.name
                        
                        # Get the base name of the input file for the zip filename
                        input_base_name = os.path.splitext(os.path.basename(args["input"]))[0]
                        remediated_zip_filename = f"{input_base_name}_remediated.zip"
                        
                        # Create the zip file
                        with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                            # Determine if remediated_path is a directory or file
                            if os.path.isdir(remediated_path):
                                # Add all files in the directory to the zip
                                for root, _, files in os.walk(remediated_path):
                                    for file in files:
                                        file_path = os.path.join(root, file)
                                        # Calculate relative path within the directory
                                        rel_path = os.path.relpath(file_path, remediated_path)
                                        zipf.write(file_path, rel_path)
                                        logger.debug(f"Added to zip: {rel_path}")
                            else:
                                # Add single file to the zip
                                zipf.write(remediated_path, os.path.basename(remediated_path))
                                logger.debug(f"Added to zip: {os.path.basename(remediated_path)}")
                        
                        # Upload the zip file to S3
                        s3_key = f"remediated/{remediated_zip_filename}"
                        
                        upload_to_s3(
                            local_path=temp_zip_path,
                            bucket=s3_bucket,
                            key=s3_key,
                            metadata={"content-type": "application/zip"}
                        )
                        
                        if not args.get("quiet"):
                            print(f"\nUploaded remediated HTML as zip to s3://{s3_bucket}/{s3_key}")
                        
                        # Clean up the temporary zip file
                        try:
                            os.unlink(temp_zip_path)
                        except Exception as e:
                            logger.warning(f"Failed to delete temporary zip file: {e}")
                    else:
                        logger.debug("No S3 bucket available for upload (not specified and no environment variable)")
                
                except Exception as e:
                    logger.error(f"Error uploading remediated HTML to S3: {e}")
                    if not args.get("quiet"):
                        print(f"\nWarning: Failed to upload remediated HTML to S3: {e}")
            
            # Add the audit report
            audit_output = os.path.join(output_dir, f"audit_report.{args.get('audit_format', 'json')}")
            if os.path.exists(audit_output):
                output_files.append(audit_output)
            
            # Add the remediation report
            report_format = args.get("format", "html")
            if report_format == "md":
                report_format = "html"
            remediation_report = os.path.join(output_dir, f"remediation_report.{report_format}")
            if os.path.exists(remediation_report):
                output_files.append(remediation_report)
            
            # Create the zip file
            if output_files:
                zip_path = zip_output_files(output_files, zip_filename)
                if not args.get("quiet"):
                    print(f"\nAll output files zipped to: {zip_path}")
        except Exception as e:
            logger.error(f"Error zipping output files: {e}")
            if not args.get("quiet"):
                print(f"\nWarning: Failed to zip output files: {e}")
                
        # Clean up the temporary directory
        try:
            import shutil
            shutil.rmtree(temp_output_dir)
            logger.debug(f"Cleaned up temporary directory: {temp_output_dir}")
        except Exception as e:
            logger.error(f"Error cleaning up temporary directory: {e}")

        if not args.get("quiet"):
            print("\nProcess completed successfully!")
            print(f"All output files are in: {zip_filename}")

        return 0

    except Exception as e:
        logger.error(f"Error in processing pipeline: {e}")
        if not args.get("quiet"):
            print(f"Error: {e}")
        return 1


def main() -> int:
    """Main entry point for the CLI."""
    try:
        args = parse_arguments()

        # Save configuration if requested
        save_configuration_from_args(args)

        if args["command"] == "convert":
            return run_convert_command(args)
        elif args["command"] == "audit":
            return run_audit_command(args)
        elif args["command"] == "remediate":
            return run_remediate_command(args)
        elif args["command"] == "process":
            return run_process_command(args)
        else:
            print("No command specified")
            return 1

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
