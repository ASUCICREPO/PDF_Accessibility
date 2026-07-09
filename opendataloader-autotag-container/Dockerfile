FROM public.ecr.aws/docker/library/python:3.12-slim

WORKDIR /app

# OpenDataLoader requires Java 11+. Java 17 is safe here.
RUN apt-get update \
    && apt-get install -y --no-install-recommends openjdk-17-jre-headless \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY opendataloader_autotag_processor.py /app/opendataloader_autotag_processor.py

CMD ["python", "./opendataloader_autotag_processor.py"]
