# OpenDataLoader migration notes

## Branch goal

Replace Adobe PDF Services API from the PDF-to-PDF path without changing the frontend UI contract.

This first branch is intentionally conservative:

- Keeps the S3 layout expected by the current splitter, alt-text generator, merger, and title generator.
- Replaces Adobe AutoTag/Extract with an OpenDataLoader tagging container.
- Replaces Adobe pre/post accessibility checker Lambdas with no-Adobe placeholder reports.
- Does not yet map OpenDataLoader figure detections back to PDF `/Figure` structure object numbers.

## Files to add or replace

Add:

```text
opendataloader-autotag-container/
  Dockerfile
  requirements.txt
  opendataloader_autotag_processor.py
```

Replace the contents of:

```text
lambda/pre-remediation-accessibility-checker/
  Dockerfile
  main.py

lambda/post-remediation-accessibility-checker/
  Dockerfile
  main.py
```

## Minimal `app.py` change

Replace the existing Docker image asset for Adobe AutoTag:

```python
adobe_autotag_image_asset = ecr_assets.DockerImageAsset(
    self,
    "AdobeAutotagImage",
    directory="adobe-autotag-container",
    platform=ecr_assets.Platform.LINUX_AMD64,
    cache_to=ecr_assets.DockerCacheOption(type="inline"),
    outputs=["type=image,compression=zstd,compression-level=3,force-compression=true"],
)
```

with:

```python
tagging_engine = (self.node.try_get_context("TAGGING_ENGINE") or "opendataloader").lower()
autotag_container_dir = "opendataloader-autotag-container" if tagging_engine == "opendataloader" else "adobe-autotag-container"

adobe_autotag_image_asset = ecr_assets.DockerImageAsset(
    self,
    "AdobeAutotagImage",
    directory=autotag_container_dir,
    platform=ecr_assets.Platform.LINUX_AMD64,
    cache_to=ecr_assets.DockerCacheOption(type="inline"),
    outputs=["type=image,compression=zstd,compression-level=3,force-compression=true"],
)
```

This intentionally keeps the variable name and Step Functions task name for now so the blast radius stays small.

## Deploy

```bash
git checkout -b feature/opendataloader-pdf2pdf

# copy in the files from this patch bundle

cdk deploy -c TAGGING_ENGINE=opendataloader
```

## What should still work

The existing pipeline should still produce:

```text
result/COMPLIANT_<original-file-name>.pdf
```

because the OpenDataLoader container writes:

```text
temp/<base>/output_autotag/COMPLIANT_<chunk>.pdf
temp/<base>/output_autotag/<chunk>.pdf_temp_images_data.db
```

and the existing alt-text stage should then upload:

```text
temp/<base>/FINAL_<chunk>.pdf
```

which the existing merger expects.

## Known limitation in this branch

This branch creates an empty image DB by default. That is deliberate. The current Bedrock alt-text container maps alt text to `/Figure` structure elements by Adobe object number. OpenDataLoader does not produce the same Adobe XLSX object IDs, so image alt text mapping needs a second change.

Phase 2 should replace the current Adobe-object-number mapping with either:

1. OpenDataLoader figure element order + PDF `/Figure` structure order, or
2. a direct hook into OpenDataLoader's tag writer before tagged-PDF export, or
3. a postprocessor that maps by page/bounding-box proximity.
