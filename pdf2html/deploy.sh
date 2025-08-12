#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Configuration
REGION="us-east-1"
STACK_NAME="Pdf2HtmlStack"
PROJECT_NAME="pdf2html-bda-project-$(date +%Y%m%d-%H%M%S)"

print_status "🚀 PDF2HTML Accessibility Utility Deployment"
print_status "============================================="

# Verify AWS credentials
print_status "Verifying AWS credentials..."
ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text 2>/dev/null || {
    print_error "Failed to get AWS account ID. Please ensure AWS CLI is configured."
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

# Setup CodeBuild deployment
TIMESTAMP=$(date +%s)
CODEBUILD_PROJECT="pdf2html-deploy-$TIMESTAMP"
CODEBUILD_ROLE="pdf2html-codebuild-role-$TIMESTAMP"
TEMP_BUCKET="temp-codebuild-$ACCOUNT_ID-$TIMESTAMP"

print_status "Setting up CodeBuild deployment..."

# Create temporary S3 bucket for source code
if [ "$REGION" == "us-east-1" ]; then
    aws s3api create-bucket --bucket $TEMP_BUCKET >/dev/null
else
    aws s3api create-bucket --bucket $TEMP_BUCKET --region $REGION --create-bucket-configuration LocationConstraint=$REGION >/dev/null
fi

# Create source archive
print_status "Preparing source code..."
tar --exclude='.git' --exclude='node_modules' --exclude='.DS_Store' -czf source.tar.gz . 2>/dev/null
aws s3 cp source.tar.gz s3://$TEMP_BUCKET/ >/dev/null

# Create IAM role for CodeBuild
print_status "Creating IAM role for CodeBuild..."
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

aws iam create-role \
    --role-name $CODEBUILD_ROLE \
    --assume-role-policy-document file://trust-policy.json >/dev/null

aws iam attach-role-policy \
    --role-name $CODEBUILD_ROLE \
    --policy-arn arn:aws:iam::aws:policy/PowerUserAccess >/dev/null

# Wait for role propagation
print_status "Waiting for IAM role to propagate..."
sleep 20

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
print_status "Monitoring deployment progress (this takes 5-10 minutes)..."

# Monitor build progress
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
            print_error "Build logs:"
            LOG_GROUP="/aws/codebuild/$CODEBUILD_PROJECT"
            sleep 5
            
            LATEST_STREAM=$(aws logs describe-log-streams --log-group-name $LOG_GROUP --order-by LastEventTime --descending --max-items 1 --query 'logStreams[0].logStreamName' --output text 2>/dev/null || echo "")
            
            if [ -n "$LATEST_STREAM" ] && [ "$LATEST_STREAM" != "None" ]; then
                aws logs get-log-events --log-group-name $LOG_GROUP --log-stream-name $LATEST_STREAM --query 'events[-30:].message' --output text 2>/dev/null || print_error "Could not retrieve logs"
            else
                print_error "Could not retrieve build logs. Check CodeBuild console for details."
            fi
            break
            ;;
        "IN_PROGRESS")
            printf "."
            DOTS=$((DOTS + 1))
            if [ $DOTS -eq 60 ]; then
                echo ""
                print_status "Still building... Please wait..."
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
rm -f trust-policy.json project.json source.tar.gz

# Show results if successful
if [ "$BUILD_STATUS" == "SUCCEEDED" ]; then
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
    echo ""
    print_status "4. Monitor processing:"
    print_status "   aws logs tail /aws/lambda/$LAMBDA_FUNCTION --follow"
    echo ""
    print_success "🚀 Your PDF accessibility solution is ready to use!"
else
    print_error "Deployment failed. Please check the error messages above and try again."
    exit 1
fi
