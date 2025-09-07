#!/bin/bash

# ========================================================================
# 🚀 PDF Accessibility Solutions - Unified Deployment Script! 🚀
# ========================================================================
# 
# This script will help you deploy PDF accessibility solutions with options for:
# 1. PDF-to-PDF Remediation (maintains PDF format)
# 2. PDF-to-HTML Remediation (converts to accessible HTML)
# 3. Frontend UI (connects to deployed backend solutions)
#
# Smart cascading deployment - deploy one, both, or add UI! 😊
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

# Global deployment tracking variables
DEPLOYED_SOLUTIONS=()
DEPLOYED_BUCKETS=()
FIRST_SOLUTION=""
PDF2PDF_BUCKET=""
PDF2HTML_BUCKET=""

echo ""
print_header "🎉 Welcome to PDF Accessibility Solutions Enhanced Deployment! 🎉"
print_header "====================================================================="
echo ""
echo "This tool will help you deploy PDF accessibility solutions:"
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
echo "3. 🎨 Frontend UI"
echo "   • Web interface for both solutions"
echo "   • User authentication with Cognito"
echo "   • File upload and processing monitoring"
echo "   • Best for: End-user accessibility"
echo ""

# Function to deploy backend solution
deploy_backend_solution() {
    local solution_type=$1
    local solution_name=$2
    
    print_header "🚀 Deploying $solution_name..."
    
    DEPLOYMENT_TYPE="$solution_type"
    
    # Solution-specific configuration
    if [ "$DEPLOYMENT_TYPE" == "pdf2pdf" ]; then
        print_status "🔐 PDF-to-PDF specific configuration..."
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
        print_status "🧠 PDF-to-HTML specific configuration..."
        echo ""
        
        # Create BDA project (using already verified credentials and region)
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

    # Create IAM Role (if not exists)
    ROLE_NAME="${PROJECT_NAME}-codebuild-service-role"

    print_status "🔐 Setting up IAM role for CodeBuild..."
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

        # Create minimal IAM policy based on solution type
        if [ "$DEPLOYMENT_TYPE" == "pdf2pdf" ]; then
            # PDF-to-PDF minimal policy
            POLICY_NAME="${PROJECT_NAME}-pdf2pdf-codebuild-policy"
            POLICY_DOCUMENT='{
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "S3FullAccess",
                        "Effect": "Allow",
                        "Action": ["s3:*"],
                        "Resource": "*"
                    },
                    {
                        "Sid": "ECRFullAccess",
                        "Effect": "Allow",
                        "Action": ["ecr:*"],
                        "Resource": "*"
                    },
                    {
                        "Sid": "LambdaFullAccess",
                        "Effect": "Allow",
                        "Action": ["lambda:*"],
                        "Resource": "*"
                    },
                    {
                        "Sid": "ECSFullAccess",
                        "Effect": "Allow",
                        "Action": ["ecs:*"],
                        "Resource": "*"
                    },
                    {
                        "Sid": "EC2FullAccess",
                        "Effect": "Allow",
                        "Action": ["ec2:*"],
                        "Resource": "*"
                    },
                    {
                        "Sid": "StepFunctionsFullAccess",
                        "Effect": "Allow",
                        "Action": ["states:*"],
                        "Resource": "*"
                    },
                    {
                        "Sid": "IAMFullAccess",
                        "Effect": "Allow",
                        "Action": ["iam:*"],
                        "Resource": "*"
                    },
                    {
                        "Sid": "CloudFormationFullAccess",
                        "Effect": "Allow",
                        "Action": ["cloudformation:*"],
                        "Resource": "*"
                    },
                    {
                        "Sid": "BedrockFullAccess",
                        "Effect": "Allow",
                        "Action": [
                            "bedrock:*",
                            "bedrock-data-automation:*",
                            "bedrock-data-automation-runtime:*"
                        ],
                        "Resource": "*"
                    },
                    {
                        "Sid": "CloudWatchLogsFullAccess",
                        "Effect": "Allow",
                        "Action": ["logs:*"],
                        "Resource": "*"
                    },
                    {
                        "Sid": "CloudWatchFullAccess",
                        "Effect": "Allow",
                        "Action": ["cloudwatch:*"],
                        "Resource": "*"
                    },
                    {
                        "Sid": "SecretsManagerFullAccess",
                        "Effect": "Allow",
                        "Action": ["secretsmanager:*"],
                        "Resource": "*"
                    },
                    {
                        "Sid": "STSAccess",
                        "Effect": "Allow",
                        "Action": [
                            "sts:GetCallerIdentity",
                            "sts:AssumeRole"
                        ],
                        "Resource": "*"
                    },
                    {
                        "Sid": "SSMParameterAccess",
                        "Effect": "Allow",
                        "Action": [
                            "ssm:GetParameter",
                            "ssm:GetParameters",
                            "ssm:PutParameter"
                        ],
                        "Resource": "*"
                    }
                ]
            }'
        else
            # PDF-to-HTML minimal policy
            POLICY_NAME="${PROJECT_NAME}-pdf2html-codebuild-policy"
            POLICY_DOCUMENT='{
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "S3FullAccess",
                        "Effect": "Allow",
                        "Action": ["s3:*"],
                        "Resource": "*"
                    },
                    {
                        "Sid": "ECRFullAccess",
                        "Effect": "Allow",
                        "Action": ["ecr:*"],
                        "Resource": "*"
                    },
                    {
                        "Sid": "LambdaFullAccess",
                        "Effect": "Allow",
                        "Action": ["lambda:*"],
                        "Resource": "*"
                    },
                    {
                        "Sid": "IAMFullAccess",
                        "Effect": "Allow",
                        "Action": ["iam:*"],
                        "Resource": "*"
                    },
                    {
                        "Sid": "CloudFormationFullAccess",
                        "Effect": "Allow",
                        "Action": ["cloudformation:*"],
                        "Resource": "*"
                    },
                    {
                        "Sid": "BedrockFullAccess",
                        "Effect": "Allow",
                        "Action": [
                            "bedrock:*",
                            "bedrock-data-automation:*",
                            "bedrock-data-automation-runtime:*"
                        ],
                        "Resource": "*"
                    },
                    {
                        "Sid": "CloudWatchLogsFullAccess",
                        "Effect": "Allow",
                        "Action": ["logs:*"],
                        "Resource": "*"
                    },
                    {
                        "Sid": "STSAccess",
                        "Effect": "Allow",
                        "Action": [
                            "sts:GetCallerIdentity",
                            "sts:AssumeRole"
                        ],
                        "Resource": "*"
                    },
                    {
                        "Sid": "SSMParameterAccess",
                        "Effect": "Allow",
                        "Action": [
                            "ssm:GetParameter",
                            "ssm:GetParameters",
                            "ssm:PutParameter"
                        ],
                        "Resource": "*"
                    }
                ]
            }'
        fi
        
        # Create the policy
        print_status "📋 Creating IAM policy: $POLICY_NAME"
        POLICY_RESPONSE=$(aws iam create-policy \
            --policy-name "$POLICY_NAME" \
            --policy-document "$POLICY_DOCUMENT" \
            --description "Minimal IAM policy for $DEPLOYMENT_TYPE CodeBuild deployment" 2>/dev/null || \
            aws iam get-policy --policy-arn "arn:aws:iam::$ACCOUNT_ID:policy/$POLICY_NAME" 2>/dev/null)
        
        if [ $? -eq 0 ]; then
            POLICY_ARN=$(echo "$POLICY_RESPONSE" | jq -r '.Policy.Arn // .Policy.Arn')
            print_success "✅ Policy ready: $POLICY_NAME"
        else
            print_error "Failed to create or retrieve IAM policy"
            exit 1
        fi
        
        print_status "🔗 Attaching policy to role..."
        aws iam attach-role-policy --role-name "$ROLE_NAME" --policy-arn "$POLICY_ARN"
        
        # Store policy info for potential cleanup
        CREATED_POLICY_ARN="$POLICY_ARN"
        CREATED_POLICY_NAME="$POLICY_NAME"

        if [ $? -ne 0 ]; then
            print_error "Failed to attach policy."
            exit 1
        fi

        print_status "⏳ Waiting for role propagation..."
        sleep 15
        print_success "✅ Role setup complete!"
    fi
    echo ""

    # Create CodeBuild Project
    print_status "🏗️  Creating CodeBuild project..."

    # Set build environment based on solution type
    if [ "$DEPLOYMENT_TYPE" == "pdf2pdf" ]; then
        BUILD_IMAGE="aws/codebuild/amazonlinux-x86_64-standard:5.0"
        COMPUTE_TYPE="BUILD_GENERAL1_SMALL"
        PRIVILEGED_MODE="false"
        SOURCE_VERSION="pdf2html-subtree"  # Use pdf2html-subtree since buildspec only exists there
        BUILDSPEC_FILE="buildspec-unified.yml"
    else
        BUILD_IMAGE="aws/codebuild/amazonlinux2-x86_64-standard:5.0"
        COMPUTE_TYPE="BUILD_GENERAL1_LARGE"
        PRIVILEGED_MODE="true"
        SOURCE_VERSION="pdf2html-subtree"
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
    print_status "   Solution: $solution_name"
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
        print_warning "⚠️ CodeBuild project may already exist, continuing..."
    fi
    echo ""

    # Start the build
    print_status "🚀 Starting the deployment build..."
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

    # Monitor build progress
    print_status "📊 Monitoring deployment progress..."
    if [ "$DEPLOYMENT_TYPE" == "pdf2pdf" ]; then
        print_status "$solution_name deployment typically takes 3-5 minutes... ⏰"
    else
        print_status "$solution_name deployment typically takes 5-10 minutes... ⏰"
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
                print_success "🎉 $solution_name deployment completed successfully!"
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

    # Collect bucket information after successful deployment
    if [ "$DEPLOYMENT_TYPE" == "pdf2pdf" ]; then
        # Try multiple methods to get PDF-to-PDF bucket name
        print_status "🔍 Retrieving PDF-to-PDF bucket name..."
        
        # Method 1: Try CloudFormation stack outputs
        PDF2PDF_BUCKET=$(aws cloudformation describe-stacks \
            --stack-name "PDFAccessibility" \
            --query 'Stacks[0].Outputs[?OutputKey==`S3BucketName`].OutputValue' \
            --output text 2>/dev/null)
        
        # Method 2: Try alternative output key names
        if [ -z "$PDF2PDF_BUCKET" ] || [ "$PDF2PDF_BUCKET" == "None" ]; then
            PDF2PDF_BUCKET=$(aws cloudformation describe-stacks \
                --stack-name "PDFAccessibility" \
                --query 'Stacks[0].Outputs[?contains(OutputKey, `Bucket`)].OutputValue' \
                --output text 2>/dev/null | head -1)
        fi
        
        # Method 3: Find bucket by naming pattern and creation time
        if [ -z "$PDF2PDF_BUCKET" ] || [ "$PDF2PDF_BUCKET" == "None" ]; then
            PDF2PDF_BUCKET=$(aws s3api list-buckets \
                --query 'Buckets[?contains(Name, `pdfaccessibility`) && CreationDate >= `'$(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S)'`].Name' \
                --output text 2>/dev/null | head -1)
        fi
        
        # Method 4: Get the most recently created bucket with pdfaccessibility in name
        if [ -z "$PDF2PDF_BUCKET" ] || [ "$PDF2PDF_BUCKET" == "None" ]; then
            PDF2PDF_BUCKET=$(aws s3api list-buckets \
                --query 'Buckets[?contains(Name, `pdfaccessibility`)] | sort_by(@, &CreationDate) | [-1].Name' \
                --output text 2>/dev/null)
        fi
        
        if [ -n "$PDF2PDF_BUCKET" ] && [ "$PDF2PDF_BUCKET" != "None" ]; then
            DEPLOYED_BUCKETS+=("$PDF2PDF_BUCKET")
            print_status "   📦 S3 Bucket: $PDF2PDF_BUCKET"
        else
            print_warning "   ⚠️ Could not automatically detect PDF-to-PDF bucket name"
            print_status "   Please check AWS Console for the bucket name starting with 'pdfaccessibility'"
        fi
        
    elif [ "$DEPLOYMENT_TYPE" == "pdf2html" ]; then
        PDF2HTML_BUCKET="$BUCKET_NAME"
        DEPLOYED_BUCKETS+=("$PDF2HTML_BUCKET")
        print_status "   📦 S3 Bucket: $PDF2HTML_BUCKET"
        print_status "   🧠 BDA Project: $BDA_PROJECT_NAME"
    fi
    
    # Track deployed solution
    DEPLOYED_SOLUTIONS+=("$DEPLOYMENT_TYPE")
    
    echo ""
    print_success "✅ $solution_name deployment summary complete!"
}

