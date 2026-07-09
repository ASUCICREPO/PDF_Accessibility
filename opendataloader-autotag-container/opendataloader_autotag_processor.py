"""
OpenDataLoader replacement for adobe-autotag-container, with optional OCRmyPDF/Tesseract preflight.

This container preserves the existing ASU/AWS PDF-to-PDF S3 contract:

Input env vars:
    S3_BUCKET_NAME = processing bucket
    S3_FILE_KEY    = temp/{file_basename}/{chunk_filename}.pdf
    S3_CHUNK_KEY   = optional; kept for compatibility

Outputs expected by the existing downstream alt-text and merger steps:
    temp/{file_basename}/output_autotag/COMPLIANT_{chunk_filename}
    temp/{file_basename}/output_autotag/{chunk_filename}_temp_images_data.db

OpenDataLoader artifacts are uploaded under:
    temp/{file_basename}/opendataloader/{chunk_filename}/...

OCR behavior:
    OCR_MODE=auto   default; run OCRmyPDF only if one or more pages have little/no text.
    OCR_MODE=always always run OCRmyPDF --skip-text.
    OCR_MODE=off    never OCR.
    OCR_MODE=redo   run OCRmyPDF --redo-ocr; useful for bad existing OCR.
    OCR_MODE=force  run OCRmyPDF --force-ocr; advanced/riskier.

Additional env vars:
    OCR_TEXT_THRESHOLD=20   page is considered low-text below this many extractable chars.
    OCR_LANGUAGE=eng        Tesseract language code.
    OCR_ON_FAILURE=fail     fail or fallback. fallback uses original PDF if OCRmyPDF fails.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

import boto3
import fitz  # PyMuPDF
from pypdf import PdfReader, PdfWriter

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

s3 = boto3.client("s3")


def parse_s3_key(s3_file_key: str) -> tuple[str, str]:
    """Return (file_basename, chunk_filename) from temp/{file}/{chunk}.pdf."""
    parts = s3_file_key.split("/")
    if len(parts) >= 3 and parts[0] == "temp":
        return parts[1], parts[-1]

    # Defensive fallback for direct chunk file names.
    chunk_filename = Path(s3_file_key).name
    file_basename = chunk_filename.rsplit("_chunk_", 1)[0]
    return file_basename, chunk_filename


def download_chunk(bucket: str, key: str, local_path: Path) -> None:
    logger.info("Downloading s3://%s/%s to %s", bucket, key, local_path)
    s3.download_file(bucket, key, str(local_path))


def upload_file(local_path: Path, bucket: str, key: str, content_type: str | None = None) -> None:
    extra_args = {"ContentType": content_type} if content_type else None
    logger.info("Uploading %s to s3://%s/%s", local_path, bucket, key)
    if extra_args:
        s3.upload_file(str(local_path), bucket, key, ExtraArgs=extra_args)
    else:
        s3.upload_file(str(local_path), bucket, key)


def env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        logger.warning("Invalid %s=%r; using default %s", name, value, default)
        return default


def analyze_text_layer(pdf_path: Path, threshold: int) -> dict[str, Any]:
    """Return simple page-level extractable-text metrics for OCR preflight."""
    metrics: dict[str, Any] = {
        "page_count": 0,
        "page_text_char_counts": [],
        "low_text_pages": [],
        "threshold": threshold,
        "has_extractable_text": False,
        "needs_ocr": False,
    }

    try:
        doc = fitz.open(str(pdf_path))
        metrics["page_count"] = len(doc)
        for index, page in enumerate(doc, start=1):
            text = page.get_text("text") or ""
            count = len(text.strip())
            metrics["page_text_char_counts"].append(count)
            if count < threshold:
                metrics["low_text_pages"].append(index)
        doc.close()
    except Exception as exc:
        logger.warning("Could not analyze text layer for %s: %s", pdf_path, exc)
        metrics["analysis_error"] = str(exc)
        metrics["needs_ocr"] = True
        return metrics

    counts = metrics["page_text_char_counts"]
    metrics["has_extractable_text"] = any(count > 0 for count in counts)
    metrics["needs_ocr"] = bool(metrics["low_text_pages"])
    return metrics


def run_ocrmypdf(input_pdf: Path, output_pdf: Path, mode: str, language: str) -> tuple[list[str], subprocess.CompletedProcess[str]]:
    """Run OCRmyPDF and return the command plus CompletedProcess."""
    cmd = [
        "ocrmypdf",
        "--jobs",
        "1",
        "--output-type",
        "pdf",
        "--rotate-pages",
        "--deskew",
        "--optimize",
        "0",
        "--language",
        language,
    ]

    if mode in ("auto", "always"):
        cmd.append("--skip-text")
    elif mode == "redo":
        cmd.append("--redo-ocr")
    elif mode == "force":
        cmd.append("--force-ocr")
    else:
        raise ValueError(f"Unsupported OCR mode for OCRmyPDF execution: {mode}")

    cmd.extend([str(input_pdf), str(output_pdf)])
    logger.info("Running OCRmyPDF: %s", " ".join(cmd))
    completed = subprocess.run(cmd, text=True, capture_output=True, check=False)
    if completed.stdout:
        logger.info("OCRmyPDF stdout:\n%s", completed.stdout)
    if completed.stderr:
        logger.info("OCRmyPDF stderr:\n%s", completed.stderr)
    return cmd, completed


def choose_pdf_for_tagging(downloaded_pdf: Path, work_dir: Path, output_dir: Path) -> Path:
    """Optionally OCR the chunk before OpenDataLoader tagging."""
    output_dir.mkdir(parents=True, exist_ok=True)

    mode = os.environ.get("OCR_MODE", "auto").strip().lower()
    threshold = env_int("OCR_TEXT_THRESHOLD", 20)
    language = os.environ.get("OCR_LANGUAGE", "eng").strip() or "eng"
    on_failure = os.environ.get("OCR_ON_FAILURE", "fail").strip().lower()

    allowed_modes = {"auto", "always", "off", "redo", "force"}
    if mode not in allowed_modes:
        raise ValueError(f"Unsupported OCR_MODE={mode!r}; expected one of {sorted(allowed_modes)}")
    if on_failure not in {"fail", "fallback"}:
        raise ValueError("OCR_ON_FAILURE must be 'fail' or 'fallback'")

    metrics = analyze_text_layer(downloaded_pdf, threshold)
    report: dict[str, Any] = {
        "ocr_mode": mode,
        "ocr_language": language,
        "ocr_text_threshold": threshold,
        "ocr_on_failure": on_failure,
        "preflight": metrics,
        "ocr_attempted": False,
        "ocr_succeeded": False,
        "ocr_output_used": False,
        "selected_input_for_opendataloader": str(downloaded_pdf),
    }

    if mode == "off":
        report["decision"] = "OCR disabled by OCR_MODE=off."
        (output_dir / "ocr_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        logger.info(report["decision"])
        return downloaded_pdf

    should_run = False
    if mode == "auto":
        should_run = bool(metrics.get("needs_ocr"))
        report["decision"] = (
            "Running OCR because one or more pages are below the text threshold."
            if should_run
            else "Skipping OCR because all pages have enough extractable text."
        )
    elif mode in {"always", "redo", "force"}:
        should_run = True
        report["decision"] = f"Running OCR because OCR_MODE={mode}."

    if not should_run:
        (output_dir / "ocr_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        logger.info(report["decision"])
        return downloaded_pdf

    ocr_pdf = work_dir / f"ocr_{downloaded_pdf.name}"
    report["ocr_attempted"] = True
    cmd, completed = run_ocrmypdf(downloaded_pdf, ocr_pdf, mode, language)
    report["ocr_command"] = cmd
    report["ocr_returncode"] = completed.returncode

    if completed.returncode == 0 and ocr_pdf.exists():
        report["ocr_succeeded"] = True
        report["ocr_output_used"] = True
        report["selected_input_for_opendataloader"] = str(ocr_pdf)
        report["post_ocr_preflight"] = analyze_text_layer(ocr_pdf, threshold)
        (output_dir / "ocr_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        logger.info("OCR succeeded; using %s for OpenDataLoader", ocr_pdf)
        return ocr_pdf

    report["ocr_stdout_tail"] = (completed.stdout or "")[-4000:]
    report["ocr_stderr_tail"] = (completed.stderr or "")[-4000:]

    if on_failure == "fallback":
        report["decision_after_failure"] = "OCR failed; falling back to original PDF."
        (output_dir / "ocr_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        logger.warning("OCR failed with code %s; falling back to original PDF", completed.returncode)
        return downloaded_pdf

    (output_dir / "ocr_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    raise RuntimeError(f"OCRmyPDF failed with exit code {completed.returncode}")


def add_viewer_preferences(input_pdf: Path, output_pdf: Path) -> None:
    """Set DisplayDocTitle without relying on Adobe."""
    reader = PdfReader(str(input_pdf))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.create_viewer_preferences()
    writer.viewer_preferences.display_doctitle = True
    with output_pdf.open("wb") as f:
        writer.write(f)


def run_opendataloader(input_pdf: Path, output_dir: Path, image_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    image_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "opendataloader-pdf",
        "--format",
        "json,tagged-pdf",
        "--output-dir",
        str(output_dir),
        "--image-output",
        "external",
        "--image-format",
        "png",
        "--image-dir",
        str(image_dir),
        str(input_pdf),
    ]
    logger.info("Running OpenDataLoader: %s", " ".join(cmd))
    completed = subprocess.run(cmd, text=True, capture_output=True, check=False)
    if completed.stdout:
        logger.info("OpenDataLoader stdout:\n%s", completed.stdout)
    if completed.stderr:
        logger.info("OpenDataLoader stderr:\n%s", completed.stderr)
    if completed.returncode != 0:
        raise RuntimeError(f"OpenDataLoader failed with exit code {completed.returncode}")


def newest_file(paths: Iterable[Path]) -> Path | None:
    files = [p for p in paths if p.is_file()]
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


def find_tagged_pdf(output_dir: Path, original_pdf_name: str) -> Path:
    pdfs = [p for p in output_dir.rglob("*.pdf") if p.name != original_pdf_name]
    tagged_candidates = [p for p in pdfs if "tag" in p.name.lower()]
    chosen = newest_file(tagged_candidates) or newest_file(pdfs)
    if not chosen:
        raise FileNotFoundError(f"OpenDataLoader did not produce a tagged PDF in {output_dir}")
    logger.info("Selected OpenDataLoader tagged PDF: %s", chosen)
    return chosen


def find_json_output(output_dir: Path) -> Path | None:
    return newest_file(output_dir.rglob("*.json"))


def walk_json(node: Any) -> Iterable[dict[str, Any]]:
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from walk_json(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk_json(value)


def get_text_value(element: dict[str, Any]) -> str | None:
    for key in ("text", "Text", "content", "Content", "value", "Value"):
        value = element.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def get_page_number(element: dict[str, Any]) -> int | None:
    for key in ("page", "Page", "page_number", "page number", "pageNumber"):
        value = element.get(key)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    return None


def get_element_type(element: dict[str, Any]) -> str:
    for key in ("type", "Type", "label", "Label", "category", "Category"):
        value = element.get(key)
        if isinstance(value, str):
            return value.lower()
    path = element.get("Path")
    if isinstance(path, str):
        return path.lower()
    return ""


def add_toc_from_json(pdf_path: Path, json_path: Path | None) -> None:
    if not json_path or not json_path.exists():
        logger.info("No OpenDataLoader JSON found; skipping TOC generation")
        return

    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Could not read OpenDataLoader JSON for TOC: %s", exc)
        return

    toc: list[list[Any]] = []
    for element in walk_json(data):
        element_type = get_element_type(element)
        if (
            "heading" not in element_type
            and "title" not in element_type
            and "h1" not in element_type
            and "h2" not in element_type
        ):
            continue

        text = get_text_value(element)
        page_number = get_page_number(element)
        if not text or page_number is None:
            continue

        # PyMuPDF TOC pages are 1-based. If OpenDataLoader gives 0-based, fix it.
        page_for_toc = page_number + 1 if page_number == 0 else page_number
        level = 1
        if "h2" in element_type or "heading2" in element_type:
            level = 2
        elif "h3" in element_type or "heading3" in element_type:
            level = 3
        elif "h4" in element_type or "heading4" in element_type:
            level = 4
        toc.append([level, text[:250], page_for_toc])

    if not toc:
        logger.info("No heading-like elements found in OpenDataLoader JSON; skipping TOC")
        return

    doc = fitz.open(str(pdf_path))
    max_page = len(doc)
    safe_toc = [entry for entry in toc if 1 <= entry[2] <= max_page]
    if safe_toc:
        logger.info("Adding %d TOC entries", len(safe_toc))
        doc.set_toc(safe_toc)
        doc.saveIncr()
    doc.close()


def create_empty_image_db(db_path: Path) -> None:
    """Create the DB schema expected by the existing alt-text container."""
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS image_data (
            objid TEXT,
            img_path TEXT,
            prev TEXT,
            current TEXT,
            next TEXT,
            context TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def upload_opendataloader_artifacts(bucket: str, file_basename: str, chunk_filename: str, output_dir: Path, image_dir: Path) -> None:
    artifact_prefix = f"temp/{file_basename}/opendataloader/{chunk_filename}"

    for artifact in output_dir.rglob("*"):
        if artifact.is_file():
            rel = artifact.relative_to(output_dir)
            upload_file(artifact, bucket, f"{artifact_prefix}/{rel.as_posix()}")

    if image_dir.exists():
        for image in image_dir.rglob("*"):
            if image.is_file():
                rel = image.relative_to(image_dir)
                upload_file(image, bucket, f"{artifact_prefix}/images/{rel.as_posix()}")


def main() -> None:
    bucket_name = os.environ.get("S3_BUCKET_NAME")
    s3_file_key = os.environ.get("S3_FILE_KEY") or os.environ.get("S3_CHUNK_KEY")

    if not bucket_name or not s3_file_key:
        logger.error("S3_BUCKET_NAME and S3_FILE_KEY/S3_CHUNK_KEY are required")
        sys.exit(1)

    file_basename, chunk_filename = parse_s3_key(s3_file_key)
    logger.info("File: %s, Status: Started OpenDataLoader tagging", file_basename)

    work_dir = Path("/tmp/odl-work")
    input_dir = work_dir / "input"
    output_dir = work_dir / "output"
    image_dir = work_dir / "images"
    input_dir.mkdir(parents=True, exist_ok=True)

    downloaded_pdf = input_dir / chunk_filename
    viewer_pdf = input_dir / f"viewer_{chunk_filename}"
    compliant_pdf = work_dir / f"COMPLIANT_{chunk_filename}"
    db_path = work_dir / f"{chunk_filename}_temp_images_data.db"

    try:
        download_chunk(bucket_name, s3_file_key, downloaded_pdf)
        tagging_input_pdf = choose_pdf_for_tagging(downloaded_pdf, work_dir, output_dir)
        add_viewer_preferences(tagging_input_pdf, viewer_pdf)
        run_opendataloader(viewer_pdf, output_dir, image_dir)

        tagged_pdf = find_tagged_pdf(output_dir, viewer_pdf.name)
        shutil.copyfile(tagged_pdf, compliant_pdf)

        json_output = find_json_output(output_dir)
        add_toc_from_json(compliant_pdf, json_output)

        create_empty_image_db(db_path)

        upload_file(
            compliant_pdf,
            bucket_name,
            f"temp/{file_basename}/output_autotag/COMPLIANT_{chunk_filename}",
            "application/pdf",
        )
        upload_file(
            db_path,
            bucket_name,
            f"temp/{file_basename}/output_autotag/{chunk_filename}_temp_images_data.db",
        )
        upload_opendataloader_artifacts(bucket_name, file_basename, chunk_filename, output_dir, image_dir)

        logger.info("File: %s, Status: Succeeded in First ECS task", file_basename)
    except Exception as exc:
        logger.exception("Filename: %s | OpenDataLoader tagging failed: %s", chunk_filename, exc)
        logger.error("File: %s, Status: Failed in First ECS task", file_basename)
        sys.exit(1)


if __name__ == "__main__":
    main()
