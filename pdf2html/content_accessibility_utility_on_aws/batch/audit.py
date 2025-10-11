# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Batch processing module for HTML accessibility auditing.

This module provides functionality for auditing HTML documents for accessibility
issues in a batch processing environment using AWS services.
"""

import os
import json
import logging
import tempfile
from typing import Dict, Any, Optional

import boto3
from botocore.exceptions import ClientError

from content_accessibility_utility_on_aws.api import audit_html_accessibility
from content_accessibility_utility_on_aws.batch.common import (
    download_from_s3,
    upload_to_s3,
    update_job_status,
    STATUS_PROCESSING,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STAGE_AUDIT,
)

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))


def process_html_document(
    job_id: str,
    source_bucket: str,
    source_key: str,
    destination_bucket: str,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Process an HTML document from S3, audit it for accessibility issues,
      and upload the results back to S3.

    Args:
        job_id: Unique identifier for the job
        source_bucket: S3 bucket containing the HTML document
        source_key: S3 key of the HTML document
        destination_bucket: S3 bucket to upload the audit results to
        options: Optional audit options

    Returns:
        Dictionary with the results of the audit
    """
    if options is None:
        options = {}

    # Update job status to PROCESSING
    update_job_status(
        job_id=job_id,
        status=STATUS_PROCESSING,
        stage=STAGE_AUDIT,
        details={
            "source_bucket": source_bucket,
            "source_key": source_key,
            "destination_bucket": destination_bucket,
        },
    )

    try:
        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Group path-related variables into a single dictionary
            paths = {}
            paths["html"] = os.path.join(temp_dir, os.path.basename(source_key))
            paths["base_name"] = os.path.splitext(os.path.basename(source_key))[0]
            report_format = options.get("report_format", "json")
            paths["report"] = os.path.join(
                temp_dir, f"{paths['base_name']}_audit.{report_format}"
            )

            # Download HTML from S3
            download_from_s3(source_bucket, source_key, paths["html"])

            # Audit HTML for accessibility issues
            logger.info("Auditing HTML for accessibility: %s", paths["html"])

            # Set default options if not provided
            audit_options = {
                "severity_threshold": "minor",
                "detailed": True,
                "report_format": "json",
                "summary_only": False,
            }
            audit_options.update(options)

            result = audit_html_accessibility(
                html_path=paths["html"],
                options=audit_options,
                output_path=paths["report"],
            )

            # Upload audit report to S3
            audit_key = f"audit/{paths['base_name']}_audit.{report_format}"
            upload_to_s3(
                local_path=paths["report"],
                bucket=destination_bucket,
                key=audit_key,
                metadata={
                    "source-document": source_key,
                    "content-type": (
                        "application/json"
                        if report_format == "json"
                        else "text/html" if report_format == "html" else "text/plain"
                    ),
                },
            )

            # Extract summary information from result
            result_summary = result.get("summary", {})
            total_issues = result_summary.get("total_issues", 0)
            severity_counts = result_summary.get("severity_counts", {})

            # Update job status to COMPLETED
            update_job_status(
                job_id=job_id,
                status=STATUS_COMPLETED,
                stage=STAGE_AUDIT,
                details={
                    "audit_key": audit_key,
                    "total_issues": total_issues,
                    "critical_issues": severity_counts.get("critical", 0),
                    "major_issues": severity_counts.get("major", 0),
                    "minor_issues": severity_counts.get("minor", 0),
                },
            )

            return {
                "job_id": job_id,
                "status": STATUS_COMPLETED,
                "stage": STAGE_AUDIT,
                "source_bucket": source_bucket,
                "source_key": source_key,
                "destination_bucket": destination_bucket,
                "audit_key": audit_key,
                "total_issues": total_issues,
                "severity_counts": severity_counts,
            }

    except Exception as e:
        logger.warning("Error auditing HTML document: %s", e)

        # Update job status to FAILED
        update_job_status(
            job_id=job_id,
            status=STATUS_FAILED,
            stage=STAGE_AUDIT,
            details={"error": str(e)},
        )

        raise


