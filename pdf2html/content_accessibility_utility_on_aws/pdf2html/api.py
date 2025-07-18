# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
PDF to HTML conversion API.

This module provides functionality for converting PDF documents to HTML.
"""

import os
import tempfile
import shutil
import contextlib
from typing import Dict, List, Any, Optional

from content_accessibility_utility_on_aws.utils.logging_helper import (
    setup_logger,
    handle_exception,
    DocumentAccessibilityError,
)
from content_accessibility_utility_on_aws.utils.resources import ensure_directory
from content_accessibility_utility_on_aws.pdf2html.services.bedrock_client import (
    ExtendedBDAClient,
    resolve_bda_project,
)
from content_accessibility_utility_on_aws.pdf2html.utils.pdf_utils import is_image_only_pdf

# Set up module-level logger
logger = setup_logger(__name__)


@contextlib.contextmanager
def temp_directory(prefix=None, suffix=None, file_dir=None, use_cwd=False, cleanup=True):
    """
    Context manager for creating and cleaning up a temporary directory.

    Args:
        prefix: Prefix for the directory name
        suffix: Suffix for the directory name
        dir: Parent directory to create the temp directory in
        use_cwd: Whether to use the current working directory instead of the system temp dir
        cleanup: Whether to clean up the directory when done

    Yields:
        str: Path to the temporary directory
    """
    if use_cwd:
        file_dir = os.getcwd()

    temp_dir = tempfile.mkdtemp(suffix=suffix, prefix=prefix, dir=file_dir)
    try:
        yield temp_dir
    finally:
        if cleanup:
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                logger.warning(
                    f"Failed to clean up temporary directory {temp_dir}: {e}"
                )


def cleanup_output_files(
    output_dir: str, single_file: bool, multiple_documents: bool
) -> None:
    """
    Clean up output files based on the conversion mode.

    Args:
        output_dir: Directory containing the output files
        single_file: Whether single file mode is enabled
        multiple_documents: Whether multiple documents mode is enabled
    """
    html_dir = os.path.join(output_dir, "extracted_html")
    if not os.path.exists(html_dir):
        logger.warning(f"HTML directory not found: {html_dir}")
        return

    # Log the current cleanup mode
    logger.debug(
        f"Cleaning up output files. Mode: single_file={single_file}, multiple_documents={multiple_documents}"
    )

    if single_file:
        # In single file mode, keep remediated.html and remove page-X.html files
        logger.debug(
            "Single-page mode: keeping combined remediated.html and removing individual page files"
        )
        for file in os.listdir(html_dir):
            if file.startswith("page-") and file.endswith(".html"):
                try:
                    os.remove(os.path.join(html_dir, file))
                    logger.debug(
                        f"Removed individual page file in single file mode: {file}"
                    )
                except Exception as e:
                    logger.warning(f"Failed to remove individual page file {file}: {e}")
    else:
        # In multi-page mode (default), keep page-X.html files and remove combined remediated.html
        logger.debug(
            "Multi-page mode: keeping individual page files and removing combined remediated.html"
        )
        combined_file = os.path.join(html_dir, "remediated.html")
        if os.path.exists(combined_file):
            try:
                os.remove(combined_file)
                logger.debug("Removed combined remediated.html file in multi-page mode")
            except Exception as e:
                logger.warning(f"Failed to remove combined remediated file: {e}")


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
            - single_html (bool): Whether to create a single HTML file. Default: False.
            - page_range (tuple): Range of pages to convert (start, end). Default: All pages.
            - single_file (bool): Create a single HTML file instead of multiple files. Default: False.
            - continuous (bool): For single-file mode, use continuous scrolling. Default: True.
            - inline_css (bool): Use inline styling instead of external stylesheet. Default: False.
            - embed_images (bool): Embed images as data URIs in HTML. Default: Based on single_file.
            - exclude_images (bool): Do not include images in the output. Default: False.
            - bda_project_name (str): Name for new BDA project if created. Default: Auto-generated.
            - bda_profile_name (str): Name for new BDA profile if created. Default: Auto-generated.
            - audit_accessibility (bool): Whether to perform an accessibility audit. Default: False.
            - audit_options (dict): Options for accessibility auditing. Default: {}.
            - cleanup_bda_output (bool): Whether to remove BDA output files after processing. Default: False.
        bda_project_arn: ARN of an existing BDA project to use.
        create_bda_project: Whether to create a new BDA project.
        s3_bucket: Name of an existing S3 bucket to use for file uploads.
        profile: AWS profile to use for authentication.

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
    # Set default options
    default_options = {
        "extract_images": True,
        "image_format": "png",
        "embed_fonts": False,
        "single_html": False,
        "page_range": None,
        "single_file": False,
        "multiple_documents": False,  # Default to single document mode
        "continuous": True,
        "inline_css": False,
        "embed_images": False,
        "exclude_images": False,
        "bda_project_name": None,
        "bda_profile_name": None,
        "audit_accessibility": False,
        "audit_options": {},
        "cleanup_bda_output": False,
        "create_bda_project": create_bda_project,  # Pass this flag through to the BDA client
        "profile": profile,  # Store the AWS profile in options
    }

    # Update default options with user-provided options
    if options:
        default_options.update(options)
    options = default_options

    try:
        logger.debug(f"Using Creds profile {profile}")
        # Verify PDF file exists
        if not os.path.isfile(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        # Open the PDF and check if it's image-only
        is_image_only = is_image_only_pdf(pdf_path)
        if is_image_only:
            logger.warning(
                "PDF appears to be image-only. BDA will handle appropriately."
            )

        # Determine whether to use a temporary directory
        use_temp_dir = output_dir is None

        # Create a temporary directory if needed
        temp_dir = None
        if use_temp_dir:
            # Use our temp_directory function with use_cwd=True to create in current working directory
            with temp_directory(
                prefix="pdf2html_", use_cwd=True, cleanup=False
            ) as dir_path:
                temp_dir = dir_path
                output_dir = temp_dir
        else:
            ensure_directory(output_dir)

        try:
            # Resolve which BDA project to use
            project_arn = resolve_bda_project(
                cli_arg=bda_project_arn,
                create_new=options.get("create_bda_project", create_bda_project),
                project_name=options.get("bda_project_name"),
                profile=profile,
            )

            # Get the standard BDA profile if needed
            profile_arn = os.getenv("BDA_PROFILE_ARN")
            if not profile_arn:
                logger.debug(
                    f"Getting standard BDA profile using AWS profile: {profile}"
                )
                # Initialize a client with the project we just created/resolved
                bda_client = ExtendedBDAClient(
                    project_arn, profile=profile
                )  # Make sure profile is used here
                profile_arn = bda_client.get_profile()

            # Initialize the ExtendedBDAClient with profile
            bda_client = ExtendedBDAClient(project_arn, profile=profile)

            # Set the S3 bucket for this operation
            if options.get("create_bda_project", create_bda_project):
                # Always create a new bucket if creating a new project
                bda_client.set_s3_bucket(create_new=True)
            else:
                bda_client.set_s3_bucket(s3_bucket, create_new=False)

            logger.debug(f"Processing PDF with Bedrock Data Automation: {pdf_path}")

            # Set environment variables for the BDA client to control output format
            # These will be read by the _extract_html_from_result_json method
            # Process mode flags: explicit multi_page takes precedence, then single_page, then defaults
            is_multi_page = options.get("multiple_documents", False) or options.get(
                "multi_page", False
            )
            is_single_page = options.get("single_file", False) or options.get(
                "single_page", False
            )

            # Multi-page takes precedence over single-page
            if is_multi_page:
                logger.debug("Setting multi-page mode (multiple individual HTML files)")
                os.environ["PDF2HTML_SINGLE_FILE"] = "false"
                os.environ["PDF2HTML_MULTIPLE_DOCUMENTS"] = "true"
                # Update options for consistency
                options["single_file"] = False
                options["multiple_documents"] = True
            elif is_single_page:
                logger.debug("Setting single-page mode (one combined HTML file)")
                os.environ["PDF2HTML_SINGLE_FILE"] = "true"
                os.environ["PDF2HTML_MULTIPLE_DOCUMENTS"] = "false"
                # Update options for consistency
                options["single_file"] = True
                options["multiple_documents"] = False
            else:
                # Default to multi-page if neither is specified
                logger.debug(
                    "Defaulting to multi-page mode (multiple individual HTML files)"
                )
                os.environ["PDF2HTML_SINGLE_FILE"] = "false"
                os.environ["PDF2HTML_MULTIPLE_DOCUMENTS"] = "true"
                # Update options for consistency
                options["single_file"] = False
                options["multiple_documents"] = True

            # Process PDF through BDA
            result = bda_client.process_and_retrieve(pdf_path, output_dir, options)

            # Clean up files based on mode
            cleanup_output_files(
                output_dir=output_dir,
                single_file=options.get("single_file", False),
                multiple_documents=options.get("multiple_documents", False),
            )

            # Update the html_files list to reflect the cleanup
            html_dir = os.path.join(output_dir, "extracted_html")

            if options.get("single_file", False):
                # In single file mode, only keep remediated.html
                logger.debug(
                    "Setting result for single-file mode: Using remediated.html as main path"
                )
                result["html_files"] = [
                    f
                    for f in result.get("html_files", [])
                    if not (f.endswith(".html") and "page-" in os.path.basename(f))
                ]
                # Update html_path to point to remediated.html
                result["html_path"] = os.path.join(html_dir, "remediated.html")
                result["mode"] = "single-page"
            else:
                # In multi-page mode (default or explicitly set)
                logger.debug(
                    "Setting result for multi-page mode: Using individual page files"
                )
                # Filter out the remediated.html from html_files
                page_files = [
                    f
                    for f in result.get("html_files", [])
                    if not f.endswith("remediated.html")
                ]
                result["html_files"] = page_files

                # Update html_path to point to the directory
                result["html_path"] = html_dir
                result["mode"] = "multi-page"

                # Log the found page files
                logger.debug(f"Found {len(page_files)} page files in {html_dir}")
                for page_file in page_files:
                    logger.debug(f"  - {os.path.basename(page_file)}")

            # Add image-only status to the result
            result["is_image_only"] = is_image_only

            # If a temporary directory was created, add it to the result
            if use_temp_dir:
                result["temp_dir"] = temp_dir

            # Ensure result_data is included in the result
            if "result_data" not in result:
                logger.warning("BDA result_data not found in processing result")
                raise ValueError(
                    "BDA result data is required but was not generated. "
                    "This could indicate an issue with the BDA processing step."
                )
            logger.debug("BDA result_data successfully included in conversion result")

            # Copy images to extracted_html directory for proper relative path resolution
            copy_info = copy_images_to_extracted_html_dir(
                output_dir, result.get("image_files")
            )
            result["copied_images"] = copy_info.get("copied_files", 0)

            return result

        except Exception:
            # Clean up temporary directory if created and conversion failed
            if use_temp_dir and temp_dir and os.path.exists(temp_dir):
                import shutil

                try:
                    shutil.rmtree(temp_dir)
                except Exception as cleanup_error:
                    logger.warning(
                        f"Failed to clean up temporary directory: {cleanup_error}"
                    )

            # Re-raise the exception
            raise

    except FileNotFoundError:
        # Re-raise FileNotFoundError directly
        raise
    except Exception as e:
        # Handle and transform other exceptions
        handle_exception(
            e,
            logger,
            custom_message=f"Error converting PDF to HTML: {pdf_path}",
            custom_exception=DocumentAccessibilityError,
        )


def copy_images_to_extracted_html_dir(
    output_dir: str, image_files: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Copy image files to the extracted_html directory for proper relative path resolution.

    Args:
        output_dir: Base output directory
        image_files: List of image file paths

    Returns:
        Dictionary with information about the copy operation
    """
    logger.debug(
        "Copying images to extracted_html directory for proper relative path resolution..."
    )

    if not image_files:
        logger.debug("No image files to copy")
        return {"copied_files": 0}

    # Find the BDA output directory with the images
    bda_output_dir = None
    for root, dirs, files in os.walk(output_dir):
        if "standard_output" in root and "assets" in root:
            if any(f.endswith(".png") or f.endswith(".jpg") for f in files):
                bda_output_dir = root
                break

    if not bda_output_dir:
        logger.warning("Could not find BDA output directory with images")
        return {"copied_files": 0}

    # Create the extracted_html directory if it doesn't exist
    html_dir = os.path.join(output_dir, "extracted_html")
    if not os.path.exists(html_dir):
        os.makedirs(html_dir, exist_ok=True)

    # Copy each image file to the extracted_html directory
    copied_files = 0
    for image_file in image_files:
        if os.path.exists(image_file):
            import shutil

            try:
                dest_file = os.path.join(html_dir, os.path.basename(image_file))
                shutil.copy2(image_file, dest_file)
                copied_files += 1
                logger.debug(f"Copied image file: {image_file} -> {dest_file}")
            except Exception as e:
                logger.warning(f"Failed to copy image file {image_file}: {e}")

    # Also copy any PNG files from the assets directory
    if bda_output_dir:
        for file in os.listdir(bda_output_dir):
            if file.endswith(".png") or file.endswith(".jpg"):
                src_file = os.path.join(bda_output_dir, file)
                dest_file = os.path.join(html_dir, file)
                try:
                    shutil.copy2(src_file, dest_file)
                    copied_files += 1
                    logger.debug(
                        f"Copied additional image file: {src_file} -> {dest_file}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to copy additional image file {src_file}: {e}"
                    )

    logger.debug(f"Copied {copied_files} image files to extracted_html directory")
    return {"copied_files": copied_files}


def cleanup_bda_output(output_dir: str) -> bool:
    """
    Clean up BDA output files after processing.

    Args:
        output_dir: Directory containing BDA output files

    Returns:
        bool: Whether cleanup was successful
    """
    try:
        # Find BDA output directories
        bda_dirs = []
        for item in os.listdir(output_dir):
            item_path = os.path.join(output_dir, item)
            if (
                os.path.isdir(item_path)
                and not item.startswith(".")
                and not item == "extracted_html"
            ):
                bda_dirs.append(item_path)

        # Remove each BDA output directory
        for bda_dir in bda_dirs:
            import shutil

            try:
                shutil.rmtree(bda_dir)
                logger.debug(f"Removed BDA output directory: {bda_dir}")
            except Exception as e:
                logger.warning(f"Failed to remove BDA output directory {bda_dir}: {e}")
                return False

        return True
    except Exception as e:
        logger.warning(f"Error during BDA output cleanup: {e}")
        return False
