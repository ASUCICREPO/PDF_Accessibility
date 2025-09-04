#!/bin/bash

# ========================================================================
# 🚀 PDF Accessibility Solutions - Unified Deployment! 🚀
# ========================================================================
# 
# This script will help you deploy either PDF accessibility solution:
# 1. PDF-to-PDF Remediation (maintains PDF format)
# 2. PDF-to-HTML Remediation (converts to accessible HTML)
#
# Choose your solution and we'll handle the rest! 😊
# ========================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_header() { echo -e "${CYAN}$1${NC}"; }

echo ""
print_header "🎉 Welcome to PDF Accessibility Solutions Unified Deployment! 🎉"
print_header "=================================================================="
echo ""
echo "This tool will help you deploy one of two PDF accessibility solutions:"
echo ""
echo "1. 📄 PDF-to-PDF Remediation"
echo "   • Maintains original PDF format"
echo "   • Uses Adobe PDF Services API"
echo "   • Advanced processing with ECS and Step Functions"
echo "   • Best for: Documents that must remain as PDFs"
echo ""
echo "2. 🌐 PDF-to-HTML Remediation"
echo "   • Converts PDFs to accessible HTML"
echo "   • Uses AWS Bedrock Data Automation"
echo "   • Serverless Lambda-based processing"
echo "   • Best for: Web-accessible content"
echo ""

# Step 1: Solution Selection
while true; do
    echo "Which solution would you like to deploy?"
    echo "1) PDF-to-PDF Remediation"
    echo "2) PDF-to-HTML Remediation"
    echo ""
    read -p "Enter your choice (1 or 2): " SOLUTION_CHOICE
    
    case $SOLUTION_CHOICE in
        1)
            DEPLOYMENT_TYPE="pdf2pdf"
            SOLUTION_NAME="PDF-to-PDF Remediation"
            break
            ;;
        2)
            DEPLOYMENT_TYPE="pdf2html"
            SOLUTION_NAME="PDF-to-HTML Remediation"
            break
            ;;
        *)
            print_error "Invalid choice. Please enter 1 or 2."
            echo ""
            ;;
    esac
done

print_success "✅ Selected: $SOLUTION_NAME"
echo ""

# Step 2: Common Configuration
print_status "📋 Step 2: Gathering deployment information..."
echo ""

# GitHub repository URL
if [ -z "$GITHUB_URL" ]; then
    echo "🔗 GitHub Repository Configuration:"
    read -p "   Enter your GitHub repository URL: " GITHUB_URL
    print_success "   Repository: $GITHUB_URL ✅"
    echo ""
fi

# CodeBuild project name
if [ -z "$PROJECT_NAME" ]; then
    echo "🏗️  CodeBuild Project Configuration:"
    read -p "   Enter the CodeBuild project name: " PROJECT_NAME
    print_success "   Project: $PROJECT_NAME ✅"
    echo ""
fi

# Step 3: Solution-specific configuration
if [ "$DEPLOYMENT_TYPE" == "pdf2pdf" ]; then
    print_status "🔐 Step 3: PDF-to-PDF specific configuration..."
    echo ""
    
    # Adobe API credentials
    if [ -z "$ADOBE_CLIENT_ID" ]; then
        echo "Adobe PDF Services API credentials are required:"
        echo "(These will be stored securely in AWS Secrets Manager)"
        read -p "   Enter Adobe API Client ID: " ADOBE_CLIENT_ID
        print_success "   Client ID received! ✅"
    fi

    if [ -z "$ADOBE_CLIENT_SECRET" ]; then
        read -p "   Enter Adobe API Client Secret: " ADOBE_CLIENT_SECRET
        print_success "   Client Secret received! ✅"
        echo ""
    fi
    
    # Set up Adobe credentials in Secrets Manager
    print_status "🔒 Setting up Adobe API credentials in AWS Secrets Manager..."
    
    JSON_TEMPLATE='{
      "client_credentials": {
        "PDF_SERVICES_CLIENT_ID": "<Your client ID here>",
        "PDF_SERVICES_CLIENT_SECRET": "<Your secret ID here>"
      }
    }'

    echo "$JSON_TEMPLATE" | jq --arg cid "$ADOBE_CLIENT_ID" --arg csec "$ADOBE_CLIENT_SECRET" \
        '.client_credentials.PDF_SERVICES_CLIENT_ID = $cid | 
         .client_credentials.PDF_SERVICES_CLIENT_SECRET = $csec' > client_credentials.json

    if aws secretsmanager create-secret --name /myapp/client_credentials --description "Client credentials for PDF services" --secret-string file://client_credentials.json 2>/dev/null; then
        print_success "   ✅ Secret created successfully in Secrets Manager!"
    else
        aws secretsmanager update-secret --secret-id /myapp/client_credentials --description "Updated client credentials for PDF services" --secret-string file://client_credentials.json
        print_success "   ✅ Secret updated successfully in Secrets Manager!"
    fi
    
    # Clean up temporary file
    rm -f client_credentials.json
    echo ""
    