def process_html_directory(
    job_id: str,
    source_bucket: str,
    source_prefix: str,
    destination_bucket: str,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Process a directory of HTML documents from S3, audit them for accessibility issues,
    and upload the results back to S3.

    Args:
        job_id: Unique identifier for the job
        source_bucket: S3 bucket containing the HTML documents
        source_prefix: S3 prefix (directory) containing the HTML documents
        destination_bucket: S3 bucket to upload the audit results to
        options: Optional audit options

    Returns:
        Dictionary with the results of the audit
    """

    s3_client = boto3.client("s3")

    if options is None:
        options = {}

    # Update job status to PROCESSING
    update_job_status(
        job_id=job_id,
        status=STATUS_PROCESSING,
        stage=STAGE_AUDIT,
        details={
            "source_bucket": source_bucket,
            "source_prefix": source_prefix,
            "destination_bucket": destination_bucket,
        },
    )

    try:
        # List HTML files in the prefix
        paginator = s3_client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=source_bucket, Prefix=source_prefix)

        html_files = []
        for page in pages:
            for obj in page.get("Contents", []):
                key = obj.get("Key")
                if key.lower().endswith(".html"):
                    html_files.append(key)

        if not html_files:
            logger.warning(
                "No HTML files found in s3://%s/%s", source_bucket, source_prefix
            )

            # Update job status to COMPLETED with warning
            update_job_status(
                job_id=job_id,
                status=STATUS_COMPLETED,
                stage=STAGE_AUDIT,
                details={
                    "warning": f"No HTML files found in s3://{source_bucket}/{source_prefix}"
                },
            )

            return {
                "job_id": job_id,
                "status": STATUS_COMPLETED,
                "stage": STAGE_AUDIT,
                "warning": f"No HTML files found in s3://{source_bucket}/{source_prefix}",
            }

        # Process each HTML file
        audit_results = []
        total_issues = 0
        severity_counts = {"critical": 0, "major": 0, "minor": 0}

        for html_key in html_files:
            try:
                result = process_html_document(
                    job_id=f"{job_id}_{len(audit_results)}",
                    source_bucket=source_bucket,
                    source_key=html_key,
                    destination_bucket=destination_bucket,
                    options=options,
                )

                audit_results.append(result)

                # Aggregate issue counts
                total_issues += result.get("total_issues", 0)
                for severity, count in result.get("severity_counts", {}).items():
                    severity_counts[severity] = severity_counts.get(severity, 0) + count

            except (IOError, ValueError, KeyError, TypeError, ClientError) as e:
                # Catch specific exceptions that might occur during HTML processing
                logger.error("Error processing HTML file %s: %s", html_key, e)
                audit_results.append(
                    {"source_key": html_key, "status": STATUS_FAILED, "error": str(e)}
                )

        # Create a combined audit report
        combined_report = {
            "job_id": job_id,
            "source_bucket": source_bucket,
            "source_prefix": source_prefix,
            "files_processed": len(html_files),
            "files_succeeded": sum(
                1 for r in audit_results if r.get("status") == STATUS_COMPLETED
            ),
            "files_failed": sum(
                1 for r in audit_results if r.get("status") == STATUS_FAILED
            ),
            "summary": {
                "total_issues": total_issues,
                "severity_counts": severity_counts,
            },
            "file_results": audit_results,
        }

        # Save combined report to a temporary file and upload to S3
        with tempfile.TemporaryDirectory() as temp_dir:
            combined_report_path = os.path.join(
                temp_dir, f"{job_id}_combined_audit.json"
            )

            with open(combined_report_path, "w", encoding="utf-8") as f:
                json.dump(combined_report, f, indent=2)

            combined_report_key = f"audit/{job_id}_combined_audit.json"
            upload_to_s3(
                local_path=combined_report_path,
                bucket=destination_bucket,
                key=combined_report_key,
                metadata={
                    "source-prefix": source_prefix,
                    "content-type": "application/json",
                },
            )

        # Update job status to COMPLETED
        update_job_status(
            job_id=job_id,
            status=STATUS_COMPLETED,
            stage=STAGE_AUDIT,
            details={
                "combined_audit_key": combined_report_key,
                "files_processed": len(html_files),
                "files_succeeded": sum(
                    1 for r in audit_results if r.get("status") == STATUS_COMPLETED
                ),
                "files_failed": sum(
                    1 for r in audit_results if r.get("status") == STATUS_FAILED
                ),
                "total_issues": total_issues,
                "critical_issues": severity_counts.get("critical", 0),
                "major_issues": severity_counts.get("major", 0),
                "minor_issues": severity_counts.get("minor", 0),
            },
        )

        return {
            "job_id": job_id,
            "status": STATUS_COMPLETED,
            "stage": STAGE_AUDIT,
            "source_bucket": source_bucket,
            "source_prefix": source_prefix,
            "destination_bucket": destination_bucket,
            "combined_audit_key": combined_report_key,
            "files_processed": len(html_files),
            "files_succeeded": sum(
                1 for r in audit_results if r.get("status") == STATUS_COMPLETED
            ),
            "files_failed": sum(
                1 for r in audit_results if r.get("status") == STATUS_FAILED
            ),
            "total_issues": total_issues,
            "severity_counts": severity_counts,
        }

    except Exception as e:
        logger.warning("Error processing HTML directory: %s", e)

        # Update job status to FAILED
        update_job_status(
            job_id=job_id,
            status=STATUS_FAILED,
            stage=STAGE_AUDIT,
            details={"error": str(e)},
        )

        raise