# Function to deploy UI
deploy_ui() {
    print_header "🎨 Deploying Frontend UI..."
    echo ""
    
    # Validate that we have at least one deployed solution
    if [ ${#DEPLOYED_SOLUTIONS[@]} -eq 0 ]; then
        print_error "No backend solutions deployed. Cannot deploy UI without backend."
        return 1
    fi
    
    # Determine bucket configuration for UI
    local pdf_to_pdf_bucket="Null"
    local pdf_to_html_bucket="Null"
    
    if [[ " ${DEPLOYED_SOLUTIONS[@]} " =~ " pdf2pdf " ]]; then
        pdf_to_pdf_bucket="$PDF2PDF_BUCKET"
    fi
    
    if [[ " ${DEPLOYED_SOLUTIONS[@]} " =~ " pdf2html " ]]; then
        pdf_to_html_bucket="$PDF2HTML_BUCKET"
    fi
    
    # Validate that at least one solution was deployed
    if [ "$pdf_to_pdf_bucket" == "Null" ] && [ "$pdf_to_html_bucket" == "Null" ]; then
        print_error "No backend solutions deployed. Cannot deploy UI without backend."
        return 1
    fi
    
    print_status "🔧 UI Configuration:"
    print_status "   PDF-to-PDF Bucket: $pdf_to_pdf_bucket"
    print_status "   PDF-to-HTML Bucket: $pdf_to_html_bucket"
    echo ""
    
    # Store current directory
    ORIGINAL_DIR=$(pwd)
    
    # Clone UI repository to temporary location
    UI_TEMP_DIR="/tmp/pdf-ui-deployment-$$"
    print_status "📥 Cloning UI repository..."
    
    if ! git clone -b updatedUI https://github.com/ASUCICREPO/PDF_accessability_UI "$UI_TEMP_DIR" 2>/dev/null; then
        print_error "Failed to clone UI repository. Check internet connection and repository access."
        return 1
    fi
    
    cd "$UI_TEMP_DIR" || {
        print_error "Failed to change to UI directory"
        return 1
    }
    
    # Set environment variables for UI deployment
    export PROJECT_NAME="${PROJECT_NAME}-ui"
    export PDF_TO_PDF_BUCKET="$pdf_to_pdf_bucket"
    export PDF_TO_HTML_BUCKET="$pdf_to_html_bucket"
    export TARGET_BRANCH="updatedUI"
    
    print_status "🚀 Starting UI deployment..."
    print_status "   This may take 10-15 minutes..."
    
    # Verify UI deployment script exists
    if [ ! -f "deploy.sh" ]; then
        print_error "UI deployment script not found in repository"
        cd "$ORIGINAL_DIR"
        rm -rf "$UI_TEMP_DIR"
        return 1
    fi
    
    # Make script executable and run
    chmod +x deploy.sh
    
    # Run UI deployment script with error handling
    if ./deploy.sh; then
        print_success "✅ UI deployment completed successfully!"
        
        # Extract Amplify URL from the deployment
        AMPLIFY_URL=$(aws cloudformation describe-stacks \
            --stack-name "${PROJECT_NAME}-AmplifyHostingStack" \
            --query 'Stacks[0].Outputs[?OutputKey==`AmplifyWebsiteUrl`].OutputValue' \
            --output text 2>/dev/null)
        
        if [ -n "$AMPLIFY_URL" ] && [ "$AMPLIFY_URL" != "None" ]; then
            print_success "🌐 Frontend URL: $AMPLIFY_URL"
        else
            print_warning "⚠️ Could not retrieve Amplify URL. Check CloudFormation console."
        fi
    else
        print_error "❌ UI deployment failed. Check the logs above for details."
        cd "$ORIGINAL_DIR"
        rm -rf "$UI_TEMP_DIR"
        return 1
    fi
    
    # Cleanup
    cd "$ORIGINAL_DIR"
    rm -rf "$UI_TEMP_DIR"
    
    echo ""
    return 0
}

# Function to show next step options
show_next_step_options() {
    local first_solution=$1
    
    echo ""
    print_header "🤔 What would you like to do next?"
    print_header "=================================="
    echo ""
    
    # Determine what options to show
    if [ "$first_solution" == "pdf2pdf" ]; then
        OTHER_SOLUTION="pdf2html"
        OTHER_SOLUTION_NAME="PDF-to-HTML Remediation"
    else
        OTHER_SOLUTION="pdf2pdf"
        OTHER_SOLUTION_NAME="PDF-to-PDF Remediation"
    fi
    
    echo "1) Deploy $OTHER_SOLUTION_NAME (complete both backend solutions)"
    echo "2) Deploy Frontend UI (for current solution)"
    echo "3) Finish (backend only)"
    echo ""
    
    while true; do
        read -p "Enter your choice (1, 2, or 3): " NEXT_CHOICE
        
        case $NEXT_CHOICE in
            1)
                print_success "✅ Selected: Deploy $OTHER_SOLUTION_NAME"
                
                # Update project name to avoid conflicts
                PROJECT_NAME="${PROJECT_NAME}-${OTHER_SOLUTION}"
                
                # Deploy the other solution
                deploy_backend_solution "$OTHER_SOLUTION" "$OTHER_SOLUTION_NAME"
                
                # After deploying both solutions, ask about UI
                echo ""
                print_status "🎉 Both backend solutions deployed successfully!"
                echo ""
                while true; do
                    read -p "Would you like to deploy the Frontend UI? (y/n): " DEPLOY_UI_CHOICE
                    case $DEPLOY_UI_CHOICE in
                        [Yy]*)
                            deploy_ui
                            break
                            ;;
                        [Nn]*)
                            print_success "Backend deployments complete!"
                            break
                            ;;
                        *)
                            print_error "Please answer yes (y) or no (n)."
                            ;;
                    esac
                done
                break
                ;;
            2)
                print_success "✅ Selected: Deploy Frontend UI"
                deploy_ui
                break
                ;;
            3)
                print_success "✅ Selected: Finish (backend only)"
                break
                ;;
            *)
                print_error "Invalid choice. Please enter 1, 2, or 3."
                echo ""
                ;;
        esac
    done
}

