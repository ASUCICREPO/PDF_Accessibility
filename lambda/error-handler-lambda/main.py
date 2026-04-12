"""
Error handler Lambda for the PDF Accessibility remediation workflow.
Writes a failure status file to S3 so the frontend can detect processing failures
instead of polling indefinitely.
"""
import json
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client('s3')


def lambda_handler(event, context):
    """
    Handles Step Function errors by writing a failure marker to S3.
    
    The event contains the original workflow input (s3_bucket, chunks)
    plus error details injected by the Step Functions Catch block.
    Writes a FAILED_<filename>.json file to the result/ prefix so the
    frontend can detect the failure and stop polling.
    """
    logger.info(f"Error handler invoked with event: {json.dumps(event)}")
    
    try:
        bucket_name = event.get("s3_bucket", "")
        chunks = event.get("chunks", [])
        error_info = event.get("errorInfo", {})
        error = error_info.get("Error", "Unknown")
        cause = error_info.get("Cause", "Unknown")
        
        # Extract the base filename from the first chunk's s3_key
        # Format: temp/<basename>/<basename>_chunk_1.pdf
        file_basename = ""
        if chunks:
            first_key = chunks[0].get("s3_key", "")
            parts = first_key.split("/")
            if len(parts) >= 2:
                file_basename = parts[1]
        
        if not bucket_name or not file_basename:
            logger.error("Could not determine bucket or filename from event")
            return {"status": "error", "message": "Missing bucket or filename"}
        
        # Write failure status file to result/ prefix where the frontend polls
        failure_status = {
            "status": "FAILED",
            "error": error,
            "cause": cause,
            "filename": file_basename
        }
        
        status_key = f"result/FAILED_{file_basename}.json"
        s3_client.put_object(
            Bucket=bucket_name,
            Key=status_key,
            Body=json.dumps(failure_status),
            ContentType="application/json"
        )
        
        logger.info(f"File: {file_basename}, Status: Failed - wrote failure marker to s3://{bucket_name}/{status_key}")
        
        return {
            "status": "FAILED",
            "filename": file_basename,
            "error": error,
            "statusFileKey": status_key
        }
        
    except Exception as e:
        logger.error(f"Error handler failed: {e}")
        return {"status": "error", "message": str(e)}
