# Error Handling & Failure Reporting

This document describes how the PDF-to-PDF remediation pipeline reports
failures so that **no failure is ever silent**, and the contract the frontend
uses to detect and display those failures.

## Background: why this exists

The frontend detects a finished job by **polling the S3 `result/` folder**:

- On success the pipeline writes `result/COMPLIANT_<name>.pdf`.
- Previously, on **any** failure the workflow ended with nothing written to
  `result/`. The UI kept polling indefinitely and the user saw the job "spin"
  for hours with no explanation.

The error-handling layer closes that gap by guaranteeing that every failed job
produces a **failure marker** in the same `result/` folder the frontend already
polls, carrying a human-readable reason.

## The two-layer design

```
Each station (on failure)              Step Functions Catch (catches EVERYTHING)
  writes a detail file       ────────►   routes any error to the failure-handler
  temp/<name>/_errors/                   Lambda, which aggregates the detail
  <station>.json                         files and writes the user-facing marker
  (station, reason)                      result/FAILED_<name>.json
        │
        └──► structured CloudWatch line:
             "File: <name>, Status: FAILED | station=adobe | reason=ADOBE_API | <message>"
```

1. **Station detail files** (`temp/<name>/_errors/*.json`) — each station writes
   rich detail only it knows (the exact reason).
2. **Step Functions `Catch` → failure-handler Lambda** — the exhaustive safety
   net. It fires on *every* failure, including infrastructure failures where a
   container dies before it can write a detail file (image-pull failure, OOM,
   task timeout, IAM error). It aggregates any detail files and always writes the
   marker. If no detail file exists, it derives the reason from the Step
   Functions error `Cause`.

> The **PDF splitter** is a special case: it runs *before* the Step Functions
> execution starts, so the Catch cannot cover it. The splitter therefore writes
> the `result/FAILED_<name>.json` marker directly.

## Frontend contract

When polling for results for an uploaded file `<name>.pdf` (base name `<name>`),
the frontend should check for **both** of these keys:

| Key | Meaning |
|---|---|
| `result/COMPLIANT_<name>.pdf` | Success — the remediated PDF is ready. |
| `result/FAILED_<name>.json` | Failure — stop polling and show the reason. |

### `FAILED_<name>.json` schema

```json
{
  "status": "FAILED",
  "filename": "<name>",
  "reason_category": "ADOBE_API",
  "summary": "Adobe API failed for this document. This document may be too complex for our Adobe API to handle.",
  "failed_chunks": [
    {
      "station": "adobe",
      "reason_category": "ADOBE_API",
      "message": "Adobe API failed for this document..."
    }
  ],
  "execution_arn": "arn:aws:states:...:execution:...",
  "timestamp": "2026-06-08T17:42:11.123456+00:00"
}
```

- `reason_category` and `summary` are safe to show directly to the user.
- `message` is the raw technical detail — useful for support, not necessarily
  for end users.

### Reason categories

| `reason_category` | Meaning |
|---|---|
| `SPLIT` | The document could not be split into pages. |
| `ADOBE_API` | Adobe API failed for this document. Too complex for our Adobe API to handle. |
| `BEDROCK_API` | Amazon Bedrock (alt text / title) failed. |
| `COMPLEXITY` | The document exceeded processing complexity limits. |
| `MERGE` | The processed pages could not be merged. |
| `TITLE` | The title/metadata step failed. |
| `INFRA` | A task failed to run (infrastructure-level failure). |
| `UNKNOWN` | Unexpected failure; see `message`. |

## CloudWatch visibility

Each station emits structured lines for the CloudWatch dashboard:

**Adobe failures:**
```
File: <name>, Status: FAILED | station=adobe | reason=ADOBE_API | Adobe API failed for this document...
```

**Bedrock per-image failures (with exact page number):**
```
File: <name>, Status: FAILED | station=alttext | image=<obj_id> | page=6 | reason=BEDROCK_API | <error_message>
```

**Images tagged decorative due to aspect ratio (with exact page number):**
```
File: <name>, Status: INFO | station=alttext | image=<obj_id> | page=6 | action=decorative | reason=complex_image_aspect_ratio_25:1
```

This lets operators see, per file, exactly which station failed and on which
page — without opening individual log streams.

## Bedrock graceful handling

Images that pass Adobe but cannot be processed by Bedrock are handled as follows:

- **Aspect ratio > 20:1**: Tagged as "Decorative element" (known problematic images
  like separator lines, thin borders). Logged to CloudWatch with exact page number.
- **Individual Bedrock API failure**: The specific image failure is logged with its
  exact page number. If not all images fail, the pipeline continues.
- **All images fail Bedrock**: The container reports total failure and exits. The user
  sees the error on UI.

## Notes for maintainers

- The failure-handler is invoked **only on failure**, so its cost is effectively
  zero. No always-on services or new datastores are introduced.
- Stations report failures on a **best-effort** basis: a failure while writing a
  detail file is logged but never masks the original error.
- The `page_num` column in the SQLite image database (written by the Adobe
  container) enables exact page-level reporting in the alt-text station.