# Main execution starts here
echo ""

# Step 1: Initial Solution Selection
while true; do
    echo "Which solution would you like to deploy first?"
    echo "1) PDF-to-PDF Remediation"
    echo "2) PDF-to-HTML Remediation"
    echo ""
    read -p "Enter your choice (1 or 2): " SOLUTION_CHOICE
    
    case $SOLUTION_CHOICE in
        1)
            DEPLOYMENT_TYPE="pdf2pdf"
            SOLUTION_NAME="PDF-to-PDF Remediation"
            FIRST_SOLUTION="pdf2pdf"
            break
            ;;
        2)
            DEPLOYMENT_TYPE="pdf2html"
            SOLUTION_NAME="PDF-to-HTML Remediation"
            FIRST_SOLUTION="pdf2html"
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
print_status "📋 Gathering deployment information..."
echo ""

# Verify AWS credentials and get region (common for both solutions)
print_status "🔍 Verifying AWS credentials..."
ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text 2>/dev/null || {
    print_error "Failed to get AWS account ID. Please ensure AWS CLI is configured."
    exit 1
})

# Get current region from environment variable (CloudShell region)
REGION=$AWS_DEFAULT_REGION

# Fallback to AWS CLI configuration if environment variable not set
if [ -z "$REGION" ]; then
    REGION=$(aws configure get region 2>/dev/null)
