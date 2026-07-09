FROM public.ecr.aws/docker/library/python:3.12-slim

WORKDIR /app

# OpenDataLoader requires Java 11+. OCRmyPDF requires Tesseract plus PDF tools.
# Java 21 is available in the current Debian base image used by python:3.12-slim.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        openjdk-21-jre \
        tesseract-ocr \
        tesseract-ocr-eng \
        ghostscript \
        qpdf \
        unpaper \
        pngquant \
        jbig2dec \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY opendataloader_autotag_processor.py /app/opendataloader_autotag_processor.py

CMD ["python", "./opendataloader_autotag_processor.py"]
