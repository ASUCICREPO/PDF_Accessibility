FROM public.ecr.aws/lambda/python:3.12

COPY main.py /asset/
COPY requirements.txt /tmp/
RUN pip3 install -r /tmp/requirements.txt -t /asset