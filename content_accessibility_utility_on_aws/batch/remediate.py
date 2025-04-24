# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Batch processing module for HTML accessibility remediation.

This module provides functionality for remediating accessibility issues in HTML
documents in a batch processing environment using AWS services.
"""

import os
import json
import logging
import tempfile
from typing import Dict, Any, Optional

import boto3

from content_accessibility_utility_on_aws.api import remediate_html_accessibility
from content_accessibility_utility_on_aws.batch.common import (
    download_from_s3,
    upload_to_s3,
    update_job_status,
    STATUS_PROCESSING,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STAGE_REMEDIATION,
    STAGE_COMPLETE,
)

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))


def process_html_with_audit(
    job_id: str,
    html_bucket: str,
    html_key: str,
    audit_bucket: str,
    audit_key: str,
    destination_bucket: str,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Process an HTML document with its audit report from S3, remediate accessibility issues,
    and upload the remediated HTML back to S3.

    Args:
        job_id: Unique identifier for the job
        html_bucket: S3 bucket containing the HTML document
        html_key: S3 key of the HTML document
        audit_bucket: S3 bucket containing the audit report
        audit_key: S3 key of the audit report
        destination_bucket: S3 bucket to upload the remediated HTML to
        options: Optional remediation options

    Returns:
        Dictionary with the results of the remediation
    """
    if options is None:
        options = {}

    # Update job status to PROCESSING
    update_job_status(
        job_id=job_id,
        status=STATUS_PROCESSING,
        stage=STAGE_REMEDIATION,
        details={
            "html_bucket": html_bucket,
            "html_key": html_key,
            "audit_bucket": audit_bucket,
            "audit_key": audit_key,
            "destination_bucket": destination_bucket,
        },
    )

    try:
        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Download HTML from S3
            html_path = os.path.join(temp_dir, os.path.basename(html_key))
            download_from_s3(html_bucket, html_key, html_path)

            # Download audit report from S3
            audit_path = os.path.join(temp_dir, os.path.basename(audit_key))
            download_from_s3(audit_bucket, audit_key, audit_path)

            # Load audit report
            with open(audit_path, "r", encoding="utf-8") as f:
                audit_report = json.load(f)

            # Set up output path for remediated HTML
            base_name = os.path.splitext(os.path.basename(html_key))[0]
            remediated_path = os.path.join(temp_dir, f"{base_name}_remediated.html")

            # Remediate HTML
            logger.info("Remediating HTML: %s", html_path)

            # Set default options if not provided
            remediate_options = {
                "severity_threshold": "minor",
                "auto_fix": True,
                "max_issues": None,
            }
            remediate_options.update(options)

            result = remediate_html_accessibility(
                html_path=html_path,
                audit_report=audit_report,
                output_path=remediated_path,
                options=remediate_options,
            )

            # Upload remediated HTML to S3
            remediated_key = f"remediated/{base_name}_remediated.html"
            upload_to_s3(
                local_path=remediated_path,
                bucket=destination_bucket,
                key=remediated_key,
                metadata={
                    "source-document": html_key,
                    "audit-report": audit_key,
                    "content-type": "text/html",
                },
            )

            # Extract remediation information
            issues_processed = result.get("issues_processed", 0)
            issues_remediated = result.get("issues_remediated", 0)
            issues_failed = result.get("issues_failed", 0)

            # Update job status to COMPLETED
            update_job_status(
                job_id=job_id,
                status=STATUS_COMPLETED,
                stage=STAGE_COMPLETE,  # Final stage
                details={
                    "remediated_key": remediated_key,
                    "issues_processed": issues_processed,
                    "issues_remediated": issues_remediated,
                    "issues_failed": issues_failed,
                },
            )

            return {
                "job_id": job_id,
                "status": STATUS_COMPLETED,
                "stage": STAGE_COMPLETE,
                "html_bucket": html_bucket,
                "html_key": html_key,
                "audit_bucket": audit_bucket,
                "audit_key": audit_key,
                "destination_bucket": destination_bucket,
                "remediated_key": remediated_key,
                "issues_processed": issues_processed,
                "issues_remediated": issues_remediated,
                "issues_failed": issues_failed,
            }

    except Exception as e:
        logger.warning("Error remediating HTML document: %s", e)

        # Update job status to FAILED
        update_job_status(
            job_id=job_id,
            status=STATUS_FAILED,
            stage=STAGE_REMEDIATION,
            details={"error": str(e)},
        )

        raise


