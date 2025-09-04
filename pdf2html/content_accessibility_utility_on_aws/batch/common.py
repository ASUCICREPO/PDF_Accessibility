# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Common utilities for batch processing.

This module provides common utilities for batch processing, including:
- DynamoDB table operations
- S3 operations
- SQS operations
- Logging
"""

import os
import json

from typing import Dict, Any, Optional, List
from datetime import datetime
import hashlib
import time

import boto3

from ..utils.logging_helper import setup_logger

# Configure logging
logger = setup_logger(__name__)
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# Initialize AWS clients
s3_client = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
sqs = boto3.client("sqs")

# Constants
DEFAULT_REGION = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or os.environ.get("CDK_DEFAULT_REGION")
JOB_STATUS_TABLE = os.environ.get("JOB_STATUS_TABLE", "DocumentAccessibilityJobs")

# Job status constants
STATUS_PENDING = "PENDING"
STATUS_PROCESSING = "PROCESSING"
STATUS_COMPLETED = "COMPLETED"
STATUS_FAILED = "FAILED"

# Processing stage constants
STAGE_PDF_TO_HTML = "PDF_TO_HTML"
STAGE_AUDIT = "AUDIT"
STAGE_REMEDIATION = "REMEDIATION"
STAGE_COMPLETE = "COMPLETE"


def get_job_table():
    """Get the DynamoDB job status table."""
    return dynamodb.Table(JOB_STATUS_TABLE)


def create_job_record(
    job_id: str, document_key: str, stage: str = STAGE_PDF_TO_HTML
) -> Dict[str, Any]:
    """
    Create a new job record in DynamoDB.

    Args:
        job_id: Unique identifier for the job
        document_key: S3 key of the original document
        stage: Initial processing stage

    Returns:
        The created job record
    """
    table = get_job_table()

    timestamp = datetime.utcnow().isoformat()
    item = {
        "job_id": job_id,
        "document_key": document_key,
        "created_at": timestamp,
        "updated_at": timestamp,
        "status": STATUS_PENDING,
        "stage": stage,
        "history": [{"timestamp": timestamp, "stage": stage, "status": STATUS_PENDING}],
    }

    table.put_item(Item=item)
    logger.debug("Created job record for job_id: %s, document: %s", job_id, document_key)

    return item


def update_job_status(
    job_id: str, status: str, stage: str, details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Update the status of a job in DynamoDB.

    Args:
        job_id: Unique identifier for the job
        status: New status (PENDING, PROCESSING, COMPLETED, FAILED)
        stage: Current processing stage
        details: Optional details about the status update

    Returns:
        The updated job record
    """
    table = get_job_table()
    timestamp = datetime.utcnow().isoformat()

    # Get the current record
    response = table.get_item(Key={"job_id": job_id})
    if "Item" not in response:
        logger.error("Job %s not found in DynamoDB", job_id)
        raise ValueError(f"Job {job_id} not found")

    current_record = response["Item"]
    history = current_record.get("history", [])

    # Add new history entry
    history_entry = {"timestamp": timestamp, "stage": stage, "status": status}

    if details:
        history_entry["details"] = details

    history.append(history_entry)

    # Update the record
    update_expression = """
    SET #status = :status, 
        #stage = :stage, 
        #updated_at = :updated_at, 
        #history = :history
    """

    expression_attribute_names = {
        "#status": "status",
        "#stage": "stage",
        "#updated_at": "updated_at",
        "#history": "history",
    }

    expression_attribute_values = {
        ":status": status,
        ":stage": stage,
        ":updated_at": timestamp,
        ":history": history,
    }

    # Add any additional fields from details
    if details:
        for key, value in details.items():
            safe_key = key.replace("-", "_")
            update_expression += f", #{safe_key} = :{safe_key}"
            expression_attribute_names[f"#{safe_key}"] = key
            expression_attribute_values[f":{safe_key}"] = value

    response = table.update_item(
        Key={"job_id": job_id},
        UpdateExpression=update_expression,
        ExpressionAttributeNames=expression_attribute_names,
        ExpressionAttributeValues=expression_attribute_values,
        ReturnValues="ALL_NEW",
    )

    updated_record = response.get("Attributes", {})
    logger.debug("Updated job %s status to %s in stage %s", job_id, status, stage)

    return updated_record


def get_job_status(job_id: str) -> Dict[str, Any]:
    """
    Get the current status of a job from DynamoDB.

    Args:
        job_id: Unique identifier for the job

    Returns:
        The job record
    """
    table = get_job_table()
    response = table.get_item(Key={"job_id": job_id})

    if "Item" not in response:
        logger.error("Job %s not found in DynamoDB", job_id)
        raise ValueError(f"Job {job_id} not found")

    return response["Item"]


def download_from_s3(bucket: str, key: str, local_path: str) -> str:
    """
    Download a file from S3 to a local path.

    Args:
        bucket: S3 bucket name
        key: S3 object key
        local_path: Local path to save the file

    Returns:
        The local path where the file was saved
    """
    os.makedirs(os.path.dirname(local_path), exist_ok=True)

    logger.debug("Downloading s3://%s/%s to %s", bucket, key, local_path)
    s3_client.download_file(bucket, key, local_path)

    return local_path


