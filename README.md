# PDF Accessibility Solutions

This repository provides two complementary solutions for PDF accessibility:

1. **PDF-to-PDF Remediation**: The solution that processes PDFs and maintains the PDF format while improving accessibility.
2. **PDF-to-HTML Remediation**: A newer solution that converts PDFs to accessible HTML format.

Both solutions leverage AWS services and generative AI to improve content accessibility according to WCAG 2.1 Level AA standards.

## PDF-to-PDF Processing AWS Infrastructure

This project builds an AWS infrastructure using AWS CDK (Cloud Development Kit) to split a PDF into chunks, process the chunks via AWS Step Functions, and merge the resulting chunks back using ECS tasks. The infrastructure also includes monitoring via CloudWatch dashboards and metrics for tracking progress.

### Automated One Click Deployment

#### Deployment Instructions

#### Common Prerequisites

1. **Fork this repository** to your own GitHub account (required for deployment and CI/CD):
   - Navigate to https://github.com/ASUCICREPO/PDF_Accessibility
   - Click the "Fork" button in the top right corner
   - Select your GitHub account as the destination
   - Wait for the forking process to complete
   - You'll now have your own copy at https://github.com/YOUR-USERNAME/PDF_Accessibility

2. **Obtain a GitHub personal access token** with repo permissions (needed for CDK deployment):
   - Go to GitHub Settings > Developer Settings > Personal Access Tokens > Tokens (classic)
   - Click "Generate new token (classic)"
   - Give the token a name and select the "repo" and "admin:repo_hook" scope
   - Click "Generate token" and save the token securely
   - For detailed instructions, see: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens

3. **Enable the following AWS Bedrock model** in your AWS account:
   - NOVA_PRO

   To request access to this model:
   - Navigate to the AWS Bedrock console
   - Click "Model access" in the left navigation pane
   - Click "Manage model access."
   - Find the model in the list and select the checkbox next to it
   - Click "Save changes" at the bottom of the page
   - Wait for model access to be granted (usually within minutes)
   - Verify access by checking the "Status" column shows "Access granted"
   - Note: If you don't see the option to enable a model, ensure your AWS account and region support Bedrock model access. Contact AWS Support if needed.

5. **AWS Account Permissions**
   - Ensure permissions to create and manage AWS resources like S3, Lambda, etc.
   - [AWS IAM Policies and Permissions](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies.html)

#### Deployment Using AWS CodeBuild and AWS Cloudshell

**Prerequisites:**
- Have access to CodeBuild and AWS Cloudshell

**Deployment:**

1. **Open AWS CloudShell** in your AWS Console:
   - Click the CloudShell icon in the AWS Console navigation bar
   - Wait for the CloudShell environment to initialize

2. **Clone the repository** (Make sure to have your own forked copy of the repo and replace the link with the forked repository link):
   ```bash
   git clone https://github.com/<YOUR-USERNAME>/PDF_Accessibility
   cd PDF_Accessibility/
   ```

3. **Deploy using the deployment script** (recommended):
   The script would prompt you for variables needed for deployment.
   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```

#### Manual CDK Deployment

For manual deployment instructions, see our [Manual Deployment Guide](docs/MANUAL_DEPLOYMENT.md).

## Usage

Once the infrastructure is deployed:

1. Create a `pdf/` folder in the S3 bucket created by the CDK stack.
2. Upload a PDF file to the `pdf/` folder in the S3 bucket.
3. The process will automatically trigger and start processing the PDF.

## Monitoring

- Use the CloudWatch dashboards created by the stack to monitor the progress and performance of the PDF processing pipeline.

## Limitations

- This solution does not remediate corrupted PDFs.
- It can process scanned PDFs, but the output accuracy is approximately 80%.
- It does not remediate fillable forms.
- It does not handle color selection/contrast adjustments.

## Troubleshooting

If you encounter any issues during setup or deployment, please check the following:

- Ensure all prerequisites are correctly installed and configured.
- Verify that your AWS credentials have the necessary permissions.
- Check CloudWatch logs for any error messages in the Lambda functions or ECS tasks. 
- If the CDK Deploy responds with: ` Python was not found; run without arguments to install from the Microsoft Store, or disable this shortcut from Settings > Manage App Execution Aliases.
Subprocess exited with error 9009 `, try changing ` "app": "python3 app.py" ` to  ` "app": "python app.py" ` in the cdk.json file
- If the CDK deploy responds with: ` Resource handler returned message: "The maximum number of addresses has been reached. ` request additional IPs from AWS. Go to https://us-east-1.console.aws.amazon.com/servicequotas/home/services/ec2/quotas and search for "IP". Then, choose "EC2-VPC Elastic IPs". Note the AWS region is included in the URL, change it to the region you are deploying into. Requests for additional IPs are usually completed within minutes.
- If any Docker images are not pushing to ECR, manually deploy to ECR using the push commands provided in the ECR console. Then, manually update the ECS service by creating a new revision of the task definition and updating the image URI with the one just deployed.

