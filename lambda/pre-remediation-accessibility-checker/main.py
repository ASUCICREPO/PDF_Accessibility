import json
import os

import boto3

s3 = boto3.client("s3")


def _safe_basename_from_event(event):
    chunks = event.get("chunks") or []
    if not chunks:
        return "unknown"

    key = chunks[0].get("s3_key", "")
    filename = os.path.basename(key)

    if "_chunk_" in filename:
        return filename.split("_chunk_")[0]

    return os.path.splitext(filename)[0]


def lambda_handler(event, context):
    """
    No-Adobe placeholder for the pre-remediation checker.

    This preserves the Step Functions branch while Adobe's
    PDFAccessibilityCheckerJob is disabled for the OpenDataLoader branch.
    """
    print("Received event:", json.dumps(event))

    bucket = event.get("s3_bucket")
    basename = _safe_basename_from_event(event)

    report = {
        "checker": "no-adobe-placeholder",
        "stage": "before_remediation",
        "status": "skipped",
        "reason": "Adobe PDF Accessibility Checker API disabled for OpenDataLoader branch.",
        "manual_review_required": True,
        "input_event_summary": {
            "chunk_count": len(event.get("chunks") or []),
            "s3_bucket_present": bool(bucket),
        },
    }

    if bucket and basename != "unknown":
        key = (
            f"temp/{basename}/accessability-report/"
            f"{basename}_accessibility_report_before_remediation_placeholder.json"
        )
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(report, indent=2).encode("utf-8"),
            ContentType="application/json",
        )
        print(f"Uploaded placeholder report to s3://{bucket}/{key}")
    else:
        print("Skipping S3 report upload because bucket or basename was missing.")

    return event
