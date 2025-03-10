FROM python:3.9

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    jq \
    less \
    sudo \
    fuse-overlayfs \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Install AWS CLI v2
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" \
    && unzip awscliv2.zip \
    && ./aws/install \
    && rm -rf awscliv2.zip aws

# Install Node.js and npm
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs

# Install AWS CDK
RUN npm install -g aws-cdk
RUN pip install aws-cdk-lib

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app

# Ensure Docker is installed inside the container
RUN curl -fsSL https://get.docker.com | sh

# Set entrypoint to a startup script
COPY deploy.sh /deploy.sh
RUN chmod +x /deploy.sh
ENTRYPOINT ["/deploy.sh"]
