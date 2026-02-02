FROM public.ecr.aws/lambda/python:3.12

# Set environment variable for Lambda Task Root (optional but recommended)
ENV LAMBDA_TASK_ROOT=/asset

# Create /asset directory if it doesn't exist
RUN mkdir -p /asset

# Copy function code to the /asset directory
COPY title_generator.py /asset/

# Copy requirements.txt to /tmp directory
COPY requirements.txt /tmp/

# Upgrade pip to the latest version
RUN pip3 install --upgrade pip

# Install dependencies into /asset
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt -t /asset/

# (Optional) Clean up /tmp to reduce image size
RUN rm -rf /tmp/*

# Set the working directory to /asset
WORKDIR /asset

# Specify the Lambda handler
CMD ["title_generator.lambda_handler"]
