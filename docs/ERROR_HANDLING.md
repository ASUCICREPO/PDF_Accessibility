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
polls, carrying a human-readable reason and the location (chunk / page range).

## The two-layer design

```
Each station (on failure)              Step Functions Catch (catches EVERYTHING)
  writes a detail file       ───────►    routes any error to the failure-handler
  temp/<name>/_errors/                    Lambda, which aggregates the detail
  <station>.json                          files and writes the user-facing marker
  (station, reason, chunk, pages)         result/FAILED_<name>.json
        │
        └──► structured CloudWatch line:
             "File: <name>, Status: FAILED | station=adobe | reason=ADOBE_API | chunk=8 | pages=1401-1600"
```

1. **Station detail files** (`temp/<name>/_errors/*.json`) — each station writes
   rich detail only it knows (the exact reason and which chunk/pages).
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
  "summary": "The Adobe PDF Services API (auto-tagging/extraction) failed.",
  "failed_chunks": [
    {
      "station": "adobe",
      "reason_category": "ADOBE_API",
      "message": "Adobe API error: ...",
      "chunk_index": 8,
      "page_start": 1401,
      "page_end": 1600
    }
  ],
  "execution_arn": "arn:aws:states:...:execution:...",
  "timestamp": "2026-06-08T17:42:11.123456+00:00"
}
```

- `reason_category` and `summary` are safe to show directly to the user.
- `failed_chunks[].page_start`/`page_end` tell the user **which pages** failed
  (e.g. "Processing failed on pages 1401–1600"). These fields are absent for
  failures that aren't chunk-specific (e.g. split or title failures).
- `message` is the raw technical detail — useful for support, not necessarily
  for end users.

### Reason categories

| `reason_category` | Meaning |
|---|---|
| `SPLIT` | The document could not be split into pages. |
| `ADOBE_API` | Adobe PDF Services (auto-tag/extract) failed. |
| `BEDROCK_API` | Amazon Bedrock (alt text / title) failed. |
| `COMPLEXITY` | The document exceeded processing complexity limits. |
| `MERGE` | The processed pages could not be merged. |
| `TITLE` | The title/metadata step failed. |
| `INFRA` | A task failed to run (infrastructure-level failure). |
| `UNKNOWN` | Unexpected failure; see `message`. |

## CloudWatch visibility

Every station emits a structured failure line that the dashboard "File status"
widget parses:

```
File: <name>, Status: FAILED | station=<station> | reason=<category> | chunk=<n> | pages=<start>-<end> | <message>
```

This lets operators see, per file, exactly which station failed and on which
pages — without opening individual log streams.

## Notes for maintainers

- `PAGES_PER_CHUNK` (default `200`) must stay in sync between the PDF splitter,
  the stations, and the failure-handler so reported page ranges are accurate. It
  is overridable via the `PAGES_PER_CHUNK` environment variable.
- The failure-handler is invoked **only on failure**, so its cost is effectively
  zero. No always-on services or new datastores are introduced.
- Stations report failures on a **best-effort** basis: a failure while writing a
  detail file is logged but never masks the original error.
