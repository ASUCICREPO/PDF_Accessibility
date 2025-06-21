import os
import boto3
import json
import traceback
from content_accessibility_utility_on_aws.api import process_pdf_accessibility

s3 = boto3.client("s3")

def lambda_handler(event, context):
    """
    Lambda handler for processing PDF files uploaded to S3.
    
    Args:
        event: S3 event notification
        context: Lambda context
        
    Returns:
        Dict: Status of the processing
    """
    try:
        # 1) Extract bucket/key from the S3 event
        print(f"Received event: {json.dumps(event)}")
        
        if not event.get("Records") or len(event["Records"]) == 0:
            print(f"[WARNING] No records found in event: {event}")
            return {"status": "error", "message": "No records found in event"}
            
        record = event["Records"][0]["s3"]
        bucket = record["bucket"]["name"]
        key = record["object"]["key"]
        
        print(f"[INFO] Processing s3://{bucket}/{key}")
        
        # Check if the key is in the uploads/ folder to prevent infinite loops
        if not key.startswith("uploads/"):
            print(f"[INFO] Skipping non-uploads file: {key}")
            return {"status": "skipped", "message": "Not in uploads/ folder"}

        # 2) Download PDF to /tmp
        local_in = "/tmp/input.pdf"
        try:
            s3.download_file(bucket, key, local_in)
            print(f"[INFO] Downloaded s3://{bucket}/{key} to {local_in}")
        except Exception as e:
            print(f"[ERROR] Failed to download s3://{bucket}/{key}: {e}")
            print(traceback.format_exc())
            # Exit cleanly so Lambda doesn't retry endlessly
            return {"status": "error", "message": f"Download failed: {e}"}

        # 3) Run your API (wrapped in try/except to swallow errors)
        local_out = "/tmp/output"
        os.makedirs(local_out, exist_ok=True)
        try:
            print(f"[INFO] Processing PDF: {local_in}")
            conversion_result = process_pdf_accessibility(pdf_path=local_in, output_dir=local_out)
            print(f"[INFO] Processing complete. Result: {conversion_result}")
        except Exception as e:
            print(f"[ERROR] Processing {key} failed: {e}")
            print(traceback.format_exc())
            return {"status": "error", "message": str(e)}

        # 4) Upload results back to S3 (remediated/ and output/)
        try:
            uploaded_files = []
            for root, _, files in os.walk(local_out):
                for fname in files:
                    full = os.path.join(root, fname)
                    rel = os.path.relpath(full, local_out)
                    dest = f"remediated/{rel}"
                    s3.upload_file(full, bucket, dest)
                    uploaded_files.append(dest)
            
            print(f"[INFO] Uploaded {len(uploaded_files)} files to s3://{bucket}/remediated/")
        except Exception as e:
            print(f"[ERROR] Uploading results failed: {e}")
            print(traceback.format_exc())
            return {"status": "error", "message": f"Upload failed: {e}"}

        return {
            "status": "done",
            "input": f"s3://{bucket}/{key}",
            "output_dir": f"s3://{bucket}/remediated/",
            "files_processed": len(uploaded_files)
        }
    except Exception as e:
        print(f"[ERROR] Unhandled exception: {e}")
        print(traceback.format_exc())
        return {"status": "error", "message": f"Unhandled exception: {e}"}