For further assistance, please open an issue in this repository.
- If you encounter issues with deployment, refer to the related discussion on the AWS CDK GitHub repository for further troubleshooting: [CDK Github Issue](https://github.com/aws/aws-cdk/issues/30258). You can also consult our [Troubleshooting CDK Deploy documentation](docs/TROUBLESHOOTING_CDK_DEPLOY.md) for more detailed guidance.
- If you continue to experience issues, please reach out to **ai-cic@amazon.com** for further assistance.

## Additional Resources

For more details on the problem approach, industry impact, and our innovative solution developed by ASU CIC, please visit our blog: [PDF Accessibility Blog](https://smartchallenges.asu.edu/challenges/pdf-accessibility-ohio-state-university)


## PDF-to-HTML Remediation Solution

In addition to the PDF-to-PDF remediation solution above, this repository also includes a PDF-to-HTML conversion solution that transforms PDFs into accessible HTML format using AWS Bedrock Data Automation (BDA).

### Overview

The PDF-to-HTML solution converts PDF documents to accessible HTML format while preserving layout and visual appearance. It leverages AWS Bedrock Data Automation for PDF parsing and processing, and uses a serverless architecture with Lambda and S3 for scalable processing.

### Directory Structure

The PDF-to-HTML solution is contained in the `pdf2html` directory:

```
pdf2html/
├── cdk/ (CDK infrastructure code)
├── content_accessibility_utility_on_aws/ (Core utility package)
├── lambda_function.py (Lambda handler for S3 events)
├── Dockerfile (Container definition for Lambda)
├── deploy.sh (Deployment script)
└── README.md (Detailed documentation)
```

### Prerequisites

Before deploying the PDF-to-HTML solution, ensure you have:

1. **AWS Bedrock Access**: Ensure your AWS account has access to Amazon Bedrock services.
2. **AWS CLI**: Installed and configured with appropriate credentials.
3. **Node.js and npm**: For CDK deployment.
4. **AWS CDK**: Installed globally (`npm install -g aws-cdk`).
5. **Docker**: Installed and running.

### Setup and Deployment

1. **Clone the Repository**:
   - Clone this repository containing the CDK code, Docker configurations, and Lambda functions.

2. **Navigate to the pdf2html directory**:
   ```bash
   cd pdf2html
   ```

3. **Create a Bedrock Data Automation (BDA) Project**:
   ```bash
   aws bedrock-data-automation create-data-automation-project \
       --project-name my-accessibility-project \
       --standard-output-configuration '{"document": {"extraction": {"granularity": {"types": ["DOCUMENT", "PAGE", "ELEMENT"]},"boundingBox": {"state": "ENABLED"}},"generativeField": {"state": "DISABLED"},"outputFormat": {"textFormat": {"types": ["HTML"]},"additionalFileFormat": {"state": "ENABLED"}}}}'
   ```
   - Save the `projectArn` from the output for the next step.

4. **Install Dependencies**:
   ```bash
    cd cdk
    npm install
    cdk bootstrap (if you haven't already / directly deploying pdf-to-html solution)
    cd ..
   ```

5. **Run the Deployment Script**:
   ```bash
   ./deploy.sh --bda-project-arn <your-bda-project-arn>
   ```

   The script will:
   - Create an S3 bucket for the pdf processing
   - Create required folders in the bucket
   - Create an ECR repository 
   - Build and push the Docker image to ECR
   - Deploy the CDK stack with all required resources

   **Optional Parameters**:
   - `--region`: AWS region to deploy to (default: us-east-1)
   - `--stack-name`: Name of the CloudFormation stack (default: Pdf2HtmlStack)
   - `--bucket-name`: Name of the S3 bucket (default: pdf2html-bucket-{account-id}-{region})
   - `--force-redeploy`: Force redeployment by deleting existing stack

6. **Verify Deployment**:
   - The script will output the S3 bucket name, Lambda function name, and other resources created.

### Usage

Once deployed, the PDF-to-HTML solution works as follows:

1. **Upload a PDF file**:
   ```bash
   Upload a pdf file in the uploads/ folder in s3 bucket
   ```

2. **Automatic Processing**:
   - The Lambda function is triggered automatically when a PDF is uploaded
   - The PDF is processed to extract text, layout, and images
   - Accessibility issues are identified and remediated
   - The result is a fully accessible HTML version of the PDF

3. **Access the Results**:
   - Check for remediated files:
     ```bash
     Final output is a zip file inside the remediated folder, download and unzip the file to find remediated.html
     as your remediated html version of the pdf file.
     ```

### Architecture

The PDF-to-HTML solution includes:
- **S3 Bucket**: Stores input PDFs and remediated HTML files
- **Lambda Function**: Processes PDFs using the PDF2HTML utility
- **ECR Repository**: Hosts the Docker image for the Lambda function
- **BDA Project**: Provides PDF parsing, extraction and remediation capabilities

### Limitations

- Preserves layout but may not perfectly match the original PDF appearance
- Complex tables may require additional manual remediation
- Some advanced PDF features (like forms) are converted to static HTML

### Troubleshooting

If you encounter issues with the PDF-to-HTML solution:

- Check the Lambda function logs in CloudWatch Logs:
  ```bash
  aws logs describe-log-groups --log-group-name-prefix /aws/lambda/Pdf2HtmlPipeline
  aws logs get-log-events --log-group-name /aws/lambda/Pdf2HtmlPipeline --log-stream-name <latest-log-stream>
  ```

- Verify S3 bucket permissions:
  ```bash
  aws s3api get-bucket-policy --bucket your-bucket-name
  ```

- Ensure the BDA project was created successfully:
  ```bash
  aws bedrock-data-automation get-data-automation-project --project-arn <your-bda-project-arn>
  ```

- Check that the Docker image was pushed to ECR correctly:
  ```bash
  aws ecr describe-images --repository-name pdf2html-lambda
  ```

## Contributing

Contributions to this project are welcome. Please fork the repository and submit a pull request with your changes.

## Release Notes

See the latest [Release Notes](RELEASE_NOTES.md) for version updates and improvements.
