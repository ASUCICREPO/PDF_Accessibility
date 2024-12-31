FROM public.ecr.aws/lambda/python:3.10.2024.06.14.14

COPY main.py /asset/
COPY requirements.txt /tmp/
RUN pip3 install -r /tmp/requirements.txt -t /asset