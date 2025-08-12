#!/bin/bash

# ========================================================================
# 🚀 PDF2HTML Accessibility Utility - Automated Deployment! 🚀
# ========================================================================
# 
# This script will deploy your PDF2HTML accessibility solution to AWS!
# Here's what we'll do together:
#
# ✅ Create a Bedrock Data Automation (BDA) project
# ✅ Set up AWS CodeBuild project from GitHub repository
# ✅ Deploy complete infrastructure (S3, Lambda, ECR, etc.)
# ✅ Provide you with testing instructions
#
# Sit back and relax - we've got this! 😊
# ========================================================================

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

echo ""
echo "🎉 Welcome to PDF2HTML Accessibility Automated Deployment! 🎉"
echo "============================================================="
echo ""
echo "Let's get your PDF accessibility tools deployed to AWS!"
echo "This process will take just a few minutes. ⏰"
echo ""

# Configuration
REGION="us-east-1"
STACK_NAME="Pdf2HtmlStack"
PROJECT_NAME="pdf2html-bda-project-$(date +%Y%m%d-%H%M%S)"
GITHUB_URL="https://github.com/ASUCICREPO/PDF_Accessibility.git"
SOURCE_VERSION="pdf2html-subtree"
CODEBUILD_PROJECT="pdf2html-deploy-$(date +%s)"
CODEBUILD_ROLE="pdf2html-codebuild-role-$(date +%s)"

print_status "📋 Configuration:"
print_status "   Region: $REGION"
print_status "   GitHub Repository: $GITHUB_URL"
print_status "   Branch: $SOURCE_VERSION"
print_status "   CodeBuild Project: $CODEBUILD_PROJECT"
echo ""

# Step 1: Verify AWS credentials
print_status "🔍 Step 1: Verifying AWS credentials..."
ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text 2>/dev/null || {
    print_error "Failed to get AWS account ID. Please ensure AWS CLI is configured."
    exit 1
})

print_success "✅ AWS credentials verified. Account: $ACCOUNT_ID, Region: $REGION"
echo ""

# Set bucket name
BUCKET_NAME="pdf2html-bucket-$ACCOUNT_ID-$REGION"

# Step 2: Create BDA project
print_status "🧠 Step 2: Creating Bedrock Data Automation project..."
print_status "   Project Name: $PROJECT_NAME"

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
print_success "✅ BDA project created successfully!"
print_status "   Project ARN: $BDA_PROJECT_ARN"
echo ""

# Step 3: Create IAM role for CodeBuild
print_status "🔐 Step 3: Setting up IAM role for CodeBuild..."
print_status "   Role Name: $CODEBUILD_ROLE"

print_status "🔍 Checking if IAM role exists..."
if aws iam get-role --role-name "$CODEBUILD_ROLE" >/dev/null 2>&1; then
    print_success "✅ Role already exists! Using existing role."
    ROLE_ARN=$(aws iam get-role --role-name "$CODEBUILD_ROLE" --output json | jq -r '.Role.Arn')
else
    print_status "🆕 Creating new IAM role..."
    
    # Create trust policy
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
        --role-name "$CODEBUILD_ROLE" \
        --assume-role-policy-document "$TRUST_POLICY" \
        --output json)

    if [ $? -ne 0 ]; then
        print_error "Failed to create IAM role."
        exit 1
    fi

    ROLE_ARN=$(echo "$CREATE_ROLE_OUTPUT" | jq -r '.Role.Arn')
    print_success "✅ Role created with ARN: $ROLE_ARN"

    print_status "🔗 Attaching PowerUserAccess policy to role..."
    aws iam attach-role-policy --role-name "$CODEBUILD_ROLE" --policy-arn "arn:aws:iam::aws:policy/PowerUserAccess"

    if [ $? -ne 0 ]; then
        print_error "Failed to attach PowerUserAccess policy."
        exit 1
    fi

    print_status "⏳ Waiting for role propagation..."
    sleep 15
    print_success "✅ Role setup complete!"
fi
echo ""

