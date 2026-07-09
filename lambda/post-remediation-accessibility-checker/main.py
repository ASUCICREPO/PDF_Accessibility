import json
import os

import boto3

s3 = boto3.client("s3")


def lambda_handler(event, context):
    """
    No-Adobe placeholder for the post-remediation checker.

    The title-generator Lambda usually returns:
    {
      "Payload": {
        "statusCode": 200,
        "body": {
          "bucket": "...",
          "save_path": "...",
          "title": "..."
        }
      }
    }

    This function preserves the payload and writes a small report artifact.
    """
    print("Received event:", json.dumps(event))

    payload = event.get("Payload", {}) if isinstance(event, dict) else {}
    body = payload.get("body", {}) if isinstance(payload, dict) else {}

    bucket = body.get("bucket")
    save_path = body.get("save_path")

    basename = "unknown"
    if save_path:
        filename = os.path.basename(save_path)
        basename = os.path.splitext(filename.replace("COMPLIANT_", "", 1))[0]

    report = {
        "checker": "no-adobe-placeholder",
        "stage": "after_remediation",
        "status": "skipped",
        "reason": "Adobe PDF Accessibility Checker API disabled for OpenDataLoader branch.",
        "manual_review_required": True,
        "remediated_pdf": save_path,
        "title": body.get("title"),
    }

    if bucket and basename != "unknown":
        key = (
            f"temp/{basename}/accessability-report/"
            f"{basename}_accessibility_report_after_remediation_placeholder.json"
        )
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(report, indent=2).encode("utf-8"),
            ContentType="application/json",
        )
        print(f"Uploaded placeholder report to s3://{bucket}/{key}")
    else:
        print("Skipping S3 report upload because bucket or save_path was missing.")

    return event
