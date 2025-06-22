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
            conversion_result = process_pdf_accessibility(
                pdf_path=local_in, 
                output_dir=local_out,
                perform_audit=True,
                perform_remediation=True  # Enable remediation
            )
            print(f"[INFO] Processing complete. Result: {conversion_result}")
        except Exception as e:
            print(f"[ERROR] Processing {key} failed: {e}")
            print(traceback.format_exc())
            return {"status": "error", "message": str(e)}

        # 4) Upload results back to S3 (remediated/ and output/)
        try:
            # Lists to track uploaded files
            output_files = []
            remediated_files = []
            
            # Set to track processed images to avoid duplicates (using full paths)
            processed_images = set()
            
            # Identify remediated content
            remediated_html_dir = os.path.join(local_out, "remediated_html")
            remediated_combined_file = os.path.join(local_out, "remediated_combined_document.html")
            
            # Track which files have been uploaded as remediated content
            uploaded_as_remediated = set()
            
            # STEP 1: Upload remediated HTML content
            
            # Check for remediated_html directory (multi-page mode)
            if os.path.exists(remediated_html_dir):
                print(f"[INFO] Found remediated_html directory: {remediated_html_dir}")
                
                # Upload all HTML files from remediated_html directory
                for root, _, files in os.walk(remediated_html_dir):
                    for file in files:
                        if file.lower().endswith('.html'):
                            local_file = os.path.join(root, file)
                            # Get relative path from remediated_html directory
                            rel_path = os.path.relpath(local_file, remediated_html_dir)
                            # Upload to remediated/ folder
                            s3_key = f"remediated/{rel_path}"
                            s3.upload_file(local_file, bucket, s3_key)
                            remediated_files.append(s3_key)
                            uploaded_as_remediated.add(local_file)
                            print(f"[INFO] Uploaded remediated HTML: {rel_path} to {s3_key}")
            
            # Check for remediated_combined_document.html file (single-page mode)
            if os.path.exists(remediated_combined_file):
                print(f"[INFO] Found remediated_combined_document.html file: {remediated_combined_file}")
                
                # Upload the remediated combined document
                filename = os.path.basename(remediated_combined_file)
                s3_key = f"remediated/{filename}"
                s3.upload_file(remediated_combined_file, bucket, s3_key)
                remediated_files.append(s3_key)
                uploaded_as_remediated.add(remediated_combined_file)
                print(f"[INFO] Uploaded remediated HTML: {filename} to {s3_key}")
            
            # STEP 2: Upload images for remediated content
            
            # For multi-page mode, check for images directory inside remediated_html
            if os.path.exists(remediated_html_dir):
                remediated_images_dir = os.path.join(remediated_html_dir, "images")
                if os.path.exists(remediated_images_dir) and os.path.isdir(remediated_images_dir):
                    print(f"[INFO] Found remediated images directory: {remediated_images_dir}")
                    for img_file in os.listdir(remediated_images_dir):
                        if img_file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                            img_path = os.path.join(remediated_images_dir, img_file)
                            
                            # Check for duplicates using full path
                            if img_path in processed_images:
                                print(f"[INFO] Skipping duplicate image by path: {img_path}")
                                continue
                            
                            processed_images.add(img_path)
                            uploaded_as_remediated.add(img_path)
                            
                            # Upload to remediated/images/ folder
                            s3_img_key = f"remediated/images/{img_file}"
                            s3.upload_file(img_path, bucket, s3_img_key)
                            remediated_files.append(s3_img_key)
                            print(f"[INFO] Uploaded remediated image: {img_file} to {s3_img_key}")
            
            # For single-page mode, check for images directory next to remediated_combined_document.html
            if os.path.exists(remediated_combined_file):
                images_dir = os.path.join(os.path.dirname(remediated_combined_file), "images")
                if os.path.exists(images_dir) and os.path.isdir(images_dir):
                    print(f"[INFO] Found remediated images directory for combined document: {images_dir}")
                    for img_file in os.listdir(images_dir):
                        if img_file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                            img_path = os.path.join(images_dir, img_file)
                            
                            # Check for duplicates using full path
                            if img_path in processed_images:
                                print(f"[INFO] Skipping duplicate image by path: {img_path}")
                                continue
                            
                            processed_images.add(img_path)
                            uploaded_as_remediated.add(img_path)
                            
                            # Upload to remediated/images/ folder
                            s3_img_key = f"remediated/images/{img_file}"
                            s3.upload_file(img_path, bucket, s3_img_key)
                            remediated_files.append(s3_img_key)
                            print(f"[INFO] Uploaded remediated image: {img_file} to {s3_img_key}")
            
            # STEP 3: Upload all other files to output/ folder
            for root, _, files in os.walk(local_out):
                for file in files:
                    local_file = os.path.join(root, file)
                    
                    # Skip files that have already been uploaded as remediated content
                    if local_file in uploaded_as_remediated:
                        continue
                    
                    # Get relative path from local_out directory
                    rel_path = os.path.relpath(local_file, local_out)
                    
                    # Upload to output/ folder
                    s3_key = f"output/{rel_path}"
                    s3.upload_file(local_file, bucket, s3_key)
                    output_files.append(s3_key)
            
            print(f"[INFO] Uploaded {len(remediated_files)} files to s3://{bucket}/remediated/")
            print(f"[INFO] Uploaded {len(output_files)} files to s3://{bucket}/output/")
            
        except Exception as e:
            print(f"[ERROR] Uploading results failed: {e}")
            print(traceback.format_exc())
            return {"status": "error", "message": f"Upload failed: {e}"}

        return {
            "status": "done",
            "input": f"s3://{bucket}/{key}",
            "remediated_dir": f"s3://{bucket}/remediated/",
            "output_dir": f"s3://{bucket}/output/",
            "remediated_files": len(remediated_files),
            "output_files": len(output_files)
        }
    except Exception as e:
        print(f"[ERROR] Unhandled exception: {e}")
        print(traceback.format_exc())
        return {"status": "error", "message": f"Unhandled exception: {e}"}
