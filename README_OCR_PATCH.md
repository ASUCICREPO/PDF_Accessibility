# OpenDataLoader OCRmyPDF/Tesseract Patch

This patch is derived for the `opendataloader-pdf2pdf` branch of `oikos99/PDF_Accessibility`.

It adds an OCR preflight step inside `opendataloader-autotag-container` before OpenDataLoader runs.

## New behavior

Default:

```text
OCR_MODE=auto
```

Flow:

```text
PDF chunk
→ PyMuPDF text-layer preflight
→ if every page has enough extractable text, skip OCR
→ if one or more pages are low-text/image-only, run OCRmyPDF/Tesseract
→ feed OCRed PDF into OpenDataLoader
→ upload tagged PDF/artifacts using the existing S3 contract
```

## Supported environment variables

```text
OCR_MODE=auto|always|off|redo|force
OCR_TEXT_THRESHOLD=20
OCR_LANGUAGE=eng
OCR_ON_FAILURE=fail|fallback
```

Recommended first test:

```bash
export PDF_STACK_NAME="PDFAccessibilityOdlDev"
export TAGGING_ENGINE="opendataloader"
export OCR_MODE="auto"
export OCR_TEXT_THRESHOLD="20"
export OCR_LANGUAGE="eng"
export OCR_ON_FAILURE="fail"
./deploy.sh
```

Choose PDF-to-PDF, then backend-only.

## Install/apply

From the repository root:

```bash
unzip opendataloader_ocr_patch.zip
python3 opendataloader_ocr_patch/apply_ocr_patch.py
python3 -m py_compile opendataloader-autotag-container/opendataloader_autotag_processor.py

git diff
git add app.py deploy.sh opendataloader-autotag-container/Dockerfile opendataloader-autotag-container/requirements.txt opendataloader-autotag-container/opendataloader_autotag_processor.py
git commit -m "Add OCRmyPDF preflight before OpenDataLoader"
git push origin opendataloader-pdf2pdf
```

Then pull/deploy from CloudShell.

## Notes

- `OCR_MODE=auto` avoids wasting compute on born-digital/text PDFs.
- `OCR_MODE=always` runs OCRmyPDF with `--skip-text`, so OCRmyPDF still skips pages that already contain text.
- `OCR_MODE=redo` is for PDFs with a bad existing OCR layer.
- `OCR_MODE=force` is advanced and can rasterize/reprocess existing content.
- This still does not replace the Adobe figure-ID alt-text mapping or real PDF/UA validation.
