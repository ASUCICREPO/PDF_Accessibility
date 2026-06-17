"""
Failure-handler Lambda for the PDF Accessibility remediation workflow.

This function is the single, exhaustive safety net for the Step Functions
state machine. It is wired to a `Catch` block that captures EVERY failure in
the pipeline -- both in-code errors (Adobe/Bedrock API failures, complexity
issues) and infrastructure failures (a container that cannot start, an
out-of-memory kill, a task timeout, an IAM error). Whenever the workflow
fails, Step Functions routes here instead of ending silently.

The frontend detects a finished job by polling the S3 `result/` folder. On
success the pipeline writes `result/COMPLIANT_<name>`. This function provides
the missing failure signal in the SAME place the frontend already looks:

    result/FAILED_<name>.json

so the UI can stop polling and show the user WHY the job failed and WHERE
(which chunk / page range), instead of spinning indefinitely.

Detail sources (in priority order):
  1. Per-station detail files at `temp/<basename>/_errors/*.json`, written by
     each station right before it exits on failure. These carry the rich
     reason + chunk + page-range context that only the station knows.
  2. The Step Functions error `Cause`/`Error`, used as a fallback when a
     station died before it could write a detail file (pure infra failure).

The function NEVER raises: a safety net that can itself fail is not a safety
net. Any internal problem is logged and a best-effort marker is still written.
"""

import json
import os
import boto3
from datetime import datetime, timezone

s3_client = boto3.client("s3")

# Human-readable summaries for each reason category. The category itself is
# emitted by the stations; this map is only for the user-facing message.
REASON_SUMMARIES = {
    "SPLIT": "The document could not be split into pages for processing.",
    "ADOBE_API": "Adobe API failed for this document. This document may be too complex for our Adobe API to handle.",
    "BEDROCK_API": "The AI model (Amazon Bedrock) failed while generating alt text.",
    "COMPLEXITY": "The document exceeded processing complexity limits.",
    "MERGE": "The processed pages could not be merged back into one document.",
    "TITLE": "The document title/metadata step failed.",
    "INFRA": "A processing task failed to run (infrastructure-level failure).",
    "UNKNOWN": "Processing failed for an unexpected reason.",
}


def _derive_basename(event):
    """Best-effort extraction of the original file's base name from the event.

    The state machine input is `{"chunks": [...], "s3_bucket": ...}` where each
    chunk key looks like `temp/<basename>/<basename>_chunk_<n>.pdf`. We use that
    to recover `<basename>` so we can both locate the `_errors/` folder and name
    the marker `result/FAILED_<basename>.json`.
    """
    chunks = event.get("chunks") or []
    if chunks and isinstance(chunks, list):
        key = chunks[0].get("s3_key") or chunks[0].get("chunk_key") or ""
        # key = temp/<basename>/<basename>_chunk_1.pdf
        parts = key.split("/")
        if len(parts) >= 2 and parts[0] == "temp":
            return parts[1]
    return None


def _resolve_bucket(event):
    """Find the processing bucket name from the event, with an env fallback."""
    return (
        event.get("s3_bucket")
        or event.get("bucket")
        or os.environ.get("BUCKET_NAME")
    )


def _collect_station_errors(bucket, basename):
    """Read every `temp/<basename>/_errors/*.json` detail file.

    Returns a list of dicts. Tolerates malformed/partial files -- a corrupt
    detail file must never prevent the marker from being written.
    """
    if not bucket or not basename:
        return []

    prefix = f"temp/{basename}/_errors/"
    errors = []
    try:
        paginator = s3_client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if not key.endswith(".json"):
                    continue
                try:
                    body = s3_client.get_object(Bucket=bucket, Key=key)["Body"].read()
                    errors.append(json.loads(body))
                except Exception as e:  # noqa: BLE001 - tolerate any bad file
                    print(f"[failure-handler] Could not read detail file {key}: {e}")
    except Exception as e:  # noqa: BLE001
        print(f"[failure-handler] Could not list {prefix}: {e}")
    return errors


