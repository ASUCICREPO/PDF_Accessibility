#!/bin/bash

# Prompt for AWS credentials and Adobe credentials
read -p "Enter your AWS Access Key ID: " AWS_ACCESS_KEY_ID
read -p "Enter your AWS Secret Access Key: " AWS_SECRET_ACCESS_KEY
read -p "Enter your AWS Account ID: " AWS_ACCOUNT_ID
read -p "Enter your AWS Default Region (e.g., us-west-2): " AWS_DEFAULT_REGION
read -p "Enter your Adobe credentials key: " ADOBE_CLIENT_ID
read -p "Enter your Adobe credentials value: " ADOBE_CLIENT_SECRET


TAG=$(date +%s)

JSON_TEMPLATE='{
  "client_credentials": {
    "PDF_SERVICES_CLIENT_ID": "<Your client ID here>",
    "PDF_SERVICES_CLIENT_SECRET": "<Your secret ID here>"
  }
}'

# Replace placeholders and store in a file
echo "$JSON_TEMPLATE" | jq --arg cid "$ADOBE_CLIENT_ID" --arg csec "$ADOBE_CLIENT_SECRET" \
    '.client_credentials.PDF_SERVICES_CLIENT_ID = $cid | 
     .client_credentials.PDF_SERVICES_CLIENT_SECRET = $csec' > client_credentials.json

cat client_credentials.json

if aws secretsmanager create-secret --name /myapp/client_credentials --description "Client credentials for PDF services" --secret-string file://client_credentials.json; then
    echo "Command create-secret succeeded"
else
    aws secretsmanager update-secret --secret-id /myapp/client_credentials --description "Updated client credentials for PDF services" --secret-string file://client_credentials.json
    echo "Command update-secret succeeded"
fi

aws configure set aws_access_key_id "$AWS_ACCESS_KEY_ID"
aws configure set aws_secret_access_key "$AWS_SECRET_ACCESS_KEY"
aws configure set region "$AWS_DEFAULT_REGION"


export AWS_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY
export AWS_ACCOUNT_ID
export AWS_DEFAULT_REGION


# Login to ECR
aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com
# Create Lambda function repositories
for repo in lambda-add-title lambda-accessibility-checker-before lambda-accessibility-checker-after lambda-split-pdf; do
  aws ecr create-repository --repository-name $repo --image-scanning-configuration scanOnPush=true --region $AWS_DEFAULT_REGION
done

# Create ECS task repositories
for repo in ecs-python-task ecs-javascript-task; do
  aws ecr create-repository --repository-name $repo --image-scanning-configuration scanOnPush=true --region $AWS_DEFAULT_REGION
done

# Push Lambda images to ECR
for service in lambda-add-title lambda-accessibility-checker-before lambda-accessibility-checker-after lambda-split-pdf; do 
  docker tag $service:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$service:latest; 
  docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$service:latest; 
done

# Push ECS task images to ECR
for service in ecs-python-task ecs-javascript-task; do 
  docker tag $service:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$service:latest; 
  docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$service:latest; 
done

# Deploy CDK stack using the uploaded images from ECR.
cdk deploy --require-approval never
