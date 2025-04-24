# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Batch processing module for PDF to HTML conversion.

This module provides functionality for converting PDF documents to HTML
in a batch processing environment using AWS services.
"""

import os
import logging
import tempfile
from typing import Dict, Any, Optional

import boto3

from content_accessibility_utility_on_aws.api import convert_pdf_to_html
from content_accessibility_utility_on_aws.batch.common import (
    download_from_s3,
    upload_to_s3,
    update_job_status,
    STATUS_PROCESSING,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STAGE_PDF_TO_HTML,
)

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))


def process_pdf_document(
    job_id: str,
    source_bucket: str,
    source_key: str,
    destination_bucket: str,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Process a PDF document from S3, convert it to HTML, and upload the results back to S3.

    Args:
        job_id: Unique identifier for the job
        source_bucket: S3 bucket containing the PDF document
        source_key: S3 key of the PDF document
        destination_bucket: S3 bucket to upload the HTML results to
        options: Optional conversion options

    Returns:
        Dictionary with the results of the conversion
    """
    if options is None:
        options = {}

    # Update job status to PROCESSING
    update_job_status(
        job_id=job_id,
        status=STATUS_PROCESSING,
        stage=STAGE_PDF_TO_HTML,
        details={
            "source_bucket": source_bucket,
            "source_key": source_key,
            "destination_bucket": destination_bucket,
        },
    )

    try:
        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Download PDF from S3
            pdf_path = os.path.join(temp_dir, os.path.basename(source_key))
            download_from_s3(source_bucket, source_key, pdf_path)

            # Set up output directory
            output_dir = os.path.join(temp_dir, "output")
            os.makedirs(output_dir, exist_ok=True)

            # Convert PDF to HTML
            logger.info("Converting PDF to HTML: %s", pdf_path)
            result = convert_pdf_to_html(
                pdf_path=pdf_path, output_dir=output_dir, options=options
            )

            # Upload HTML and associated files to S3
            s3_results = upload_conversion_results(
                result=result,
                source_key=source_key,
                destination_bucket=destination_bucket,
            )

            # Update job status to COMPLETED
            update_job_status(
                job_id=job_id,
                status=STATUS_COMPLETED,
                stage=STAGE_PDF_TO_HTML,
                details={
                    "html_key": s3_results.get("html_key"),
                    "html_files": s3_results.get("html_files", []),
                    "image_files": s3_results.get("image_files", []),
                    "is_image_only": result.get("is_image_only", False),
                },
            )

            return {
                "job_id": job_id,
                "status": STATUS_COMPLETED,
                "stage": STAGE_PDF_TO_HTML,
                "source_bucket": source_bucket,
                "source_key": source_key,
                "destination_bucket": destination_bucket,
                "html_key": s3_results.get("html_key"),
                "html_files": s3_results.get("html_files", []),
                "image_files": s3_results.get("image_files", []),
                "is_image_only": result.get("is_image_only", False),
            }

    except Exception as e:
        logger.warning("Error processing PDF document: %s", e)

        # Update job status to FAILED
        update_job_status(
            job_id=job_id,
            status=STATUS_FAILED,
            stage=STAGE_PDF_TO_HTML,
            details={"error": str(e)},
        )

        raise


def upload_conversion_results(
    result: Dict[str, Any], source_key: str, destination_bucket: str
) -> Dict[str, Any]:
    """
    Upload the results of a PDF to HTML conversion to S3.

    Args:
        result: Result dictionary from convert_pdf_to_html
        source_key: Original S3 key of the PDF document
        destination_bucket: S3 bucket to upload the results to

    Returns:
        Dictionary with the S3 keys of the uploaded files
    """
    # Extract base name from source key
    base_name = os.path.splitext(os.path.basename(source_key))[0]

    # Generate prefix for the HTML files
    prefix = f"html/{base_name}/"

    # Upload main HTML file
    html_path = result.get("html_path")
    html_key = f"{prefix}{os.path.basename(html_path)}"

    upload_to_s3(
        local_path=html_path,
        bucket=destination_bucket,
        key=html_key,
        metadata={"source-document": source_key, "content-type": "text/html"},
    )

    # Upload additional HTML files
    html_files = []
    for file_path in result.get("html_files", []):
        file_key = f"{prefix}{os.path.basename(file_path)}"
        upload_to_s3(
            local_path=file_path,
            bucket=destination_bucket,
            key=file_key,
            metadata={"source-document": source_key, "content-type": "text/html"},
        )
        html_files.append(file_key)

    # Upload image files
    image_files = []
    for file_path in result.get("image_files", []):
        file_key = f"{prefix}images/{os.path.basename(file_path)}"

        # Determine content type based on file extension
        content_type = "image/png"  # Default
        if file_path.lower().endswith(".jpg") or file_path.lower().endswith(".jpeg"):
            content_type = "image/jpeg"
        elif file_path.lower().endswith(".webp"):
            content_type = "image/webp"

        upload_to_s3(
            local_path=file_path,
            bucket=destination_bucket,
            key=file_key,
            metadata={"source-document": source_key, "content-type": content_type},
        )
        image_files.append(file_key)

    # Upload CSS files if present
    css_files = []
    for file_path in result.get("css_files", []):
        file_key = f"{prefix}css/{os.path.basename(file_path)}"
        upload_to_s3(
            local_path=file_path,
            bucket=destination_bucket,
            key=file_key,
            metadata={"source-document": source_key, "content-type": "text/css"},
        )
        css_files.append(file_key)

    return {
        "html_key": html_key,
        "html_files": html_files,
        "image_files": image_files,
        "css_files": css_files,
    }


def check_bda_job_status(job_id: str, bda_job_id: str) -> Dict[str, Any]:
    """
    Check the status of a Bedrock Document Automation job.

    Args:
        job_id: Unique identifier for our tracking job
        bda_job_id: Bedrock Document Automation job ID

    Returns:
        Dictionary with the job status
    """
    bda_client = boto3.client("bedrock")

    try:
        response = bda_client.get_document_analysis(jobId=bda_job_id)

        status = response.get("jobStatus")

        if status == "SUCCEEDED":
            return {
                "status": "COMPLETED",
                "bda_status": status,
                "job_id": job_id,
                "bda_job_id": bda_job_id,
            }
        elif status in ["FAILED", "EXPIRED"]:
            return {
                "status": "FAILED",
                "bda_status": status,
                "job_id": job_id,
                "bda_job_id": bda_job_id,
                "failure_reason": response.get("statusMessage", "Unknown failure"),
            }
        else:
            # Still in progress
            return {
                "status": "PROCESSING",
                "bda_status": status,
                "job_id": job_id,
                "bda_job_id": bda_job_id,
            }

    except boto3.exceptions.Boto3Error as e:
        logger.warning("Error checking BDA job status: %s", e)
        return {
            "status": "ERROR",
            "error": str(e),
            "job_id": job_id,
            "bda_job_id": bda_job_id,
        }
