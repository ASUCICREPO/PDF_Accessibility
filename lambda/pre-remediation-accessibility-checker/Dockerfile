FROM public.ecr.aws/sam/build-python3.12:latest

WORKDIR /tmp/build

COPY main.py .

RUN python -m py_compile main.py \
    && mkdir -p /asset \
    && cp main.py /asset/main.py
