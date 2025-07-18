# PDF Accessibility Solutions

This repository provides two complementary solutions for PDF accessibility:

1. **PDF-to-PDF Remediation**: The solution that processes PDFs and maintains the PDF format while improving accessibility.
2. **PDF-to-HTML Remediation**: A newer solution that converts PDFs to accessible HTML format.

Both solutions leverage AWS services and generative AI to improve content accessibility according to WCAG 2.1 Level AA standards.

## PDF-to-PDF Processing AWS Infrastructure

This project builds an AWS infrastructure using AWS CDK (Cloud Development Kit) to split a PDF into chunks, process the chunks via AWS Step Functions, and merge the resulting chunks back using ECS tasks. The infrastructure also includes monitoring via CloudWatch dashboards and metrics for tracking progress.

## Prerequisites

Before running the AWS CDK stack, ensure the following are installed and configured:

1. **AWS Bedrock Access**: Ensure your AWS account has access to the Nova pro model in Amazon Bedrock.
   - [Request access to Amazon Bedrock](https://console.aws.amazon.com/bedrock/) through the AWS console if not already enabled.

2. **Adobe API Access** - An enterprise-level contract or a trial account (For Testing) for Adobe's API is required.

   - [Adobe PDF Services API](https://acrobatservices.adobe.com/dc-integration-creation-app-cdn/main.html) to obtain API credentials.
   
4. **Python (3.7 or later)**  
   - [Download Python](https://www.python.org/downloads/)  
   - [Set up a virtual environment](https://docs.python.org/3/library/venv.html)  
     ```bash
     python -m venv .venv
     source .venv/bin/activate  # For macOS/Linux
     .venv\Scripts\activate     # For Windows
     ```
   - Also ensure that if you are using windows to confirm the python path in cmd before deploying. That can be done by running:
     ```bash
     where python
     ```

5. **AWS CLI**: To interact with AWS services and set up credentials.

   - [Install AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html)
     
6. **npm**  
   - npm is required to install AWS CDK. Install npm by installing Node.js:  
     - [Download Node.js](https://nodejs.org/) (includes npm).  
   - Verify npm installation:  
     ```bash
     npm --version
     ```
7. **AWS CDK**: For defining cloud infrastructure in code.
   - [Install AWS CDK](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html)  
     ```bash
     npm install -g aws-cdk
     ```

8. **Docker**: Required to build and run Docker images for the ECS tasks.  
   - [Install Docker](https://docs.docker.com/get-docker/)  
   - Verify installation:  
     ```bash
     docker --version
     ```

9. **AWS Account Permissions**  
   - Ensure permissions to create and manage AWS resources like S3, Lambda, ECS, ECR, Step Functions, and CloudWatch.  
   - [AWS IAM Policies and Permissions](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies.html)
   - Also, For the ease of deployment. Create a IAM user in the account you want to deploy to and attach adminstrator access to that user and use the Access key and Secret key for that user.

## Directory Structure

Ensure your project has the following structure:

```
├── app.py (Main CDK app)
├── lambda/
│   ├── split_pdf/ (Python Lambda for splitting PDF)
│   └── java_lambda/ (Java Lambda for merging PDFs)
├── docker_autotag/ (Python Docker image for ECS task)
└── javascript_docker/ (JavaScript Docker image for ECS task)
|__ client_credentials.json (The client id and client secret id for adobe)
```

## Setup and Deployment

1. **Clone the Repository**:
   - Clone this repository containing the CDK code, Docker configurations, and Lambda functions.
     
2. **Set Up Your Environment**:
   - Configure AWS CLI with your AWS account credentials:
     ```bash
     aws configure
     ```
   - Make sure the region is set to
     ```
     us-east-1
     ```
     
3. **Set Up CDK Environment**:
   - Bootstrap your AWS environment for CDK (run only once per AWS account/region):
     ```
     cdk bootstrap
     ```
     
4. **Create Adobe API Credentials**:
   - Create a file called `client_credentials.json` in the root directory with the following structure:
     ```json
     {
       "client_credentials": {
         "PDF_SERVICES_CLIENT_ID": "<Your client ID here>",
         "PDF_SERVICES_CLIENT_SECRET": "<Your secret ID here>"
       }
     }
     ```
   - Replace <Your Client ID here> and <Your Secret ID here> with your actual Client ID and Client Secret provided by Adobe and not the whole file.

5. **Upload Credentials to Secrets Manager**:
   - Run this command in the terminal of the project to push the secret keys to secret manager:
   - For Mac
     ```
     aws secretsmanager create-secret \
         --name /myapp/client_credentials \
         --description "Client credentials for PDF services" \
         --secret-string file://client_credentials.json
     ```
   - For Windows
     ```bash
     aws secretsmanager create-secret --name /myapp/client_credentials --description "Client credentials for PDF services" --secret-string file://client_credentials.json
     ```
   - Run this command if you have already uploaded the keys earlier and would like to update the keys in secret manager.
   - For Mac:
     ```
        aws secretsmanager update-secret \
       --secret-id /myapp/client_credentials \
       --description "Updated client credentials for PDF services" \
       --secret-string file://client_credentials.json
     ```
   - For Windows:
     ```bash
     aws secretsmanager update-secret --secret-id /myapp/client_credentials --description "Updated client credentials for PDF services" --secret-string file://client_credentials.json
     ```
6. **Install the Requirements**:
   - For both Mac and Windows
   - ```bash
     pip install -r requirements.txt
     ```
   
8. **Connect to ECR**:
   - Ensure Docker Desktop is running, then execute:
     ```
     aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com
     ```
  
9. **Set a environment variable once for deployment**
   - An environment variable needs to be set before deployment. This step ensures compatibility and prevents deployment issues.
   - For additional guidance or if you encounter any deployment issues, please refer to [Troubleshooting](#troubleshooting) section.
   - For Mac,
     ```
     export BUILDX_NO_DEFAULT_ATTESTATIONS=1   
     ```
   - For Windows,
     ```
     set BUILDX_NO_DEFAULT_ATTESTATIONS=1
     ```
  
10. **Deploy the CDK Stack**:
   - Deploy the stack to AWS:
     ```
     cdk deploy
     ```

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
- If you encounter issues with the 9th step, refer to the related discussion on the AWS CDK GitHub repository for further troubleshooting: [CDK Github Issue](https://github.com/aws/aws-cdk/issues/30258). You can also consult our [Troubleshooting CDK Deploy documentation](TROUBLESHOOTING_CDK_DEPLOY.md) for more detailed guidance.
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
