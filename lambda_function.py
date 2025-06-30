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
        output_check_key = f"output/{filename_base}.zip"
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
                perform_remediation=True,
                conversion_options={
                    "cleanup_bda_output": True,
                    "single_file": True
                }
            )
            print(f"[INFO] Processing complete. Result: {conversion_result}")
        except Exception as e:
            print(f"[ERROR] Processing {key} failed: {e}")
            print(traceback.format_exc())
            return {"status": "error", "message": str(e)}

        # 4) Create a zip file with all output files (like the CLI does)
        try:
            # Upload only the index.html file for compatibility with existing code
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
                index_s3_key = f"output/{filename_base}.html"
                s3.upload_file(index_html_path, bucket, index_s3_key)
                print(f"[INFO] Uploaded index.html to s3://{bucket}/{index_s3_key}")
            else:
                print(f"[WARNING] No index.html found in output directory")
                
            # 5) Clean up Bedrock intermediate files - COMMENTED OUT TO PRESERVE OUTPUT FILES
            """
            try:
                # Delete the entire Bedrock output folder to prevent accumulation
                bedrock_prefix = f"output/{filename_base}/"
                print(f"[INFO] Cleaning up Bedrock intermediate files at s3://{bucket}/{bedrock_prefix}")
                
                # List all objects in the prefix
                objects_to_delete = []
                paginator = s3.get_paginator('list_objects_v2')
                for page in paginator.paginate(Bucket=bucket, Prefix=bedrock_prefix):
                    if 'Contents' in page:
                        for obj in page['Contents']:
                            objects_to_delete.append({'Key': obj['Key']})
                
                # Delete in batches of 1000 (S3 limit)
                for i in range(0, len(objects_to_delete), 1000):
                    response = s3.delete_objects(
                        Bucket=bucket,
                        Delete={'Objects': objects_to_delete[i:i+1000]}
                    )
                    print(f"[INFO] Deleted {len(response.get('Deleted', []))} files from {bedrock_prefix}")
                    
            except Exception as cleanup_error:
                print(f"[WARNING] Failed to clean up Bedrock intermediate files: {cleanup_error}")
            """
            print(f"[INFO] Skipping cleanup of Bedrock intermediate files to preserve output files")
            
            # MOVED: Create the zip file at the end after all processing is complete
            # This ensures all files are included in the zip
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
            
            # Upload zip to the output folder so head_object can detect it
            # This MUST match the path we check in the idempotency check above
            output_s3_key = f"output/{filename_base}.zip"
            s3.upload_file(zip_path, bucket, output_s3_key)
            print(f"[INFO] Uploaded complete zip file to s3://{bucket}/{output_s3_key}")
            
            # Create a separate "final" zip for the remediated folder with only specific files
            final_zip_path = f"/tmp/final_{filename_base}.zip"
            
            # List of files/folders to include in the final zip
            include_patterns = [
                "remediated_html/",
                "usage_data.json",
                "remediation_report.html"
            ]
            
            with zipfile.ZipFile(final_zip_path, 'w', zipfile.ZIP_DEFLATED) as final_zipf:
                # Walk through the output directory and add only specific files to zip
                for root, dirs, files in os.walk(temp_output_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        # Calculate relative path to maintain directory structure
                        rel_path = os.path.relpath(file_path, temp_output_dir)
                        
                        # Check if this file should be included
                        should_include = False
                        for pattern in include_patterns:
                            if pattern.lower() in rel_path.lower():
                                should_include = True
                                break
                        
                        if should_include:
                            final_zipf.write(file_path, rel_path)
                            print(f"[INFO] Added to final zip: {rel_path}")
            
            # Upload the final zip to the remediated folder
            remediated_s3_key = f"remediated/final_{filename_base}.zip"
            s3.upload_file(final_zip_path, bucket, remediated_s3_key)
            print(f"[INFO] Uploaded final zip file to s3://{bucket}/{remediated_s3_key}")
                
        except Exception as e:
            print(f"[ERROR] Creating or uploading zip failed: {e}")
            print(traceback.format_exc())
            return {"status": "error", "message": f"Zip creation or upload failed: {e}"}

        return {
            "status": "done",
            "execution_id": context.aws_request_id,
            "input": f"s3://{bucket}/{key}",
            "output_dir": f"s3://{bucket}/output/",
            "output_zip": f"s3://{bucket}/output/{filename_base}.zip",
            "remediated_zip": f"s3://{bucket}/remediated/final_{filename_base}.zip"
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