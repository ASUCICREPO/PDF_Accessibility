#!/bin/bash
# This script sets Adobe API credentials in AWS Secrets Manager,
# creates (or reuses) an IAM service role, creates a CodeBuild project using a
# specific branch from a GitHub repository (code-deploy-automation), and starts a build.

# ------------------------- Configuration Variables -------------------------

# Check if GitHub repository URL is provided; if not, prompt.
if [ -z "$GITHUB_URL" ]; then
    read -p "Enter the GitHub repository URL (e.g., https://github.com/ASUCICREPO/PDF_Accessibility): " GITHUB_URL
fi

# Check if CodeBuild project name is provided; if not, prompt.
if [ -z "$PROJECT_NAME" ]; then
    read -p "Enter the CodeBuild project name: " PROJECT_NAME
fi

# Check if Adobe API credentials are provided as environment variables; if not, prompt.
if [ -z "$ADOBE_CLIENT_ID" ]; then
    read -p "Enter Adobe API client key: " ADOBE_CLIENT_ID
fi

if [ -z "$ADOBE_CLIENT_SECRET" ]; then
    read -p "Enter Adobe API secret key: " ADOBE_CLIENT_SECRET
fi

# ------------------------- Adobe API Credentials Setup -------------------------

# Create a JSON template with placeholders
JSON_TEMPLATE='{
  "client_credentials": {
    "PDF_SERVICES_CLIENT_ID": "<Your client ID here>",
    "PDF_SERVICES_CLIENT_SECRET": "<Your secret ID here>"
  }
}'

# Replace placeholders with actual Adobe API credentials and store in client_credentials.json
echo "$JSON_TEMPLATE" | jq --arg cid "$ADOBE_CLIENT_ID" --arg csec "$ADOBE_CLIENT_SECRET" \
    '.client_credentials.PDF_SERVICES_CLIENT_ID = $cid | 
     .client_credentials.PDF_SERVICES_CLIENT_SECRET = $csec' > client_credentials.json

echo "Generated client_credentials.json:"
cat client_credentials.json

# Create or update the secret in AWS Secrets Manager
if aws secretsmanager create-secret --name /myapp/client_credentials --description "Client credentials for PDF services" --secret-string file://client_credentials.json 2>/dev/null; then
    echo "Secret created successfully in Secrets Manager."
else
    aws secretsmanager update-secret --secret-id /myapp/client_credentials --description "Updated client credentials for PDF services" --secret-string file://client_credentials.json
    echo "Secret updated successfully in Secrets Manager."
fi

# ----------------------- CodeBuild Project Setup ---------------------------

# Define a name for the IAM service role (unique per project)
ROLE_NAME="${PROJECT_NAME}-codebuild-service-role"

echo "Checking if IAM role '$ROLE_NAME' exists..."
if aws iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
  echo "Role '$ROLE_NAME' exists. Using the existing role."
  ROLE_ARN=$(aws iam get-role --role-name "$ROLE_NAME" --output json | jq -r '.Role.Arn')
else
  echo "Role '$ROLE_NAME' does not exist. Creating it now..."
  # Create a trust policy for CodeBuild
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
    echo "Error: Failed to create IAM role."
    exit 1
  fi

  ROLE_ARN=$(echo "$CREATE_ROLE_OUTPUT" | jq -r '.Role.Arn')
  echo "Role created with ARN: $ROLE_ARN"

  echo "Attaching AdministratorAccess policy to role..."
  aws iam attach-role-policy --role-name "$ROLE_NAME" --policy-arn "arn:aws:iam::aws:policy/AdministratorAccess"

  if [ $? -ne 0 ]; then
    echo "Error: Failed to attach AdministratorAccess policy."
    exit 1
  fi

  echo "Waiting a few seconds for role propagation..."
  sleep 10
fi

# Define the build environment settings using the amazonlinux-x86_64-standard:5.0 image
ENVIRONMENT='{"type": "LINUX_CONTAINER", "image": "aws/codebuild/amazonlinux-x86_64-standard:5.0", "computeType": "BUILD_GENERAL1_SMALL"}'

# Define the artifacts configuration (NO_ARTIFACTS in this example)
ARTIFACTS='{"type": "NO_ARTIFACTS"}'

# Create the source configuration JSON.
# The repository URL is provided without the branch; the branch is specified separately.
SOURCE='{"type": "GITHUB", "location": "'"$GITHUB_URL"'"}'

# Specify the source version (branch) you want to build (deployment branch)
SOURCE_VERSION="code-deploy-automation"

echo "Creating CodeBuild project '$PROJECT_NAME' using GitHub repo $GITHUB_URL with branch '$SOURCE_VERSION' ..."
aws codebuild create-project \
  --name "$PROJECT_NAME" \
  --source "$SOURCE" \
  --source-version "$SOURCE_VERSION" \
  --artifacts "$ARTIFACTS" \
  --environment "$ENVIRONMENT" \
  --service-role "$ROLE_ARN" \
  --output json

if [ $? -eq 0 ]; then
    echo "CodeBuild project '$PROJECT_NAME' created successfully."
else
    echo "Failed to create CodeBuild project. Please check your AWS CLI configuration and parameters."
    exit 1
fi

echo "Starting a build for project '$PROJECT_NAME' ..."
aws codebuild start-build --project-name "$PROJECT_NAME" --output json

if [ $? -eq 0 ]; then
    echo "Build started successfully."
else
    echo "Failed to start the build."
    exit 1
fi

echo "Listing CodeBuild projects:"
aws codebuild list-projects --output table

# Auto exit the script
exit 0
