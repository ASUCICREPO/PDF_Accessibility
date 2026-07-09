#!/usr/bin/env python3
"""Apply OCRmyPDF/Tesseract support to the opendataloader-pdf2pdf branch.

Run this from the repository root:
    python3 apply_ocr_patch.py
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

ROOT = Path.cwd()
PATCH_DIR = Path(__file__).resolve().parent


def copy_replacement(rel_path: str) -> None:
    src = PATCH_DIR / rel_path
    dst = ROOT / rel_path
    if not src.exists():
        raise FileNotFoundError(src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    print(f"replaced {rel_path}")


def patch_app_py() -> None:
    path = ROOT / "app.py"
    text = path.read_text(encoding="utf-8")

    if 'name="OCR_MODE"' in text or 'name = "OCR_MODE"' in text:
        print("app.py already contains OCR_MODE container env vars; skipping app.py patch")
        return

    pattern = r'(tasks\.TaskEnvironmentVariable\(\s*name\s*=\s*"AWS_REGION"\s*,\s*value\s*=\s*region\s*\)\s*,)'
    replacement = r'''\1
                                            tasks.TaskEnvironmentVariable(
                                                  name="OCR_MODE",
                                                  value=os.environ.get("OCR_MODE", "auto")
                                              ),
                                            tasks.TaskEnvironmentVariable(
                                                  name="OCR_TEXT_THRESHOLD",
                                                  value=os.environ.get("OCR_TEXT_THRESHOLD", "20")
                                              ),
                                            tasks.TaskEnvironmentVariable(
                                                  name="OCR_LANGUAGE",
                                                  value=os.environ.get("OCR_LANGUAGE", "eng")
                                              ),
                                            tasks.TaskEnvironmentVariable(
                                                  name="OCR_ON_FAILURE",
                                                  value=os.environ.get("OCR_ON_FAILURE", "fail")
                                              ),'''

    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.DOTALL)
    if count != 1:
        raise RuntimeError(
            "Could not patch app.py: failed to find the first AWS_REGION TaskEnvironmentVariable. "
            "Patch it manually by adding OCR_MODE/OCR_TEXT_THRESHOLD/OCR_LANGUAGE/OCR_ON_FAILURE "
            "to the OpenDataLoader/AutoTag ECS container override."
        )

    path.write_text(updated, encoding="utf-8")
    print("patched app.py OpenDataLoader ECS environment variables")


def patch_deploy_sh() -> None:
    path = ROOT / "deploy.sh"
    text = path.read_text(encoding="utf-8")

    if '\\"name\\": \\"OCR_MODE\\"' in text or '"name": "OCR_MODE"' in text:
        print("deploy.sh already contains OCR_MODE CodeBuild env vars; skipping deploy.sh patch")
        return

    target = '{\\"name\\": \\"TAGGING_ENGINE\\", \\"value\\": \\"${TAGGING_ENGINE:-opendataloader}\\"}'
    addition = (
        target
        + ',\n            {\\"name\\": \\"OCR_MODE\\", \\"value\\": \\"${OCR_MODE:-auto}\\"},'
        + '\n            {\\"name\\": \\"OCR_TEXT_THRESHOLD\\", \\"value\\": \\"${OCR_TEXT_THRESHOLD:-20}\\"},'
        + '\n            {\\"name\\": \\"OCR_LANGUAGE\\", \\"value\\": \\"${OCR_LANGUAGE:-eng}\\"},'
        + '\n            {\\"name\\": \\"OCR_ON_FAILURE\\", \\"value\\": \\"${OCR_ON_FAILURE:-fail}\\"}'
    )

    if target not in text:
        raise RuntimeError(
            "Could not patch deploy.sh: TAGGING_ENGINE env var block not found. "
            "Add OCR_MODE/OCR_TEXT_THRESHOLD/OCR_LANGUAGE/OCR_ON_FAILURE to the PDF-to-PDF ENV_VARS block manually."
        )

    text = text.replace(target, addition, 1)
    path.write_text(text, encoding="utf-8")
    print("patched deploy.sh CodeBuild OCR environment variables")


def main() -> None:
    required = [ROOT / "app.py", ROOT / "deploy.sh", ROOT / "opendataloader-autotag-container"]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise SystemExit("Run this script from the PDF_Accessibility repository root. Missing: " + ", ".join(missing))

    copy_replacement("opendataloader-autotag-container/Dockerfile")
    copy_replacement("opendataloader-autotag-container/requirements.txt")
    copy_replacement("opendataloader-autotag-container/opendataloader_autotag_processor.py")
    patch_app_py()
    patch_deploy_sh()
    print("\nOCR patch applied. Recommended defaults: OCR_MODE=auto, OCR_TEXT_THRESHOLD=20, OCR_LANGUAGE=eng.")


if __name__ == "__main__":
    main()
