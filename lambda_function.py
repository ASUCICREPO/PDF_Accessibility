import os
import boto3
import json
import traceback
import zipfile
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

        # 2) Download PDF to /tmp with original filename
        original_filename = os.path.basename(key)
        filename_base = os.path.splitext(original_filename)[0]
        local_in = f"/tmp/{original_filename}"
        try:
            s3.download_file(bucket, key, local_in)
            print(f"[INFO] Downloaded s3://{bucket}/{key} to {local_in}")
        except Exception as e:
            print(f"[ERROR] Failed to download s3://{bucket}/{key}: {e}")
            print(traceback.format_exc())
            return {"status": "error", "message": f"Download failed: {e}"}

        # 3) Run the API exactly as the CLI would
        local_out = f"/tmp/{filename_base}"
        os.makedirs(local_out, exist_ok=True)
        try:
            print(f"[INFO] Processing PDF: {local_in}")
            
            # Process the PDF using the API with the same options as CLI
            conversion_result = process_pdf_accessibility(
                pdf_path=local_in, 
                output_dir=local_out,
                perform_audit=True,
                perform_remediation=True
            )
            print(f"[INFO] Processing complete. Result: {conversion_result}")
        except Exception as e:
            print(f"[ERROR] Processing {key} failed: {e}")
            print(traceback.format_exc())
            return {"status": "error", "message": str(e)}

        # 4) Create a zip file with the same structure as CLI output
        try:
            # Create a zip file in /tmp
            zip_path = f"/tmp/{filename_base}.zip"
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Walk through the output directory and add files to zip
                for root, dirs, files in os.walk(local_out):
                    for file in files:
                        file_path = os.path.join(root, file)
                        # Calculate relative path to maintain directory structure
                        rel_path = os.path.relpath(file_path, local_out)
                        zipf.write(file_path, rel_path)
                        print(f"[INFO] Added to zip: {rel_path}")
            
            # Upload the zip file to S3
            s3_key = f"remediated/{filename_base}/{filename_base}.zip"
            s3.upload_file(zip_path, bucket, s3_key)
            print(f"[INFO] Uploaded zip file to s3://{bucket}/{s3_key}")
            
            # Also upload individual files to maintain compatibility with existing code
            uploaded_files = []
            for root, dirs, files in os.walk(local_out):
                for file in files:
                    local_path = os.path.join(root, file)
                    rel_path = os.path.relpath(local_path, local_out)
                    
                    # Upload to output/[filename_base]/ folder
                    s3_key = f"output/{filename_base}/{rel_path}"
                    s3.upload_file(local_path, bucket, s3_key)
                    uploaded_files.append(s3_key)
                    print(f"[INFO] Uploaded: {s3_key}")
            
            print(f"[INFO] Uploaded {len(uploaded_files)} files to s3://{bucket}/output/{filename_base}/")
            
            # Print the directory structure for debugging
            print("[INFO] Directory structure in local_out:")
            for root, dirs, files in os.walk(local_out):
                rel_root = os.path.relpath(root, local_out)
                print(f"[INFO] Directory: {rel_root}")
                for file in files:
                    print(f"[INFO]   File: {file}")
            
        except Exception as e:
            print(f"[ERROR] Uploading results failed: {e}")
            print(traceback.format_exc())
            return {"status": "error", "message": f"Upload failed: {e}"}

        return {
            "status": "done",
            "input": f"s3://{bucket}/{key}",
            "output_dir": f"s3://{bucket}/output/{filename_base}/",
            "output_zip": f"s3://{bucket}/output/{filename_base}/{filename_base}.zip",
            "uploaded_files": len(uploaded_files) + 1  # +1 for the zip file
        }
    except Exception as e:
        print(f"[ERROR] Unhandled exception: {e}")
        print(traceback.format_exc())
        return {"status": "error", "message": f"Unhandled exception: {e}"}