fi

if [ -z "$REGION" ]; then
    REGION=$(aws configure get region --profile default 2>/dev/null)
fi

if [ -z "$REGION" ]; then
    print_error "Could not determine AWS region. Please set your region:"
    print_error "  export AWS_DEFAULT_REGION=us-west-2"
    print_error "  OR: aws configure set region us-west-2"
    exit 1
fi

print_success "✅ AWS credentials verified. Account: $ACCOUNT_ID, Region: $REGION"
echo ""

# GitHub repository URL (hardcoded)
GITHUB_URL="https://github.com/ASUCICREPO/PDF_Accessibility.git"
print_success "   Repository: $GITHUB_URL ✅"
echo ""

# CodeBuild project name (hardcoded with timestamp)
PROJECT_NAME="pdfremediation-$(date +%Y%m%d%H%M%S)"
print_success "   Project: $PROJECT_NAME ✅"
echo ""

# Step 3: Deploy first solution
deploy_backend_solution "$DEPLOYMENT_TYPE" "$SOLUTION_NAME"

# Step 4: Show next step options
show_next_step_options "$FIRST_SOLUTION"

# Step 5: Final success message
echo ""
print_header "🎊 Deployment Complete!"
print_header "======================="
echo ""

print_status "📊 Deployment Summary:"
for solution in "${DEPLOYED_SOLUTIONS[@]}"; do
    if [ "$solution" == "pdf2pdf" ]; then
        print_status "   ✅ PDF-to-PDF Remediation: $PDF2PDF_BUCKET"
    elif [ "$solution" == "pdf2html" ]; then
        print_status "   ✅ PDF-to-HTML Remediation: $PDF2HTML_BUCKET"
    fi
done

if [ -n "$AMPLIFY_URL" ]; then
    print_status "   🌐 Frontend UI: $AMPLIFY_URL"
fi

echo ""
print_status "🔍 Monitor builds in AWS Console:"
print_status "   https://console.aws.amazon.com/codesuite/codebuild/projects"
echo ""

print_success "🚀 Your PDF accessibility solution is ready to use!"
print_success "Thank you for using PDF Accessibility Enhanced Deployment! 😊"
echo ""

exit 0