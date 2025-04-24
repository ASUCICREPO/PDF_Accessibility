# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Bedrock Data Automation Client module.

This module provides functionality for interacting with Amazon Bedrock Data Automation
to convert PDFs to HTML.
"""

import os
import uuid
import json
import time
import boto3
import tempfile
import shutil
from bs4 import BeautifulSoup
from datetime import datetime

from content_accessibility_utility_on_aws.utils.logging_helper import (
    setup_logger,
)
from content_accessibility_utility_on_aws.utils.usage_tracker import SessionUsageTracker
from content_accessibility_utility_on_aws.pdf2html.services.page_builder import build_html_data

# Set up module-level logger
logger = setup_logger(__name__)


# Update the function signature to accept profile parameter
def resolve_bda_project(
    cli_arg=None, create_new=False, project_name=None, profile=None
):
    """
    Resolve which BDA project to use.

    Args:
        cli_arg: Project ARN provided via CLI
        create_new: Whether to create a new project
        project_name: Name for new BDA project if created
        profile: AWS profile name to use for authentication

    Returns:
        str: Project ARN
    """
    # If create_new is explicitly requested, create a new project regardless of existing ones
    if create_new:
        logger.debug("Creating new BDA project as requested...")

        try:
            # Verify AWS credentials are available
            try:
                session = (
                    boto3.Session(profile_name=profile) if profile else boto3.Session()
                )
                sts_client = session.client("sts")
                identity = sts_client.get_caller_identity()
                logger.debug(
                    f"AWS credentials verified: Account ID {identity['Account']}"
                )
            except Exception as aws_error:
                logger.warning(f"AWS credentials error: {aws_error}")
                raise RuntimeError(
                    f"AWS credentials not configured correctly: {aws_error}"
                )

            # Create a client with the profile
            bda_client = BDAClient(profile=profile)

            # Create a new project using the boto3 client directly
            logger.debug(
                f"Creating new BDA project with name: {project_name or 'auto-generated'}"
            )

            # Generate a project name if not provided
            project_name = project_name or f"pdf2html-project-{uuid.uuid4().hex[:8]}"

            # Create the project using the client
            new_project = bda_client.create_project(project_name)

            logger.debug(f"Successfully created new BDA project: {new_project}")
            return new_project

        except Exception as e:
            # Don't silently fail - this is an explicit request to create a project
            error_msg = f"Failed to create BDA project: {e}"
            logger.warning(error_msg)
            raise RuntimeError(error_msg)

    # Check command line argument
    if cli_arg:
        logger.debug(f"Using BDA project from CLI argument: {cli_arg}")
        return cli_arg

    # Check environment variable
    env_project = os.getenv("BDA_PROJECT_ARN")
    if env_project:
        logger.debug(f"Using BDA project from environment: {env_project}")
        return env_project

    # Check temp file
    tmp_file = os.path.join(tempfile.gettempdir(), "pdf2html_bda_project")
    if os.path.exists(tmp_file):
        with open(tmp_file, "r", encoding="utf-8") as f:
            saved_project = f.read().strip()
            if saved_project:
                logger.debug(f"Using BDA project from saved file: {saved_project}")
                return saved_project

    # Default to None
    return None


class BDAClient:
    """Base client for interacting with Amazon Bedrock Data Automation."""

    def __init__(self, project_arn=None, profile=None):
        """
        Initialize the BDA client.

        Args:
            project_arn: ARN of the BDA project to use
            profile: AWS profile name to use for authentication
        """
        self.project_arn = project_arn
        self.s3_bucket = None
        self.profile = profile
        logger.debug(f"BDA CLIENT INIT - profile={profile}")
        # Create a boto3 session with the provided profile
        self.session = (
            boto3.Session(profile_name=profile) if profile else boto3.Session()
        )

        # Create clients using the session
        self.bda_runtime_client = self.session.client("bedrock-data-automation-runtime")
        self.bda_admin_client = self.session.client("bedrock-data-automation")
        self.s3_client = self.session.client("s3")
        self.sts_client = self.session.client("sts")

        # Verify AWS credentials
        try:
            self.sts_client.get_caller_identity()
            logger.debug(
                f"Successfully initialized AWS clients with profile: {profile}"
            )
        except Exception as e:
            logger.warning(f"Failed to initialize AWS clients: {e}")
            raise

    def create_project(self, name=None):
        """
        Create a new BDA project.

        Args:
            name: Optional name for the project

        Returns:
            str: ARN of the created project
        """
        try:
            # Create the project name if not provided
            project_name = name or f"pdf2html-project-{uuid.uuid4().hex[:8]}"

            # Create standard output configuration
            standard_output_config = {
                "document": {
                    "extraction": {
                        "granularity": {"types": ["DOCUMENT", "PAGE", "ELEMENT"]},
                        "boundingBox": {"state": "ENABLED"},
                    },
                    "generativeField": {"state": "ENABLED"},
                    "outputFormat": {
                        "textFormat": {"types": ["HTML"]},
                        "additionalFileFormat": {"state": "ENABLED"},
                    },
                }
            }

            # Create the project using boto3
            bda_admin_client = self.session.client("bedrock-data-automation")
            response = bda_admin_client.create_data_automation_project(
                projectName=project_name,
                projectDescription="PDF to HTML conversion project",
                standardOutputConfiguration=standard_output_config,
            )

            # Get the project ARN
            project_arn = response.get("projectArn")

            if not project_arn:
                raise RuntimeError("Project creation returned no ARN")

            # Save for future use
            tmp_file = os.path.join(tempfile.gettempdir(), "pdf2html_bda_project")
            with open(tmp_file, "w", encoding="utf-8") as f:
                f.write(project_arn)

            return project_arn

        except Exception as e:
            logger.warning(f"Failed to create BDA project: {e}")
            raise

    def set_s3_bucket(self, bucket_name=None, create_new=False):
        """
        Set the S3 bucket to use for file uploads.

        Args:
            bucket_name: Name of an existing bucket to use
            create_new: Whether to create a new bucket if none exists
        """
        if bucket_name:
            self.s3_bucket = bucket_name
            logger.debug(f"Using S3 bucket: {bucket_name}")
            return

        # Check environment variable
        env_bucket = os.getenv("BDA_S3_BUCKET")
        if env_bucket:
            self.s3_bucket = env_bucket
            logger.debug(f"Using S3 bucket from environment: {env_bucket}")
            return

        # Check temp file
        tmp_file = os.path.join(tempfile.gettempdir(), "pdf2html_s3_bucket")
        if os.path.exists(tmp_file):
            with open(tmp_file, "r", encoding="utf-8") as f:
                saved_bucket = f.read().strip()
                if saved_bucket:
                    self.s3_bucket = saved_bucket
                    logger.debug(f"Using S3 bucket from saved file: {saved_bucket}")
                    return

        # Create new if requested
        if create_new:
            bucket_name = f"pdf2html-input-{uuid.uuid4().hex[:8]}"
            try:
                self.s3_client.create_bucket(Bucket=bucket_name)
                self.s3_bucket = bucket_name
                logger.debug(f"Created new S3 bucket: {bucket_name}")

                # Save for future use
                with open(tmp_file, "w", encoding="utf-8") as f:
                    f.write(bucket_name)

            except Exception as e:
                logger.warning(f"Failed to create S3 bucket: {e}")
                raise

    def get_profile(self):
        """
        Get the standard BDA profile ARN.

        Returns:
            str: ARN of the standard BDA profile
        """
        # Check environment variable
        env_profile = os.getenv("BDA_PROFILE_ARN")
        if env_profile:
            logger.debug(f"Using profile ARN from environment: {env_profile}")
            return env_profile

        # Construct the standard profile ARN using region and account ID
        try:
            region = self.session.region_name
            identity = self.sts_client.get_caller_identity()
            account_id = identity["Account"]

            profile_arn = f"arn:aws:bedrock:{region}:{account_id}:data-automation-profile/us.data-automation-v1"
            logger.debug(f"Using constructed standard profile ARN: {profile_arn}")

            return profile_arn

        except Exception as e:
            logger.warning(f"Failed to construct BDA profile ARN: {e}")
            raise


class ExtendedBDAClient(BDAClient):
    """Extended client with additional functionality for PDF processing."""


    def process_and_retrieve(
        self, pdf_path: str, output_dir: str, options: dict
    ) -> dict:
        """
        Process a PDF through BDA and retrieve the results.

        Args:
            pdf_path: Path to the PDF file
            output_dir: Directory to save output files
            options: Processing options

        Returns:
            dict: Processing results
        """
        start_time = datetime.now()
        
        try:
            # Verify we have a bucket
            if not self.s3_bucket:
                raise ValueError("S3 bucket not configured")

            # Upload PDF to S3
            s3_key = f"uploads/{uuid.uuid4().hex}/{os.path.basename(pdf_path)}"
            s3_path = f"s3://{self.s3_bucket}/{s3_key}"

            logger.debug(f"Uploading {pdf_path} to {s3_path}")
            self.s3_client.upload_file(pdf_path, self.s3_bucket, s3_key)

            # Submit for processing
            logger.debug(f"Submitting PDF for processing: {pdf_path}")

            # Get the profile ARN
            profile_arn = self.get_profile()
            logger.debug(f"Using profile ARN: {profile_arn}")
            logger.debug(f"Using project ARN: {self.project_arn}")
            # Submit the job with project ARN
            response = self.bda_runtime_client.invoke_data_automation_async(
                inputConfiguration={"s3Uri": s3_path},
                outputConfiguration={
                    "s3Uri": f"s3://{self.s3_bucket}/output/{uuid.uuid4().hex}/"
                },
                dataAutomationConfiguration={
                    "dataAutomationProjectArn": self.project_arn,
                    "stage": "LIVE",
                },
                dataAutomationProfileArn=profile_arn,
            )

            # Get the invocation ARN and output path
            invocation_arn = response["invocationArn"]

            # Handle the case when 'output' key is missing or has a different structure
            if "output" in response and "outputPath" in response["output"]:
                output_path = response["output"]["outputPath"]
                logger.debug(f"Results will be available at: {output_path}")
            else:
                # Log the actual response structure for debugging
                logger.debug(f"Response structure: {response}")
                # Use a default output path based on the invocation ARN
                output_path = f"s3://{self.s3_bucket}/output/{uuid.uuid4().hex}/"
                logger.debug(
                    f"Output key 'output' not found in response, using default path: {output_path}"
                )

            # Monitor the job
            logger.debug(f"Monitoring job {invocation_arn}")
            while True:
                try:
                    # Try the new method name first (get_data_automation_status)
                    response = self.bda_runtime_client.get_data_automation_status(
                        invocationArn=invocation_arn
                    )
                except AttributeError:
                    try:
                        # Fall back to the old method name if needed
                        response = (
                            self.bda_runtime_client.get_data_automation_invocation(
                                invocationArn=invocation_arn
                            )
                        )
                    except Exception as e:
                        logger.warning(f"Failed to get job status: {e}")
                        raise

                status = response["status"]
                logger.debug(f"Job {invocation_arn} status: {status}")

                if status in ["Success", "Failed", "Cancelled"]:
                    break

                # nosemgrep: arbitrary-sleep
                time.sleep(10)

            # Get the output path from the job status
            if status == "Success":
                # Get the output path from the job status response
                if (
                    "outputConfiguration" in response
                    and "s3Uri" in response["outputConfiguration"]
                ):
                    output_path = response["outputConfiguration"]["s3Uri"]
                    # Extract the base directory from the path (remove the job_metadata.json part)
                    if output_path.endswith("job_metadata.json"):
                        output_path = "/".join(output_path.split("/")[:-1]) + "/"
                    logger.debug(f"Results will be available at: {output_path}")
                else:
                    logger.warning(
                        f"Output path not found in job status response: {response}"
                    )
                    # Use the default output path we created earlier
                    logger.debug(f"Using default output path: {output_path}")

            logger.debug(f"Job {invocation_arn} finished with status: {status}")

            if status != "Success":
                raise RuntimeError(f"Job failed with status: {status}")

            # Download results
            logger.debug(f"Downloading results from {output_path}")
            logger.debug(f"Saving to {output_dir}")

            # Parse the S3 path
            bucket = output_path.split("/")[2]
            prefix = "/".join(output_path.split("/")[3:])

            # List objects in the output directory
            paginator = self.s3_client.get_paginator("list_objects_v2")
            downloaded_files = []

            # Parse the S3 path
            bucket = output_path.split("/")[2]
            prefix = "/".join(output_path.split("/")[3:])

            # Check if we need to look for the result.json in a subdirectory
            result_json_found = False

            for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                for obj in page.get("Contents", []):
                    # Get the key
                    key = obj["Key"]

                    # Check if this is a result.json file
                    if key.endswith("result.json"):
                        result_json_found = True
                        logger.debug(f"Found result.json at: {key}")

                        # Get the relative path
                        rel_path = os.path.relpath(key, prefix)

                        # Create the local directory structure
                        local_path = os.path.join(output_dir, rel_path)
                        os.makedirs(os.path.dirname(local_path), exist_ok=True)

                        # Download the file
                        logger.debug(f"Downloading {key} to {local_path}")
                        self.s3_client.download_file(bucket, key, local_path)
                        downloaded_files.append(local_path)

                        # If we found a result.json, we need to check for other files in the same directory
                        result_dir = os.path.dirname(key)

                        # List all objects in the result directory
                        for result_page in paginator.paginate(
                            Bucket=bucket, Prefix=result_dir
                        ):
                            for result_obj in result_page.get("Contents", []):
                                result_key = result_obj["Key"]
                                if (
                                    result_key != key
                                ):  # Skip the result.json file we already downloaded
                                    # Get the relative path
                                    result_rel_path = os.path.relpath(
                                        result_key, prefix
                                    )

                                    # Create the local directory structure
                                    result_local_path = os.path.join(
                                        output_dir, result_rel_path
                                    )
                                    os.makedirs(
                                        os.path.dirname(result_local_path),
                                        exist_ok=True,
                                    )

                                    # Download the file
                                    logger.debug(
                                        f"Downloading {result_key} to {result_local_path}"
                                    )
                                    self.s3_client.download_file(
                                        bucket, result_key, result_local_path
                                    )
                                    downloaded_files.append(result_local_path)

            if not result_json_found:
                raise FileNotFoundError("result.json not found in BDA output")

            # Find the result.json file
            result_json = None
            for file in downloaded_files:
                if file.endswith("result.json"):
                    result_json = file
                    break

            if not result_json:
                raise FileNotFoundError("result.json not found in BDA output")

            logger.debug(f"Found BDA result.json file: {result_json}")

            # Debug: List all files in the output directory
            logger.debug("Listing all files in output directory:")
            for root, dirs, files in os.walk(output_dir):
                for file in files:
                    logger.debug(f"  {os.path.join(root, file)}")

            # Extract HTML content
            extract_result = self._extract_html_from_result_json(
                result_json, output_dir
            )

            # Calculate processing time
            end_time = datetime.now()
            processing_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Count pages from the result data
            page_count = 0
            
            # Read the result data to count pages
            try:
                with open(result_json, "r", encoding="utf-8") as f:
                    result_data = json.load(f)
                    if "pages" in result_data:
                        page_count = len(result_data["pages"])
            except Exception as e:
                logger.warning(f"Error reading result data for page count: {e}")
            
            # Fallback to counting HTML files if we couldn't get page count from result data
            if page_count == 0 and extract_result["html_files"]:
                # If we don't have explicit page data, count HTML files as a fallback
                # But only count files that appear to be pages (match page-X.html pattern)
                import re
                page_files = [f for f in extract_result["html_files"] if re.search(r'page-\d+\.html$', f)]
                page_count = max(1, len(page_files))  # At least 1 page
            
            # Generate a unique document ID
            document_id = f"doc-{uuid.uuid4().hex[:8]}"
            
            # Track BDA usage
            try:
                usage_tracker = SessionUsageTracker.get_instance()
                usage_tracker.track_bda_processing(
                    project_arn=self.project_arn,
                    document_id=document_id,
                    page_count=page_count,
                    processing_time_ms=processing_time_ms
                )
                logger.debug(f"Tracked BDA processing: document={document_id}, pages={page_count}, time={processing_time_ms}ms")
            except Exception as track_error:
                logger.warning(f"Failed to track BDA usage: {track_error}")
            
            # Return the results
            return {
                "html_files": extract_result["html_files"],
                "html_path": (
                    extract_result["html_files"][0]
                    if extract_result["html_files"]
                    else None
                ),
                "image_files": downloaded_files,
                "result_data": extract_result.get("element_data", {}),
                "document_id": document_id,
                "page_count": page_count
            }

        except Exception as e:
            logger.warning(f"Error processing PDF: {e}")
            raise

    def _extract_html_from_result_json(self, json_file_path, output_dir):
        """
        Extract HTML content from BDA result.json file.

        Args:
            json_file_path: Path to the result.json file
            output_dir: Directory to save extracted HTML files

        Returns:
            dict: Dictionary containing paths to extracted HTML files and element data
        """
        logger.debug(f"Extracting HTML content from BDA result.json: {json_file_path}")

        try:
            # Read the JSON file
            with open(json_file_path, "r", encoding="utf-8") as f:
                result_data = json.load(f)

            # Determine if we should use single-page or multi-page mode ONLY from the CLI/API parameters
            # NOT based on what exists in the results
            single_file = (
                os.environ.get("PDF2HTML_SINGLE_FILE", "false").lower() == "true"
            )
            multiple_documents = (
                os.environ.get("PDF2HTML_MULTIPLE_DOCUMENTS", "false").lower() == "true"
            )

            # Use single-page processing if single_file is true and multiple_documents is false
            is_single_page = single_file and not multiple_documents
            logger.debug(
                f"Mode selection based on parameters: single_file={single_file}, multiple_documents={multiple_documents}, using single-page={is_single_page}"
            )

            # Ensure the required data is available - if not, log a warning but still try to process
            if is_single_page and (
                "document" not in result_data
                or "representation" not in result_data["document"]
                or "html" not in result_data["document"]["representation"]
            ):
                logger.warning(
                    "Single-page mode requested but document.representation.html not found in result data"
                )
                # Note: We still continue with is_single_page=True as requested by parameters

            if "pages" not in result_data:
                logger.warning(f"No pages data found in result JSON: {json_file_path}")
                if (
                    not is_single_page
                    or "document" not in result_data
                    or "representation" not in result_data["document"]
                    or "html" not in result_data["document"]["representation"]
                ):
                    # Only return empty if we don't have any usable data
                    logger.warning("No usable HTML data found in the result")
                    return {"html_files": [], "element_data": {}}

            # Create a subdirectory for extracted HTML files - with full normalized path
            # Use realpath to resolve any symlinks in the path
            norm_output_dir = os.path.realpath(output_dir)
            html_output_dir = os.path.normpath(
                os.path.join(norm_output_dir, "extracted_html")
            )
            logger.debug(f"Creating HTML output directory: {html_output_dir}")

            # Create directory explicitly with os.makedirs
            try:
                os.makedirs(html_output_dir, exist_ok=True)
                logger.debug(f"Directory created: {html_output_dir}")
            except Exception as e:
                logger.warning(f"Failed to create directory: {e}")
                raise IOError(f"Failed to create output directory: {html_output_dir}")

            if not os.path.isdir(html_output_dir):
                logger.warning(f"Path exists but is not a directory: {html_output_dir}")
                raise IOError(f"Failed to create valid directory: {html_output_dir}")

            logger.debug(
                f"Output mode configuration: single_file={single_file}, multiple_documents={multiple_documents}, using single-page={is_single_page}"
            )

            # First, copy all image files to the extracted_html directory
            # This ensures they're available for the page builder
            self._copy_all_images_to_html_dir(output_dir, html_output_dir)

            # Use the new page builder to generate HTML from elements
            build_result = build_html_data(result_data, output_dir, is_single_page)
            extracted_html_files = build_result["html_files"]

            # Extract element data for images
            element_data = {}
            if "elements" in result_data:
                # Process each element
                for element in result_data["elements"]:
                    # Only process image elements
                    if element.get("type") == "FIGURE" and element.get("sub_type") in [
                        "IMAGE",
                        "ICON",
                        "DIAGRAM",
                    ]:
                        element_id = element.get("id")
                        page_indices = element.get("page_indices", [])
                        crop_images = element.get("crop_images", [])
                        representation = element.get("representation", {}).get(
                            "html", ""
                        )

                        if element_id and crop_images:
                            # Extract filename from S3 path
                            image_filename = os.path.basename(crop_images[0])
                            element_data[element_id] = {
                                "page_indices": page_indices,
                                "filename": image_filename,
                                "s3_path": crop_images[0],
                                "html": representation,
                            }

                            # Extract the image src from the HTML representation
                            if representation:
                                soup = BeautifulSoup(representation, "html.parser")
                                img_tags = soup.find_all("img")
                                for img_tag in img_tags:
                                    src = img_tag.get("src", "")
                                    if src:
                                        src_filename = os.path.basename(
                                            src.replace("./", "").strip()
                                        )
                                        element_data[element_id]["src"] = src_filename

                                        # Copy the image if needed
                                        crop_file = os.path.join(
                                            output_dir, image_filename
                                        )
                                        dest_file = os.path.join(
                                            html_output_dir, src_filename
                                        )
                                        if os.path.exists(
                                            crop_file
                                        ) and not os.path.exists(dest_file):
                                            try:
                                                shutil.copy2(crop_file, dest_file)
                                                logger.debug(
                                                    f"Copied image for element {element_id}: {crop_file} -> {dest_file}"
                                                )
                                            except Exception as e:
                                                logger.warning(
                                                    f"Failed to copy image for element {element_id}: {e}"
                                                )

                logger.debug(f"Extracted data for {len(element_data)} image elements")

            # Final check to ensure all images referenced in HTML are available
            from content_accessibility_utility_on_aws.pdf2html.services.image_mapper import (
                ensure_all_images_available,
            )

            ensure_all_images_available(output_dir)

            # If we're in single file mode, remove the individual page files
            if single_file and not multiple_documents and len(extracted_html_files) > 1:
                # The first file is the combined file, so we need to keep that one
                for page_file in extracted_html_files[1:]:
                    try:
                        os.remove(page_file)
                        logger.debug(
                            f"Removed individual page file in single file mode: {page_file}"
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to remove individual page file {page_file}: {e}"
                        )

                # Update the list to only include the combined file
                extracted_html_files = [extracted_html_files[0]]

            return {"html_files": extracted_html_files, "element_data": element_data}
        except Exception as e:
            logger.warning(f"Error extracting HTML from result JSON: {e}")
            return {"html_files": [], "element_data": {}}

    def _copy_all_images_to_html_dir(self, output_dir, html_output_dir):
        """
        Copy all image files to the extracted_html directory.

        Args:
            output_dir: Base output directory
            html_output_dir: HTML output directory
        """
        logger.debug("Copying all image files to HTML directory...")

        # Find all image files in the output directory
        image_files = []
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                if file.endswith(".png") or file.endswith(".jpg"):
                    image_files.append(os.path.join(root, file))

        logger.debug(f"Found {len(image_files)} image files")

        # Copy each image file to the HTML directory
        copied_files = 0
        for image_file in image_files:
            dest_file = os.path.join(html_output_dir, os.path.basename(image_file))
            # Skip copy if source and destination are the same file
            if os.path.abspath(image_file) == os.path.abspath(dest_file):
                logger.debug(f"Skipping copy of identical paths: {image_file}")
                continue
            try:
                shutil.copy2(image_file, dest_file)
                copied_files += 1
                logger.debug(f"Copied image file: {image_file} -> {dest_file}")
            except Exception as e:
                logger.warning(f"Failed to copy image file {image_file}: {e}")

        logger.debug(f"Copied {copied_files} image files to HTML directory")
