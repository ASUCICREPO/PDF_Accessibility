#!/bin/bash

set -e

# Parse command line arguments
REGION="us-east-1"
STACK_NAME="Pdf2HtmlStack"
BDA_PROJECT_ARN=""
BUCKET_NAME=""
FORCE_REDEPLOY=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --region)
      REGION="$2"
      shift 2
      ;;
    --stack-name)
      STACK_NAME="$2"
      shift 2
      ;;
    --bda-project-arn)
      BDA_PROJECT_ARN="$2"
      shift 2
      ;;
    --bucket-name)
      BUCKET_NAME="$2"
      shift 2
      ;;
    --force-redeploy)
      FORCE_REDEPLOY=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Check if BDA_PROJECT_ARN is provided
if [ -z "$BDA_PROJECT_ARN" ]; then
  echo "Error: --bda-project-arn is required"
  echo "Usage: ./deploy.sh --bda-project-arn <arn> [--region <region>] [--stack-name <name>] [--bucket-name <name>] [--force-redeploy]"
  exit 1
fi

# Get AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)
echo "Deploying to AWS Account: $ACCOUNT_ID in region $REGION"

# Set default bucket name if not provided
if [ -z "$BUCKET_NAME" ]; then
  BUCKET_NAME="pdf2html-bucket-$ACCOUNT_ID-$REGION"
fi

# Check if stack exists and delete it if force-redeploy is set
if [ "$FORCE_REDEPLOY" = true ]; then
  STACK_EXISTS=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION 2>/dev/null || echo "STACK_NOT_FOUND")
  if [ "$STACK_EXISTS" != "STACK_NOT_FOUND" ]; then
    echo "Force redeploy requested. Deleting existing stack $STACK_NAME..."
    aws cloudformation delete-stack --stack-name $STACK_NAME --region $REGION
    echo "Waiting for stack deletion to complete..."
    aws cloudformation wait stack-delete-complete --stack-name $STACK_NAME --region $REGION
    echo "Stack deleted successfully."
  fi
else
  # Check if stack exists and is in ROLLBACK_COMPLETE state
  STACK_STATUS=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query "Stacks[0].StackStatus" --output text 2>/dev/null || echo "STACK_NOT_FOUND")
  if [ "$STACK_STATUS" == "ROLLBACK_COMPLETE" ]; then
    echo "Stack $STACK_NAME is in ROLLBACK_COMPLETE state. Deleting it before proceeding..."
    aws cloudformation delete-stack --stack-name $STACK_NAME --region $REGION
    echo "Waiting for stack deletion to complete..."
    aws cloudformation wait stack-delete-complete --stack-name $STACK_NAME --region $REGION
    echo "Stack deleted successfully."
  fi
fi

# Create S3 bucket if it doesn't exist
echo "Checking if S3 bucket $BUCKET_NAME exists..."
if ! aws s3api head-bucket --bucket $BUCKET_NAME 2>/dev/null; then
  echo "Creating S3 bucket $BUCKET_NAME..."
  if [ "$REGION" == "us-east-1" ]; then
    aws s3api create-bucket --bucket $BUCKET_NAME --region $REGION
  else
    aws s3api create-bucket --bucket $BUCKET_NAME --region $REGION --create-bucket-configuration LocationConstraint=$REGION
  fi
  
  # Enable versioning on the bucket
  aws s3api put-bucket-versioning --bucket $BUCKET_NAME --versioning-configuration Status=Enabled
  
  # Create required folders
  echo "Creating required folders in the bucket..."
  aws s3api put-object --bucket $BUCKET_NAME --key uploads/
  aws s3api put-object --bucket $BUCKET_NAME --key output/
  aws s3api put-object --bucket $BUCKET_NAME --key remediated/
  
  echo "S3 bucket created successfully."
else
  echo "S3 bucket $BUCKET_NAME already exists."
fi

# Create ECR repository if it doesn't exist
REPO_NAME="pdf2html-lambda"
REPO_URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO_NAME"

echo "Checking if ECR repository $REPO_NAME exists..."
if ! aws ecr describe-repositories --repository-names $REPO_NAME --region $REGION 2>/dev/null; then
  echo "Creating ECR repository $REPO_NAME..."
  aws ecr create-repository --repository-name $REPO_NAME --region $REGION
  echo "ECR repository created successfully."
else
  echo "ECR repository $REPO_NAME already exists."
fi

# Build and push Docker image
echo "Building and pushing Docker image to $REPO_URI..."
docker buildx build --platform linux/amd64 --load -t $REPO_URI:latest .
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $REPO_URI
docker push $REPO_URI:latest
echo "Docker image pushed successfully."

# Bootstrap CDK (if not already done)
echo "Bootstrapping CDK in account $ACCOUNT_ID region $REGION..."
cd cdk
npx cdk bootstrap aws://$ACCOUNT_ID/$REGION

# Deploy CDK stack
echo "Deploying CDK stack..."
npx cdk deploy --app "node bin/app.js" \
  --parameters BdaProjectArn=$BDA_PROJECT_ARN \
  --parameters BucketName=$BUCKET_NAME \
  --require-approval never

# Get Lambda function name from stack outputs
LAMBDA_FUNCTION_NAME=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query "Stacks[0].Outputs[?OutputKey=='LambdaFunctionNameOutput'].OutputValue" --output text)

echo "Deployment complete!"
echo ""
echo "To test the deployment:"
echo "1. Upload a PDF file to the S3 bucket's 'uploads/' prefix:"
echo "   aws s3 cp test.pdf s3://$BUCKET_NAME/uploads/"
echo ""
echo "2. Check for output files:"
echo "   aws s3 ls s3://$BUCKET_NAME/output/"
echo ""
echo "3. Download the processed HTML:"
echo "   aws s3 cp s3://$BUCKET_NAME/output/test.zip ."
echo ""
