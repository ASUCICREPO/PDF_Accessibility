#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Default values
REGION="us-east-1"
STACK_NAME="Pdf2HtmlStack"
PROJECT_NAME="pdf2html-bda-project-$(date +%Y%m%d-%H%M%S)"

print_status "🚀 PDF2HTML Accessibility Utility - One-Click Deployment"
print_status "=================================================="

# Verify AWS credentials
print_status "Verifying AWS credentials..."
ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text 2>/dev/null || {
    print_error "Failed to get AWS account ID. Please ensure you're in AWS CloudShell or have AWS CLI configured."
    exit 1
})

print_success "✅ AWS credentials verified. Account: $ACCOUNT_ID, Region: $REGION"

# Set bucket name
BUCKET_NAME="pdf2html-bucket-$ACCOUNT_ID-$REGION"

# Create BDA project
print_status "Creating Bedrock Data Automation project..."
BDA_RESPONSE=$(aws bedrock-data-automation create-data-automation-project \
    --project-name "$PROJECT_NAME" \
    --standard-output-configuration '{
        "document": {
            "extraction": {
                "granularity": {
                    "types": ["DOCUMENT", "PAGE", "ELEMENT"]
                },
                "boundingBox": {
                    "state": "ENABLED"
                }
            },
            "generativeField": {
                "state": "DISABLED"
            },
            "outputFormat": {
                "textFormat": {
                    "types": ["HTML"]
                },
                "additionalFileFormat": {
                    "state": "ENABLED"
                }
            }
        }
    }' \
    --region $REGION 2>/dev/null || {
    print_error "Failed to create BDA project. Please ensure you have bedrock-data-automation permissions."
    exit 1
})

BDA_PROJECT_ARN=$(echo $BDA_RESPONSE | jq -r '.projectArn')
print_success "✅ BDA project created: $PROJECT_NAME"

# Create CodeBuild deployment
print_status "Setting up CodeBuild for deployment..."

# Create buildspec for CloudShell optimized deployment
cat > buildspec.yml << 'EOF'
version: 0.2

phases:
  install:
    runtime-versions:
      nodejs: 18
      python: 3.11
    commands:
      - echo "Installing dependencies..."
      - npm install -g aws-cdk@latest
      - pip install --upgrade pip
      
  pre_build:
    commands:
      - echo "Pre-build phase started"
      - aws --version
      - docker --version
      - cdk --version
      
  build:
    commands:
      - echo "Build phase started"
      
      # Create S3 bucket
      - |
        if ! aws s3api head-bucket --bucket $BUCKET_NAME 2>/dev/null; then
          echo "Creating S3 bucket $BUCKET_NAME..."
          if [ "$REGION" == "us-east-1" ]; then
            aws s3api create-bucket --bucket $BUCKET_NAME --region $REGION
          else
            aws s3api create-bucket --bucket $BUCKET_NAME --region $REGION --create-bucket-configuration LocationConstraint=$REGION
          fi
          aws s3api put-bucket-versioning --bucket $BUCKET_NAME --versioning-configuration Status=Enabled
          aws s3api put-object --bucket $BUCKET_NAME --key uploads/
          aws s3api put-object --bucket $BUCKET_NAME --key output/
          aws s3api put-object --bucket $BUCKET_NAME --key remediated/
        fi
      
      # Create ECR repository
      - |
        REPO_NAME="pdf2html-lambda"
        if ! aws ecr describe-repositories --repository-names $REPO_NAME --region $REGION 2>/dev/null; then
          aws ecr create-repository --repository-name $REPO_NAME --region $REGION
        fi
      
      # Build and push Docker image
      - echo "Building Docker image..."
      - REPO_URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/pdf2html-lambda"
      - aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $REPO_URI
      - docker build --platform linux/amd64 -t $REPO_URI:latest .
      - docker push $REPO_URI:latest
      
      # Deploy with CDK
      - cd cdk
      - npm install
      - npx cdk bootstrap aws://$ACCOUNT_ID/$REGION
      - npx cdk deploy --app "node bin/app.js" --parameters BdaProjectArn=$BDA_PROJECT_ARN --parameters BucketName=$BUCKET_NAME --require-approval never
      
  post_build:
    commands:
      - echo "Deployment completed successfully!"
EOF

# Create temporary CodeBuild project
CODEBUILD_PROJECT="pdf2html-deploy-$(date +%s)"
CODEBUILD_ROLE="pdf2html-codebuild-role-$(date +%s)"

print_status "Creating IAM role for CodeBuild..."

# Create trust policy
cat > trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "codebuild.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create IAM role
aws iam create-role \
    --role-name $CODEBUILD_ROLE \
    --assume-role-policy-document file://trust-policy.json >/dev/null

# Attach comprehensive policy
aws iam attach-role-policy \
    --role-name $CODEBUILD_ROLE \
    --policy-arn arn:aws:iam::aws:policy/PowerUserAccess

# Wait for role propagation
sleep 15

# Create source bundle
print_status "Preparing source code..."
TEMP_BUCKET="temp-codebuild-$ACCOUNT_ID-$(date +%s)"

if [ "$REGION" == "us-east-1" ]; then
    aws s3api create-bucket --bucket $TEMP_BUCKET >/dev/null
else
    aws s3api create-bucket --bucket $TEMP_BUCKET --region $REGION --create-bucket-configuration LocationConstraint=$REGION >/dev/null
fi