def process_html_directory_with_combined_audit(
    job_id: str,
    html_bucket: str,
    html_prefix: str,
    audit_bucket: str,
    audit_key: str,
    destination_bucket: str,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Process a directory of HTML documents with a combined audit report from S3,
    remediate accessibility issues, and upload the remediated HTML back to S3.

    Args:
        job_id: Unique identifier for the job
        html_bucket: S3 bucket containing the HTML documents
        html_prefix: S3 prefix (directory) containing the HTML documents
        audit_bucket: S3 bucket containing the combined audit report
        audit_key: S3 key of the combined audit report
        destination_bucket: S3 bucket to upload the remediated HTML to
        options: Optional remediation options

    Returns:
        Dictionary with the results of the remediation
    """

    s3_client = boto3.client("s3")

    if options is None:
        options = {}

    # Update job status to PROCESSING
    update_job_status(
        job_id=job_id,
        status=STATUS_PROCESSING,
        stage=STAGE_REMEDIATION,
        details={
            "html_bucket": html_bucket,
            "html_prefix": html_prefix,
            "audit_bucket": audit_bucket,
            "audit_key": audit_key,
            "destination_bucket": destination_bucket,
        },
    )

    try:
        # Download combined audit report from S3
        with tempfile.TemporaryDirectory() as temp_dir:
            audit_path = os.path.join(temp_dir, os.path.basename(audit_key))
            download_from_s3(audit_bucket, audit_key, audit_path)

            # Load combined audit report
            with open(audit_path, "r", encoding="utf-8") as f:
                combined_audit = json.load(f)

        # Extract file-specific audit results
        file_results = combined_audit.get("file_results", [])

        # List HTML files in the prefix
        paginator = s3_client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=html_bucket, Prefix=html_prefix)

        html_files = []
        for page in pages:
            for obj in page.get("Contents", []):
                key = obj.get("Key")
                if key.lower().endswith(".html"):
                    html_files.append(key)

        if not html_files:
            logger.warning(
                "No HTML files found in s3://%s/%s", html_bucket, html_prefix
            )

            # Update job status to COMPLETED with warning
            update_job_status(
                job_id=job_id,
                status=STATUS_COMPLETED,
                stage=STAGE_REMEDIATION,
                details={
                    "warning": f"No HTML files found in s3://{html_bucket}/{html_prefix}"
                },
            )

            return {
                "job_id": job_id,
                "status": STATUS_COMPLETED,
                "stage": STAGE_REMEDIATION,
                "warning": f"No HTML files found in s3://{html_bucket}/{html_prefix}",
            }

        # Process each HTML file with its corresponding audit result
        remediation_results = []
        total_issues_processed = 0
        total_issues_remediated = 0
        total_issues_failed = 0

        for html_key in html_files:
            # Find matching audit result
            matching_audit = None
            for result in file_results:
                if result.get("source_key") == html_key:
                    matching_audit = result
                    break

            if not matching_audit or matching_audit.get("status") != STATUS_COMPLETED:
                logger.warning(
                    "No valid audit result found for %s, skipping remediation", html_key
                )
                continue

            try:
                # Get the audit key from the matching audit result
                audit_result_key = matching_audit.get("audit_key")

                if not audit_result_key:
                    logger.warning(
                        "No audit key found in audit result for %s, skipping remediation",
                        html_key,
                    )
                    continue

                # Process the HTML file with its audit report
                result = process_html_with_audit(
                    job_id=f"{job_id}_{len(remediation_results)}",
                    html_bucket=html_bucket,
                    html_key=html_key,
                    audit_bucket=audit_bucket,
                    audit_key=audit_result_key,
                    destination_bucket=destination_bucket,
                    options=options,
                )

                remediation_results.append(result)

                # Aggregate issue counts
                total_issues_processed += result.get("issues_processed", 0)
                total_issues_remediated += result.get("issues_remediated", 0)
                total_issues_failed += result.get("issues_failed", 0)

            except (KeyError, ValueError, IOError) as e:
                logger.warning("Error processing HTML file %s: %s", html_key, e)
                remediation_results.append(
                    {"html_key": html_key, "status": STATUS_FAILED, "error": str(e)}
                )
        # Create a combined remediation report
        combined_report = {
            "job_id": job_id,
            "html_bucket": html_bucket,
            "html_prefix": html_prefix,
            "audit_bucket": audit_bucket,
            "audit_key": audit_key,
            "files_processed": len(remediation_results),
            "files_succeeded": sum(
                1 for r in remediation_results if r.get("status") == STATUS_COMPLETED
            ),
            "files_failed": sum(
                1 for r in remediation_results if r.get("status") == STATUS_FAILED
            ),
            "summary": {
                "total_issues_processed": total_issues_processed,
                "total_issues_remediated": total_issues_remediated,
                "total_issues_failed": total_issues_failed,
            },
            "file_results": remediation_results,
        }

        # Save combined report to a temporary file and upload to S3
        with tempfile.TemporaryDirectory() as temp_dir:
            combined_report_path = os.path.join(
                temp_dir, f"{job_id}_combined_remediation.json"
            )

            with open(combined_report_path, "w", encoding="utf-8") as f:
                json.dump(combined_report, f, indent=2)

            combined_report_key = f"remediated/{job_id}_combined_remediation.json"
            upload_to_s3(
                local_path=combined_report_path,
                bucket=destination_bucket,
                key=combined_report_key,
                metadata={
                    "html-prefix": html_prefix,
                    "audit-key": audit_key,
                    "content-type": "application/json",
                },
            )

        # Update job status to COMPLETED
        update_job_status(
            job_id=job_id,
            status=STATUS_COMPLETED,
            stage=STAGE_COMPLETE,  # Final stage
            details={
                "combined_remediation_key": combined_report_key,
                "files_processed": len(remediation_results),
                "files_succeeded": sum(
                    1
                    for r in remediation_results
                    if r.get("status") == STATUS_COMPLETED
                ),
                "files_failed": sum(
                    1 for r in remediation_results if r.get("status") == STATUS_FAILED
                ),
                "total_issues_processed": total_issues_processed,
                "total_issues_remediated": total_issues_remediated,
                "total_issues_failed": total_issues_failed,
            },
        )

        return {
            "job_id": job_id,
            "status": STATUS_COMPLETED,
            "stage": STAGE_COMPLETE,
            "html_bucket": html_bucket,
            "html_prefix": html_prefix,
            "audit_bucket": audit_bucket,
            "audit_key": audit_key,
            "destination_bucket": destination_bucket,
            "combined_remediation_key": combined_report_key,
            "files_processed": len(remediation_results),
            "files_succeeded": sum(
                1 for r in remediation_results if r.get("status") == STATUS_COMPLETED
            ),
            "files_failed": sum(
                1 for r in remediation_results if r.get("status") == STATUS_FAILED
            ),
            "total_issues_processed": total_issues_processed,
            "total_issues_remediated": total_issues_remediated,
            "total_issues_failed": total_issues_failed,
        }

    except Exception as e:
        logger.warning("Error processing HTML directory with combined audit: %s", e)

        # Update job status to FAILED
        update_job_status(
            job_id=job_id,
            status=STATUS_FAILED,
            stage=STAGE_REMEDIATION,
            details={"error": str(e)},
        )

        raise
