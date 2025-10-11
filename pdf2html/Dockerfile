# 1. Start FROM the AWS Lambda Python 3.11 base image
FROM public.ecr.aws/lambda/python:3.11

# 2. Set working directory inside the container
#    Lambda will look here for your handler file by default.
WORKDIR /var/task

# 3. Install AWS CLI for debugging purposes
RUN yum -y update && \
    yum -y install unzip gcc zlib-devel libjpeg-devel && \
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    ./aws/install && \
    rm -rf aws awscliv2.zip && \
    yum clean all

# 4. Copy your handler and requirement specs
#    - lambda_function.py: our S3→/tmp entrypoint
#    - requirements.txt: your pip deps
COPY lambda_function.py    ./ 
COPY requirements.txt      ./

# 5. Copy your package source code
#    The folder name here must match exactly what you see on disk:
#    content_accessibility_utility_on_aws/
COPY content_accessibility_utility_on_aws/ ./content_accessibility_utility_on_aws/

# 6. Install Python dependencies into /var/task
#    This both pulls in third-party libraries AND makes your
#    package importable (since we've copied it under /var/task).
RUN pip3 install --no-cache-dir -r requirements.txt

# 7. Install the package itself to make sure all dependencies are properly resolved
COPY pyproject.toml ./
RUN pip3 install --no-cache-dir -e .

# 8. Tell Lambda which handler to invoke: file "lambda_function", func "lambda_handler"
CMD [ "lambda_function.lambda_handler" ]