# Step 4: Create CodeBuild project
print_status "🏗️  Step 4: Creating CodeBuild project..."
print_status "   Project Name: $CODEBUILD_PROJECT"
print_status "   Repository: $GITHUB_URL"
print_status "   Branch: $SOURCE_VERSION"

# Define build environment
ENVIRONMENT='{"type": "LINUX_CONTAINER", "image": "aws/codebuild/amazonlinux2-x86_64-standard:5.0", "computeType": "BUILD_GENERAL1_LARGE", "privilegedMode": true}'

# Define artifacts
ARTIFACTS='{"type": "NO_ARTIFACTS"}'

# Define source (simple, like the working project)
SOURCE='{"type": "GITHUB", "location": "'"$GITHUB_URL"'"}'

# Define environment variables
ENV_VARS='[
    {"name": "ACCOUNT_ID", "value": "'"$ACCOUNT_ID"'"},
    {"name": "REGION", "value": "'"$REGION"'"},
    {"name": "BUCKET_NAME", "value": "'"$BUCKET_NAME"'"},
    {"name": "BDA_PROJECT_ARN", "value": "'"$BDA_PROJECT_ARN"'"}
]'

# Update environment with variables
ENVIRONMENT=$(echo "$ENVIRONMENT" | jq --argjson envvars "$ENV_VARS" '.environmentVariables = $envvars')

aws codebuild create-project \
    --name "$CODEBUILD_PROJECT" \
    --source "$SOURCE" \
    --source-version "$SOURCE_VERSION" \
    --artifacts "$ARTIFACTS" \
    --environment "$ENVIRONMENT" \
    --service-role "$ROLE_ARN" \
    --output json > /dev/null

if [ $? -eq 0 ]; then
    print_success "✅ CodeBuild project '$CODEBUILD_PROJECT' created successfully!"
else
    print_error "Failed to create CodeBuild project. Please check your configuration."
    exit 1
fi
echo ""

# Step 5: Start the build
print_status "🚀 Step 5: Starting the deployment build..."
print_status "   Launching build for project '$CODEBUILD_PROJECT'..."

BUILD_RESPONSE=$(aws codebuild start-build \
    --project-name "$CODEBUILD_PROJECT" \
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

# Step 6: Monitor build progress
print_status "📊 Step 6: Monitoring deployment progress..."
print_status "This will take 5-10 minutes. Please be patient... ⏰"
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
            LOG_GROUP="/aws/codebuild/$CODEBUILD_PROJECT"
            
            # Wait a moment for logs to be available
            sleep 5
            
            # Try to get the latest log stream
            LATEST_STREAM=$(aws logs describe-log-streams --log-group-name $LOG_GROUP --order-by LastEventTime --descending --max-items 1 --query 'logStreams[0].logStreamName' --output text 2>/dev/null || echo "")
            
            if [ -n "$LATEST_STREAM" ] && [ "$LATEST_STREAM" != "None" ]; then
                print_error "Recent build logs:"
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

# Cleanup temporary resources (but keep CodeBuild project for future use)
print_status "🧹 Cleaning up temporary resources..."
# Note: Keeping CodeBuild project for future deployments
# Note: Keeping IAM role for future deployments
print_success "✅ Cleanup complete!"
echo ""

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
    print_status "   CodeBuild Project: $CODEBUILD_PROJECT (kept for future deployments)"
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
    print_status "💡 Future Deployments:"
    print_status "   You can reuse the CodeBuild project '$CODEBUILD_PROJECT' for updates:"
    print_status "   aws codebuild start-build --project-name $CODEBUILD_PROJECT --source-version $SOURCE_VERSION"
    echo ""
    print_status "🔍 Monitor builds in AWS Console:"
    print_status "   https://console.aws.amazon.com/codesuite/codebuild/projects"
    echo ""
    print_success "🚀 Your PDF accessibility solution is ready to use!"
    print_success "Thank you for using PDF2HTML Accessibility Automated Deployment! 😊"
else
    print_error "Deployment failed. Please check the error messages above and try again."
    exit 1
fi

echo ""
exit 0