def upload_to_s3(
    local_path: str, bucket: str, key: str, metadata: Optional[Dict[str, str]] = None
) -> Dict[str, str]:
    """
    Upload a file from a local path to S3.

    Args:
        local_path: Local path of the file to upload
        bucket: S3 bucket name
        key: S3 object key
        metadata: Optional metadata to attach to the S3 object

    Returns:
        Dictionary with bucket and key
    """
    logger.debug("Uploading %s to s3://%s/%s", local_path, bucket, key)

    extra_args = {}
    if metadata:
        extra_args["Metadata"] = metadata

    s3_client.upload_file(local_path, bucket, key, ExtraArgs=extra_args)

    return {"bucket": bucket, "key": key}


def send_sqs_message(
    queue_url: str, message_body: Dict[str, Any], delay_seconds: int = 0
) -> Dict[str, Any]:
    """
    Send a message to an SQS queue.

    Args:
        queue_url: URL of the SQS queue
        message_body: Message body as a dictionary
        delay_seconds: Delay in seconds before the message is available

    Returns:
        SQS response
    """
    logger.debug("Sending message to %s", queue_url)

    response = sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(message_body),
        DelaySeconds=delay_seconds,
    )

    return response


def parse_s3_event(event: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Parse an S3 event from Lambda and extract bucket and key information.

    Args:
        event: Lambda event object

    Returns:
        List of dictionaries with bucket and key
    """
    s3_records = []

    try:
        records = event.get("Records", [])

        for record in records:
            if record.get("eventSource") == "aws:s3":
                s3_info = record.get("s3", {})
                bucket = s3_info.get("bucket", {}).get("name")
                key = s3_info.get("object", {}).get("key")

                if bucket and key:
                    s3_records.append({"bucket": bucket, "key": key})
    except KeyError as e:
        logger.error("Missing key in S3 event: %s", e)
    except AttributeError as e:
        logger.error("Attribute error while parsing S3 event: %s", e)

    return s3_records


def parse_sqs_event(event: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parse an SQS event from Lambda and extract message bodies.

    Args:
        event: Lambda event object

    Returns:
        List of parsed message bodies
    """
    messages = []

    try:
        records = event.get("Records", [])

        for record in records:
            if record.get("eventSource") == "aws:sqs":
                body = record.get("body")

                if body:
                    try:
                        parsed_body = json.loads(body)
                        messages.append(parsed_body)
                    except json.JSONDecodeError:
                        logger.error("Error parsing SQS message body: %s", body)
                        messages.append({"raw_body": body})
    except (KeyError, json.JSONDecodeError, AttributeError) as e:
        logger.error("Error parsing SQS event: %s", e)
    return messages


def generate_s3_key(original_key: str, stage: str, extension: str = None) -> str:
    """
    Generate an S3 key for a processed file based on the original key.

    Args:
        original_key: Original S3 key
        stage: Processing stage (e.g., 'html', 'audit', 'remediated')
        extension: Optional file extension to use

    Returns:
        Generated S3 key
    """
    # Extract the base filename without extension
    base_name = os.path.splitext(os.path.basename(original_key))[0]

    # If no extension provided, use the original extension
    if not extension:
        extension = os.path.splitext(original_key)[1]
        if not extension:
            extension = ".html"  # Default to .html if no extension

    # Ensure extension starts with a dot
    if not extension.startswith("."):
        extension = f".{extension}"

    # Generate the new key
    return f"{stage}/{base_name}{extension}"

def upload_directory_to_s3(local_dir: str, bucket: str, prefix: str) -> List[Dict[str, str]]:
    """
    Upload a directory and its contents to S3.

    Args:
        local_dir: Local directory to upload
        bucket: S3 bucket name
        prefix: S3 key prefix (folder path)

    Returns:
        List of dictionaries with bucket and key for each uploaded file
    """
    if not os.path.isdir(local_dir):
        logger.error(f"Not a directory: {local_dir}")
        return []

    uploaded_files = []
    
    # Ensure prefix ends with a slash if it's not empty
    if prefix and not prefix.endswith('/'):
        prefix = f"{prefix}/"
        
    # Walk through the directory and upload all files
    for root, _, files in os.walk(local_dir):
        for file in files:
            local_path = os.path.join(root, file)
            
            # Calculate the relative path from the local_dir
            rel_path = os.path.relpath(local_path, local_dir)
            
            # Create the S3 key by combining the prefix and relative path
            s3_key = f"{prefix}{rel_path}"
            
            # Determine content type based on file extension
            content_type = None
            if file.lower().endswith('.html'):
                content_type = 'text/html'
            elif file.lower().endswith('.css'):
                content_type = 'text/css'
            elif file.lower().endswith('.js'):
                content_type = 'application/javascript'
            elif file.lower().endswith('.png'):
                content_type = 'image/png'
            elif file.lower().endswith(('.jpg', '.jpeg')):
                content_type = 'image/jpeg'
            
            # Prepare extra args for upload
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            
            try:
                # Upload the file
                s3_client.upload_file(local_path, bucket, s3_key, ExtraArgs=extra_args)
                uploaded_files.append({"bucket": bucket, "key": s3_key})
                logger.debug(f"Uploaded {local_path} to s3://{bucket}/{s3_key}")
            except Exception as e:
                logger.error(f"Failed to upload {local_path} to S3: {e}")
    
    return uploaded_files


def generate_job_id(bucket: str, key: str) -> str:
    """
    Generate a unique job ID based on the S3 bucket and key.

    Args:
        bucket: S3 bucket name
        key: S3 object key

    Returns:
        Unique job ID
    """
    # Create a unique string based on bucket, key, and current timestamp
    unique_string = f"{bucket}:{key}:{time.time()}"

    # Generate a hash
    hash_object = hashlib.md5(unique_string.encode(), usedforsecurity=False)

    # Return the first 12 characters of the hash
    return hash_object.hexdigest()[:12]
