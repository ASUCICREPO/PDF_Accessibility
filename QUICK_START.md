# PDF2HTML Accessibility Utility - Quick Start Guide

This guide provides quick instructions to deploy the PDF2HTML Accessibility Utility to your AWS account.

## Prerequisites

- AWS CLI installed and configured
- Node.js and npm installed
- Docker installed and running
- AWS CDK installed globally (`npm install -g aws-cdk`)

## Step 1: Create a Bedrock Data Automation (BDA) Project

```bash
aws bedrock-data-automation create-data-automation-project \
    --project-name pdf2html-bda-project \
    --standard-output-configuration '{"document": {"extraction": {"granularity": {"types": ["DOCUMENT", "PAGE", "ELEMENT"]},"boundingBox": {"state": "ENABLED"}},"generativeField": {"state": "DISABLED"},"outputFormat": {"textFormat": {"types": ["HTML"]},"additionalFileFormat": {"state": "ENABLED"}}}}'
```

Save the `projectArn` from the output.

## Step 2: Deploy the Solution

```bash
./deploy.sh --bda-project-arn <your-bda-project-arn>
```

The script will automatically:
- Create an S3 bucket if it doesn't exist
- Deploy all necessary AWS resources
- Build and push the Docker image
- Configure the Lambda function

## Step 3: Test the Deployment

Upload a PDF file to the S3 bucket:

```bash
aws s3 cp test.pdf s3://<your-bucket-name>/uploads/
```

Check for output files:

```bash
aws s3 ls s3://<your-bucket-name>/output/
```

Download and view the processed HTML:

```bash
aws s3 cp s3://<your-bucket-name>/output/test.zip .
unzip test.zip
```

## For More Information

See the [DEPLOYMENT.md](DEPLOYMENT.md) file for detailed deployment instructions and customization options.