def _parse_sfn_cause(event):
    """Extract a reason from the Step Functions Catch error payload.

    When a station dies before writing a detail file (e.g. the container could
    not start), Step Functions still hands us `Error` and `Cause`. We map that
    to the INFRA category so the user always gets *something* actionable.

    The Catch in app.py nests this under `$.failureInfo` (result_path), so we
    look there first and fall back to the top level for robustness.
    """
    failure_info = event.get("failureInfo") or event
    err = failure_info.get("Error")
    cause_raw = failure_info.get("Cause")
    cause = cause_raw
    if cause_raw:
        try:
            # ECS/Lambda causes are often JSON strings
            parsed = json.loads(cause_raw)
            cause = parsed.get("errorMessage") or parsed.get("Cause") or cause_raw
        except (ValueError, TypeError):
            cause = cause_raw
    if err or cause:
        return {
            "station": "workflow",
            "reason_category": "INFRA",
            "message": cause or err or "Unknown infrastructure failure.",
        }
    return None


def lambda_handler(event, context):
    """Aggregate failure detail and write the user-facing FAILED_ marker.

    `event` is the state-machine execution input augmented by the Catch block
    with `Error`/`Cause`. This function is intentionally exception-proof.
    """
    print(f"[failure-handler] Invoked with event: {json.dumps(event, default=str)}")

    bucket = _resolve_bucket(event)
    basename = _derive_basename(event)

    station_errors = _collect_station_errors(bucket, basename)

    # Fall back to the Step Functions cause if no station detail was written.
    if not station_errors:
        sfn_error = _parse_sfn_cause(event)
        if sfn_error:
            station_errors = [sfn_error]

    # Build the failure detail from whatever station errors exist.
    failed_chunks = []
    categories = []
    for err in station_errors:
        category = err.get("reason_category", "UNKNOWN")
        categories.append(category)
        entry = {
            "station": err.get("station", "unknown"),
            "reason_category": category,
            "message": err.get("message", ""),
        }
        failed_chunks.append(entry)

    # Choose the primary category (first non-UNKNOWN, else UNKNOWN).
    primary_category = next((c for c in categories if c != "UNKNOWN"), None) or (
        categories[0] if categories else "UNKNOWN"
    )
    summary = REASON_SUMMARIES.get(primary_category, REASON_SUMMARIES["UNKNOWN"])

    marker = {
        "status": "FAILED",
        "filename": basename,
        "reason_category": primary_category,
        "summary": summary,
        "failed_chunks": failed_chunks,
        "execution_arn": event.get("executionArn"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Structured CloudWatch line for the dashboard "File status" widget.
    detail_desc = "; ".join(
        f"{c['station']}: {c['message'][:100]}" for c in failed_chunks if c.get("message")
    )
    print(
        f"File: {basename}, Status: FAILED | reason={primary_category}"
        + (f" | {detail_desc}" if detail_desc else "")
    )

    # Write the marker where the frontend already polls. Best-effort: if even
    # this fails, we log loudly but do not raise (raising would re-fail the
    # state machine and produce a confusing double-failure).
    if bucket and basename:
        marker_key = f"result/FAILED_{basename}.json"
        try:
            s3_client.put_object(
                Bucket=bucket,
                Key=marker_key,
                Body=json.dumps(marker, indent=2).encode("utf-8"),
                ContentType="application/json",
            )
            print(f"[failure-handler] Wrote failure marker to s3://{bucket}/{marker_key}")
        except Exception as e:  # noqa: BLE001
            print(f"[failure-handler] CRITICAL: could not write marker {marker_key}: {e}")
    else:
        print(
            "[failure-handler] CRITICAL: missing bucket/basename; "
            f"bucket={bucket} basename={basename}. Marker NOT written."
        )

    return marker