# Create source archive excluding unnecessary files
tar --exclude='.git' --exclude='node_modules' --exclude='.DS_Store' --exclude='*.zip' -czf source.tar.gz .
aws s3 cp source.tar.gz s3://$TEMP_BUCKET/

# Create CodeBuild project
print_status "Creating CodeBuild project..."
cat > project.json << EOF
{
  "name": "$CODEBUILD_PROJECT",
  "source": {
    "type": "S3",
    "location": "$TEMP_BUCKET/source.tar.gz"
  },
  "artifacts": {
    "type": "NO_ARTIFACTS"
  },
  "environment": {
    "type": "LINUX_CONTAINER",
    "image": "aws/codebuild/amazonlinux2-x86_64-standard:5.0",
    "computeType": "BUILD_GENERAL1_LARGE",
    "privilegedMode": true,
    "environmentVariables": [
      {
        "name": "ACCOUNT_ID",
        "value": "$ACCOUNT_ID"
      },
      {
        "name": "REGION",
        "value": "$REGION"
      },
      {
        "name": "BUCKET_NAME",
        "value": "$BUCKET_NAME"
      },
      {
        "name": "BDA_PROJECT_ARN",
        "value": "$BDA_PROJECT_ARN"
      }
    ]
  },
  "serviceRole": "arn:aws:iam::$ACCOUNT_ID:role/$CODEBUILD_ROLE"
}
EOF

aws codebuild create-project --cli-input-json file://project.json >/dev/null

# Start build
print_status "Starting deployment build..."
BUILD_ID=$(aws codebuild start-build --project-name $CODEBUILD_PROJECT --query 'build.id' --output text)

print_status "Build ID: $BUILD_ID"
print_status "Monitoring deployment progress..."

# Monitor build with progress indicator
DOTS=0
while true; do
    BUILD_STATUS=$(aws codebuild batch-get-builds --ids $BUILD_ID --query 'builds[0].buildStatus' --output text)
    
    case $BUILD_STATUS in
        "SUCCEEDED")
            echo ""
            print_success "🎉 Deployment completed successfully!"
            break
            ;;
        "FAILED"|"FAULT"|"STOPPED"|"TIMED_OUT")
            echo ""
            print_error "❌ Deployment failed with status: $BUILD_STATUS"
            
            # Get build logs
            LOG_GROUP="/aws/codebuild/$CODEBUILD_PROJECT"
            print_error "Build logs:"
            aws logs describe-log-streams --log-group-name $LOG_GROUP --order-by LastEventTime --descending --max-items 1 --query 'logStreams[0].logStreamName' --output text | xargs -I {} aws logs get-log-events --log-group-name $LOG_GROUP --log-stream-name {} --query 'events[*].message' --output text | tail -20
            exit 1
            ;;
        "IN_PROGRESS")
            printf "."
            DOTS=$((DOTS + 1))
            if [ $DOTS -eq 60 ]; then
                echo ""
                print_status "Still deploying... This may take several minutes."
                DOTS=0
            fi
            sleep 5
            ;;
        *)
            printf "."
            sleep 3
            ;;
    esac
done

# Cleanup temporary resources
print_status "Cleaning up temporary resources..."
aws s3 rm s3://$TEMP_BUCKET/source.tar.gz >/dev/null 2>&1 || true
aws s3api delete-bucket --bucket $TEMP_BUCKET >/dev/null 2>&1 || true
aws codebuild delete-project --name $CODEBUILD_PROJECT >/dev/null 2>&1 || true
aws iam detach-role-policy --role-name $CODEBUILD_ROLE --policy-arn arn:aws:iam::aws:policy/PowerUserAccess >/dev/null 2>&1 || true
aws iam delete-role --role-name $CODEBUILD_ROLE >/dev/null 2>&1 || true
rm -f buildspec.yml trust-policy.json project.json source.tar.gz

# Get deployment info
LAMBDA_FUNCTION=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query "Stacks[0].Outputs[?OutputKey=='LambdaFunctionNameOutput'].OutputValue" --output text 2>/dev/null || echo "Not found")

echo ""
print_success "🎊 PDF2HTML Accessibility Utility Deployed Successfully!"
echo ""
print_status "📋 Deployment Summary:"
print_status "   AWS Account: $ACCOUNT_ID"
print_status "   Region: $REGION"
print_status "   S3 Bucket: $BUCKET_NAME"
print_status "   Lambda Function: $LAMBDA_FUNCTION"
print_status "   BDA Project: $PROJECT_NAME"
echo ""
print_status "🧪 Test Your Deployment:"
print_status "1. Upload a PDF file:"
print_status "   aws s3 cp your-file.pdf s3://$BUCKET_NAME/uploads/"
echo ""
print_status "2. Check processing results:"
print_status "   aws s3 ls s3://$BUCKET_NAME/output/"
echo ""
print_status "3. Download processed files:"
print_status "   aws s3 cp s3://$BUCKET_NAME/output/your-file.zip ./"
print_status "   aws s3 cp s3://$BUCKET_NAME/remediated/final_your-file.zip ./"
echo ""
print_status "4. Monitor processing:"
print_status "   aws logs tail /aws/lambda/$LAMBDA_FUNCTION --follow"
echo ""
print_success "🚀 Your PDF accessibility solution is ready to use!"
print_warning "💡 Tip: The first PDF processing may take longer as Lambda cold starts. Subsequent processing will be faster."
