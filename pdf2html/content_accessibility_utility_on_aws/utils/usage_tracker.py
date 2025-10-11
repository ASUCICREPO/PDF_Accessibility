# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Usage Tracker module for Document Accessibility.

This module provides tracking capabilities for AWS Bedrock and BDA usage.
It records usage metrics for the current session and supports exporting to S3.
"""

import os
import uuid
import json
import boto3
from datetime import datetime
from typing import Dict, Any, Optional

from content_accessibility_utility_on_aws.utils.logging_helper import setup_logger

# Set up module-level logger
logger = setup_logger(__name__)


class SessionUsageTracker:
    """
    Tracks usage metrics for the current document accessibility processing session.

    This class maintains in-memory tracking of Bedrock API calls and BDA processing
    for the duration of a single processing session.
    """

    _instance = None

    @classmethod
    def get_instance(cls):
        """
        Get or create the singleton instance of SessionUsageTracker.

        Returns:
            SessionUsageTracker: The singleton instance
        """
        if cls._instance is None:
            cls._instance = SessionUsageTracker()
        return cls._instance

    def __init__(self):
        """Initialize a new SessionUsageTracker."""
        self.session_id = str(uuid.uuid4())
        self.start_time = datetime.utcnow()
        self.end_time = None
        self.bda_usage = {
            "total_documents_processed": 0,
            "total_pages_processed": 0,
            "project_arn": None,
            "processing_details": []
        }
        self.bedrock_usage = {
            "total_calls": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "calls_by_model": {},
            "calls_by_purpose": {},
            "call_details": []
        }

    def track_bedrock_call(
        self,
        model_id: str,
        purpose: str,
        input_tokens: int,
        output_tokens: int,
        processing_time_ms: Optional[int] = None
    ) -> None:
        """
        Track a single Bedrock API call.

        Args:
            model_id: The Bedrock model ID used
            purpose: The purpose of the call (e.g., 'alt_text_generation')
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            processing_time_ms: Optional processing time in milliseconds
        """
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        # Update total counts
        self.bedrock_usage["total_calls"] += 1
        self.bedrock_usage["total_input_tokens"] += input_tokens
        self.bedrock_usage["total_output_tokens"] += output_tokens
        
        # Update model-specific stats
        if model_id not in self.bedrock_usage["calls_by_model"]:
            self.bedrock_usage["calls_by_model"][model_id] = {
                "total_calls": 0,
                "input_tokens": 0,
                "output_tokens": 0
            }
        
        self.bedrock_usage["calls_by_model"][model_id]["total_calls"] += 1
        self.bedrock_usage["calls_by_model"][model_id]["input_tokens"] += input_tokens
        self.bedrock_usage["calls_by_model"][model_id]["output_tokens"] += output_tokens
        
        # Update purpose-specific stats
        if purpose not in self.bedrock_usage["calls_by_purpose"]:
            self.bedrock_usage["calls_by_purpose"][purpose] = {
                "total_calls": 0,
                "input_tokens": 0,
                "output_tokens": 0
            }
        
        self.bedrock_usage["calls_by_purpose"][purpose]["total_calls"] += 1
        self.bedrock_usage["calls_by_purpose"][purpose]["input_tokens"] += input_tokens
        self.bedrock_usage["calls_by_purpose"][purpose]["output_tokens"] += output_tokens
        
        # Add detailed record
        call_detail = {
            "timestamp": timestamp,
            "model_id": model_id,
            "purpose": purpose,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens
        }
        
        if processing_time_ms is not None:
            call_detail["processing_time_ms"] = processing_time_ms
            
        self.bedrock_usage["call_details"].append(call_detail)
        
        logger.debug(f"Tracked Bedrock call: model={model_id}, purpose={purpose}, input_tokens={input_tokens}, output_tokens={output_tokens}")

    def track_bda_processing(
        self,
        project_arn: str,
        document_id: str,
        page_count: int,
        processing_time_ms: Optional[int] = None
    ) -> None:
        """
        Track BDA document processing.

        Args:
            project_arn: The BDA project ARN
            document_id: ID of the document processed
            page_count: Number of pages in the document
            processing_time_ms: Optional processing time in milliseconds
        """
        # Set project ARN if not already set
        if not self.bda_usage["project_arn"]:
            self.bda_usage["project_arn"] = project_arn
            
        # Update total counts
        self.bda_usage["total_documents_processed"] += 1
        self.bda_usage["total_pages_processed"] += page_count
        
        # Add detailed record
        processing_detail = {
            "document_id": document_id,
            "pages": page_count,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        if processing_time_ms is not None:
            processing_detail["processing_time_ms"] = processing_time_ms
            
        self.bda_usage["processing_details"].append(processing_detail)
        
        logger.debug(f"Tracked BDA processing: document={document_id}, pages={page_count}")

    def finalize_session(self) -> None:
        """Mark the session as complete and record the end time."""
        self.end_time = datetime.utcnow()

    def get_usage_data(self) -> Dict[str, Any]:
        """
        Get the complete usage data for the session.

        Returns:
            Dict containing all usage data
        """
        # Update end time if not already set
        if not self.end_time:
            self.end_time = datetime.utcnow()
            
        return {
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat() + "Z",
            "end_time": self.end_time.isoformat() + "Z",
            "bda_usage": self.bda_usage,
            "bedrock_usage": self.bedrock_usage
        }

    def save_to_file(
        self,
        output_path: str
    ) -> str:
        """
        Save usage data to a local file.

        Args:
            output_path: Path to save the JSON file

        Returns:
            Path to the saved file

        Raises:
            Exception: If there's an error saving to file
        """
        try:
            # Get the usage data and convert to JSON
            usage_data = self.get_usage_data()
            json_data = json.dumps(usage_data, indent=2)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(json_data)
                
            logger.info(f"Usage data saved to file: {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.warning(f"Failed to save usage data to file: {e}")
            raise

    def save_to_s3(
        self,
        bucket_name: str,
        prefix: Optional[str] = None,
        profile: Optional[str] = None
    ) -> str:
        """
        Save usage data to S3.

        Args:
            bucket_name: S3 bucket name
            prefix: Optional prefix for the S3 key
            profile: Optional AWS profile name

        Returns:
            S3 URI of the saved file

        Raises:
            Exception: If there's an error saving to S3
        """
        try:
            # Create a boto3 session with the provided profile
            session = boto3.Session(profile_name=profile) if profile else boto3.Session()
            s3_client = session.client('s3')
            
            # Ensure we have end time set
            if not self.end_time:
                self.end_time = datetime.utcnow()
                
            # Format the key path
            date_str = self.start_time.strftime("%Y-%m-%d")
            timestamp_str = self.start_time.strftime("%Y%m%d-%H%M%S")
            
            key_parts = []
            if prefix:
                key_parts.append(prefix.rstrip('/'))
                
            key_parts.extend([
                "document-accessability-usage",
                date_str,
                f"document-accessibility-usage-{timestamp_str}.json"
            ])
            
            key = '/'.join(key_parts)
            
            # Get the usage data and convert to JSON
            usage_data = self.get_usage_data()
            json_data = json.dumps(usage_data, indent=2)
            
            # Upload to S3
            s3_client.put_object(
                Bucket=bucket_name,
                Key=key,
                Body=json_data,
                ContentType='application/json'
            )
            
            s3_uri = f"s3://{bucket_name}/{key}"
            logger.info(f"Usage data saved to S3: {s3_uri}")
            
            return s3_uri
            
        except Exception as e:
            logger.warning(f"Failed to save usage data to S3: {e}")
            raise

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Estimate the number of tokens in a text string.

        This is a simple approximation method. For production use, consider using a 
        proper tokenizer library or the Bedrock TokenCount API.

        Args:
            text: The input text

        Returns:
            Estimated number of tokens
        """
        if not text:
            return 0
            
        # Simple approximation: ~4 characters per token
        return max(1, len(text) // 4)