elif [ "$DEPLOYMENT_TYPE" == "pdf2html" ]; then
    print_status "🧠 Step 3: PDF-to-HTML specific configuration..."
    echo ""
    
    # Verify AWS credentials first
    print_status "🔍 Verifying AWS credentials..."
    ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text 2>/dev/null || {
        print_error "Failed to get AWS account ID. Please ensure AWS CLI is configured."
        exit 1
    })
    
    REGION=$(aws configure get region 2>/dev/null)
    if [ -z "$REGION" ]; then
        print_error "AWS region not configured. Please set your region:"
        print_error "  aws configure set region <your-region>"
        exit 1
    fi
    print_success "✅ AWS credentials verified. Account: $ACCOUNT_ID, Region: $REGION"
    
    # Create BDA project
    BDA_PROJECT_NAME="pdf2html-bda-project-$(date +%Y%m%d-%H%M%S)"
    print_status "Creating Bedrock Data Automation project: $BDA_PROJECT_NAME"
    
    BDA_RESPONSE=$(aws bedrock-data-automation create-data-automation-project \
        --project-name "$BDA_PROJECT_NAME" \
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
    BUCKET_NAME="pdf2html-bucket-$ACCOUNT_ID-$REGION"
    
    print_success "✅ BDA project created successfully!"
    print_status "   Project ARN: $BDA_PROJECT_ARN"
    print_status "   S3 Bucket: $BUCKET_NAME"
    echo ""
fi

# Step 4: Create IAM Role
print_status "🔐 Step 4: Setting up IAM role for CodeBuild..."
ROLE_NAME="${PROJECT_NAME}-codebuild-service-role"

print_status "🔍 Checking if IAM role '$ROLE_NAME' exists..."
if aws iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
    print_success "✅ Role '$ROLE_NAME' already exists! Using existing role."
    ROLE_ARN=$(aws iam get-role --role-name "$ROLE_NAME" --output json | jq -r '.Role.Arn')
else
    print_status "🆕 Creating new IAM role..."
    
    TRUST_POLICY=$(cat <<EOF
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
    )

    CREATE_ROLE_OUTPUT=$(aws iam create-role \
        --role-name "$ROLE_NAME" \
        --assume-role-policy-document "$TRUST_POLICY" \
        --output json)

    if [ $? -ne 0 ]; then
        print_error "Failed to create IAM role."
        exit 1
    fi

    ROLE_ARN=$(echo "$CREATE_ROLE_OUTPUT" | jq -r '.Role.Arn')
    print_success "✅ Role created with ARN: $ROLE_ARN"

    # Attach appropriate policy based on solution type
    if [ "$DEPLOYMENT_TYPE" == "pdf2pdf" ]; then
        POLICY_ARN="arn:aws:iam::aws:policy/AdministratorAccess"
    else
        POLICY_ARN="arn:aws:iam::aws:policy/PowerUserAccess"
    fi
    
    print_status "🔗 Attaching policy to role..."
    aws iam attach-role-policy --role-name "$ROLE_NAME" --policy-arn "$POLICY_ARN"

    if [ $? -ne 0 ]; then
        print_error "Failed to attach policy."
        exit 1
    fi

    print_status "⏳ Waiting for role propagation..."
    sleep 15
    print_success "✅ Role setup complete!"
fi
echo ""

# Step 5: Create CodeBuild Project
print_status "🏗️  Step 5: Creating CodeBuild project..."

# Set build environment based on solution type
if [ "$DEPLOYMENT_TYPE" == "pdf2pdf" ]; then
    BUILD_IMAGE="aws/codebuild/amazonlinux-x86_64-standard:5.0"
    COMPUTE_TYPE="BUILD_GENERAL1_SMALL"
    PRIVILEGED_MODE="false"
    SOURCE_VERSION="main"
    BUILDSPEC_FILE="buildspec-unified.yml"
else
    BUILD_IMAGE="aws/codebuild/amazonlinux2-x86_64-standard:5.0"
    COMPUTE_TYPE="BUILD_GENERAL1_LARGE"
    PRIVILEGED_MODE="true"
    SOURCE_VERSION="main"
    BUILDSPEC_FILE="buildspec-unified.yml"
fi

# Create environment configuration
ENVIRONMENT="{\"type\": \"LINUX_CONTAINER\", \"image\": \"$BUILD_IMAGE\", \"computeType\": \"$COMPUTE_TYPE\", \"privilegedMode\": $PRIVILEGED_MODE}"

# Add environment variables based on solution type
if [ "$DEPLOYMENT_TYPE" == "pdf2html" ]; then
    ENV_VARS="[
        {\"name\": \"DEPLOYMENT_TYPE\", \"value\": \"$DEPLOYMENT_TYPE\"},
        {\"name\": \"ACCOUNT_ID\", \"value\": \"$ACCOUNT_ID\"},
        {\"name\": \"REGION\", \"value\": \"$REGION\"},
        {\"name\": \"BUCKET_NAME\", \"value\": \"$BUCKET_NAME\"},
        {\"name\": \"BDA_PROJECT_ARN\", \"value\": \"$BDA_PROJECT_ARN\"}
    ]"
else
    ENV_VARS="[
        {\"name\": \"DEPLOYMENT_TYPE\", \"value\": \"$DEPLOYMENT_TYPE\"}
    ]"
fi

ENVIRONMENT=$(echo "$ENVIRONMENT" | jq --argjson envvars "$ENV_VARS" '.environmentVariables = $envvars')

# Define source and artifacts
SOURCE="{\"type\": \"GITHUB\", \"location\": \"$GITHUB_URL\", \"buildspec\": \"$BUILDSPEC_FILE\"}"
ARTIFACTS='{"type": "NO_ARTIFACTS"}'

print_status "📦 Project Configuration:"
print_status "   Name: $PROJECT_NAME"
print_status "   Repository: $GITHUB_URL"
print_status "   Branch: $SOURCE_VERSION"
print_status "   Buildspec: $BUILDSPEC_FILE"
print_status "   Solution: $SOLUTION_NAME"
echo ""

aws codebuild create-project \
    --name "$PROJECT_NAME" \
    --source "$SOURCE" \
    --source-version "$SOURCE_VERSION" \
    --artifacts "$ARTIFACTS" \
    --environment "$ENVIRONMENT" \
    --service-role "$ROLE_ARN" \
    --output json > /dev/null

if [ $? -eq 0 ]; then
    print_success "✅ CodeBuild project '$PROJECT_NAME' created successfully!"
else
    print_error "Failed to create CodeBuild project. Please check your configuration."
    exit 1
fi
echo ""

# Step 6: Start the build
print_status "🚀 Step 6: Starting the deployment build..."
print_status "   Launching build for project '$PROJECT_NAME'..."

BUILD_RESPONSE=$(aws codebuild start-build \
    --project-name "$PROJECT_NAME" \
    --source-version "$SOURCE_VERSION" \
    --output json)

if [ $? -eq 0 ]; then
    BUILD_ID=$(echo "$BUILD_RESPONSE" | jq -r '.build.id')
    print_success "✅ Build started successfully!"
    print_status "   Build ID: $BUILD_ID"
else
    print_error "Failed to start the build."
    exit 1
fi
echo ""

# Step 7: Monitor build progress
print_status "📊 Step 7: Monitoring deployment progress..."
if [ "$DEPLOYMENT_TYPE" == "pdf2pdf" ]; then
    print_status "PDF-to-PDF deployment typically takes 3-5 minutes... ⏰"
else
    print_status "PDF-to-HTML deployment typically takes 5-10 minutes... ⏰"
fi
echo ""

DOTS=0
LAST_STATUS=""
while true; do
    BUILD_STATUS=$(aws codebuild batch-get-builds --ids $BUILD_ID --query 'builds[0].buildStatus' --output text)
    
    # Show status change
    if [ "$BUILD_STATUS" != "$LAST_STATUS" ]; then
        echo ""
        print_status "Build status: $BUILD_STATUS"
        LAST_STATUS="$BUILD_STATUS"
        DOTS=0
    fi
    
    case $BUILD_STATUS in
        "SUCCEEDED")
            echo ""
            print_success "🎉 Deployment completed successfully!"
            break
            ;;
        "FAILED"|"FAULT"|"STOPPED"|"TIMED_OUT")
            echo ""
            print_error "❌ Deployment failed with status: $BUILD_STATUS"
            
            # Get build logs for debugging
            print_error "Checking build logs..."
            LOG_GROUP="/aws/codebuild/$PROJECT_NAME"
            
            sleep 5
            
            LATEST_STREAM=$(aws logs describe-log-streams --log-group-name $LOG_GROUP --order-by LastEventTime --descending --max-items 1 --query 'logStreams[0].logStreamName' --output text 2>/dev/null || echo "")
            
            if [ -n "$LATEST_STREAM" ] && [ "$LATEST_STREAM" != "None" ]; then
                print_error "Recent build logs:"
                aws logs get-log-events --log-group-name $LOG_GROUP --log-stream-name $LATEST_STREAM --query 'events[-30:].message' --output text 2>/dev/null || print_error "Could not retrieve logs"
            else
                print_error "Could not retrieve build logs. Check CodeBuild console for details."
            fi
            exit 1
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

# Step 8: Show deployment results
echo ""
print_header "🎊 $SOLUTION_NAME Deployed Successfully!"
print_header "================================================"
echo ""

if [ "$DEPLOYMENT_TYPE" == "pdf2pdf" ]; then
    print_status "📋 PDF-to-PDF Deployment Summary:"
    print_status "   ✅ Adobe API credentials stored in AWS Secrets Manager"
    print_status "   ✅ Step Functions workflow deployed"
    print_status "   ✅ ECS cluster and tasks configured"
    print_status "   ✅ Lambda functions deployed"
    print_status "   ✅ CloudWatch dashboard created"
    echo ""
    print_status "🧪 Test Your Deployment:"
    print_status "1. Find your S3 bucket in the AWS Console"
    print_status "2. Create a 'pdf/' folder in the bucket"
    print_status "3. Upload a PDF file to the 'pdf/' folder"
    print_status "4. Monitor progress in the CloudWatch dashboard"
    echo ""
    
else
    print_status "📋 PDF-to-HTML Deployment Summary:"
    print_status "   ✅ S3 Bucket: $BUCKET_NAME"
    print_status "   ✅ BDA Project: $BDA_PROJECT_NAME"
    print_status "   ✅ Lambda function deployed"
    print_status "   ✅ ECR repository created"
    echo ""
    print_status "🧪 Test Your Deployment:"
    print_status "1. Upload a PDF file:"
    print_status "   aws s3 cp your-file.pdf s3://$BUCKET_NAME/uploads/"
    echo ""
    print_status "2. Check processing results:"
    print_status "   aws s3 ls s3://$BUCKET_NAME/output/"
    echo ""
    print_status "3. Download processed files:"
    print_status "   aws s3 cp s3://$BUCKET_NAME/remediated/final_your-file.zip ./"
    echo ""
fi

print_status "🔍 Monitor builds in AWS Console:"
print_status "   https://console.aws.amazon.com/codesuite/codebuild/projects"
echo ""

print_status "💡 Future Deployments:"
print_status "   You can reuse the CodeBuild project '$PROJECT_NAME' for updates:"
print_status "   aws codebuild start-build --project-name $PROJECT_NAME --source-version $SOURCE_VERSION"
echo ""

print_success "🚀 Your PDF accessibility solution is ready to use!"
print_success "Thank you for using PDF Accessibility Unified Deployment! 😊"
echo ""

exit 0
