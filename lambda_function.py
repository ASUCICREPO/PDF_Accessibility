import os
import boto3
import json
import traceback
import zipfile
import tempfile
import shutil
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
    # Create a variable to track the temporary directory for cleanup in finally block
    temp_output_dir = None
    
    try:
        # 1) Extract bucket/key from the S3 event
        print(f"Received event: {json.dumps(event)}")
        print(f"[INFO] Lambda execution ID: {context.aws_request_id}")
        
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
            
        # Additional check to ensure we're only processing PDF files
        if not key.lower().endswith('.pdf'):
            print(f"[INFO] Skipping non-PDF file: {key}")
            return {"status": "skipped", "message": "Not a PDF file"}
            
        # Extract filename for output paths
        original_filename = os.path.basename(key)
        filename_base = os.path.splitext(original_filename)[0]
        
        # IDEMPOTENCY CHECK: Check if output already exists
        output_check_key = f"output/{filename_base}/{filename_base}.zip"
        try:
            # Try to head the object - if it exists, we've already processed this file
            s3.head_object(Bucket=bucket, Key=output_check_key)
            print(f"[INFO] Output already exists for {key}, skipping processing")
            return {
                "status": "skipped", 
                "message": "Output already exists",
                "input": f"s3://{bucket}/{key}",
                "output_dir": f"s3://{bucket}/output/{filename_base}/"
            }
        except s3.exceptions.ClientError as e:
            # If we get a 404, the file doesn't exist and we should process it
            if e.response['Error']['Code'] != '404':
                # If it's not a 404, something else went wrong
                raise e
            # Otherwise continue with processing
            print(f"[INFO] No existing output found, proceeding with processing")

        # 2) Download PDF to /tmp with original filename
        local_in = f"/tmp/{original_filename}"
        try:
            s3.download_file(bucket, key, local_in)
            print(f"[INFO] Downloaded s3://{bucket}/{key} to {local_in}")
        except Exception as e:
            print(f"[ERROR] Failed to download s3://{bucket}/{key}: {e}")
            print(traceback.format_exc())
            return {"status": "error", "message": f"Download failed: {e}"}

        # Create a temporary directory for processing (like the CLI does)
        temp_output_dir = tempfile.mkdtemp(prefix="accessibility_", dir="/tmp")
        print(f"[INFO] Created temporary directory for processing: {temp_output_dir}")

        # 3) Run the API exactly as the CLI would
        try:
            print(f"[INFO] Processing PDF: {local_in}")
            
            # Process the PDF using the API with the same options as CLI
            conversion_result = process_pdf_accessibility(
                pdf_path=local_in, 
                output_dir=temp_output_dir,
                perform_audit=True,
                perform_remediation=True
            )
            print(f"[INFO] Processing complete. Result: {conversion_result}")
        except Exception as e:
            print(f"[ERROR] Processing {key} failed: {e}")
            print(traceback.format_exc())
            return {"status": "error", "message": str(e)}

        # 4) Create a zip file with all output files (like the CLI does)
        try:
            # Create a zip file in /tmp
            zip_path = f"/tmp/{filename_base}.zip"
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Walk through the output directory and add files to zip
                for root, dirs, files in os.walk(temp_output_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        # Calculate relative path to maintain directory structure
                        rel_path = os.path.relpath(file_path, temp_output_dir)
                        zipf.write(file_path, rel_path)
                        print(f"[INFO] Added to zip: {rel_path}")
            
            # Upload the zip file directly to output/ and remediated/ folders (no nested folders)
            # output_s3_key = f"output/{filename_base}.zip"
            # s3.upload_file(zip_path, bucket, output_s3_key)
            # print(f"[INFO] Uploaded zip file to s3://{bucket}/{output_s3_key}")
            
             # Also upload a copy to the remediated folder
            remediated_s3_key = f"remediated/{filename_base}.zip"
            s3.upload_file(zip_path, bucket, remediated_s3_key)
            print(f"[INFO] Uploaded zip file to s3://{bucket}/{remediated_s3_key}")
            
            # Upload only the index.html file for compatibility with existing code
            # First check if it exists directly in the temp directory
            index_html_path = os.path.join(temp_output_dir, "index.html")
            if not os.path.exists(index_html_path):
                # If not found directly, look for it in subdirectories
                for root, _, files in os.walk(temp_output_dir):
                    for file in files:
                        if file == "index.html":
                            index_html_path = os.path.join(root, file)
                            break
                    if os.path.exists(index_html_path):
                        break
            
            if os.path.exists(index_html_path):
                index_s3_key = f"output/{filename_base}/index.html"
                s3.upload_file(index_html_path, bucket, index_s3_key)
                print(f"[INFO] Uploaded index.html to s3://{bucket}/{index_s3_key}")
            else:
                print(f"[WARNING] No index.html found in output directory")
                
        except Exception as e:
            print(f"[ERROR] Creating or uploading zip failed: {e}")
            print(traceback.format_exc())
            return {"status": "error", "message": f"Zip creation or upload failed: {e}"}

        return {
            "status": "done",
            "execution_id": context.aws_request_id,
            "input": f"s3://{bucket}/{key}",
            "output_dir": f"s3://{bucket}/output/{filename_base}/",
            "output_zip": f"s3://{bucket}/output/{filename_base}/{filename_base}.zip",
            "remediated_zip": f"s3://{bucket}/remediated/{filename_base}/{filename_base}.zip"
        }
    except Exception as e:
        print(f"[ERROR] Unhandled exception: {e}")
        print(traceback.format_exc())
        return {"status": "error", "message": f"Unhandled exception: {e}"}
    finally:
        # Make sure we clean up the temporary directory even if there's an error
        try:
            if temp_output_dir and os.path.exists(temp_output_dir):
                shutil.rmtree(temp_output_dir)
                print(f"[INFO] Cleaned up temporary directory: {temp_output_dir}")
        except Exception as e:
            print(f"[WARNING] Failed to clean up temporary directory: {e}")