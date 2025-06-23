# Deployment Guide for PDF2HTML Accessibility Utility

This guide explains how to deploy the PDF2HTML Accessibility Utility to any AWS account.

## Prerequisites

Before deploying, ensure you have the following:

1. **AWS CLI** installed and configured with appropriate credentials
2. **Node.js and npm** installed (for CDK)
3. **AWS CDK** installed globally (`npm install -g aws-cdk`)
4. **Docker** installed and running

## Step 1: Create a Bedrock Data Automation (BDA) Project

First, create a BDA project using the AWS CLI:

```bash
aws bedrock-data-automation create-data-automation-project \
    --project-name pdf2html-bda-project \
    --standard-output-configuration '{"document": {"extraction": {"granularity": {"types": ["DOCUMENT", "PAGE", "ELEMENT"]},"boundingBox": {"state": "ENABLED"}},"generativeField": {"state": "DISABLED"},"outputFormat": {"textFormat": {"types": ["HTML"]},"additionalFileFormat": {"state": "ENABLED"}}}}'
```

Note the `projectArn` from the output. You'll need it for the deployment.

## Step 2: Deploy the Solution

Run the deployment script with the BDA project ARN:

```bash
./deploy.sh --bda-project-arn <your-bda-project-arn>
```

The script will:
1. Create an S3 bucket if it doesn't exist
2. Bootstrap CDK in your account (if needed)
3. Deploy the CloudFormation stack with all required resources
4. Build and push the Docker image to ECR
5. Update the Lambda function with the new image

### Customization Options

You can customize the deployment with the following parameters:

```bash
./deploy.sh --bda-project-arn <your-bda-project-arn> --region us-west-2 --bucket-name my-custom-bucket
```

Available options:
- `--bda-project-arn`: ARN of the pre-created BDA project (required)
- `--region`: AWS region to deploy to (default: us-east-1)
- `--stack-name`: Name of the CloudFormation stack (default: Pdf2HtmlStack)
- `--bucket-name`: Name of the S3 bucket (default: pdf2html-bucket-{account-id}-{region})

## Testing the Deployment

1. Upload a PDF file to the S3 bucket's 'uploads/' prefix:
   ```bash
   aws s3 cp test.pdf s3://your-bucket-name/uploads/
   ```

2. Check for output files:
   ```bash
   aws s3 ls s3://your-bucket-name/output/
   ```

3. Download the processed HTML:
   ```bash
   aws s3 cp s3://your-bucket-name/output/test.zip .
   unzip test.zip
   ```

## Architecture

The deployed solution includes:

1. **S3 Bucket** for storing input PDFs and output HTML files
2. **Lambda Function** that processes PDFs using the PDF2HTML utility
3. **ECR Repository** for the Docker image
4. **IAM Roles** with necessary permissions

## Troubleshooting

If you encounter issues:

1. Check Lambda function logs in CloudWatch Logs:
   ```bash
   aws logs describe-log-groups --log-group-name-prefix /aws/lambda/Pdf2HtmlPipeline
   aws logs get-log-events --log-group-name /aws/lambda/Pdf2HtmlPipeline --log-stream-name <latest-log-stream>
   ```

2. Verify S3 bucket permissions:
   ```bash
   aws s3api get-bucket-policy --bucket your-bucket-name
   ```

3. Ensure the BDA project was created successfully:
   ```bash
   aws bedrock-data-automation get-data-automation-project --project-arn <your-bda-project-arn>
   ```

4. Check that the Docker image was pushed to ECR correctly:
   ```bash
   aws ecr describe-images --repository-name pdf2html-lambda
   ```

## Cleanup

To remove all deployed resources:

1. Delete the CloudFormation stack:
   ```bash
   aws cloudformation delete-stack --stack-name Pdf2HtmlStack
   ```

2. Delete the S3 bucket (optional):
   ```bash
   aws s3 rm s3://your-bucket-name --recursive
   aws s3api delete-bucket --bucket your-bucket-name
   ```

3. Delete the BDA project (optional):
   ```bash
   aws bedrock-data-automation delete-data-automation-project --project-arn <your-bda-project-arn>
   ```
