# PDF Processing AWS Infrastructure

This project builds an AWS infrastructure using AWS CDK (Cloud Development Kit) to split a PDF into chunks, process the chunks via AWS Step Functions, and merge the resulting chunks back using ECS tasks. The infrastructure also includes monitoring via CloudWatch dashboards and metrics for tracking progress.

## Prerequisites

Before running the AWS CDK stack, ensure the following are installed and configured:

1. **AWS Bedrock Access**: Ensure your AWS account has access to the Claude Sonnet 3.5 V2 model in Amazon Bedrock.
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

5. **AWS CLI**: To interact with AWS services and set up credentials.

   - [Install AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html)  

6. **AWS CDK**: For defining cloud infrastructure in code.
   - [Install AWS CDK](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html)  
     ```bash
     npm install -g aws-cdk
     ```

7. **Docker**: Required to build and run Docker images for the ECS tasks.  
   - [Install Docker](https://docs.docker.com/get-docker/)  
   - Verify installation:  
     ```bash
     docker --version
     ```

8. **AWS Account Permissions**  
   - Ensure permissions to create and manage AWS resources like S3, Lambda, ECS, ECR, Step Functions, and CloudWatch.  
   - [AWS IAM Policies and Permissions](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies.html)

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
     ```
     aws configure
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

5. **Upload Credentials to Secrets Manager**:
   - Run this command in the terminal of the project:
     ```
     aws secretsmanager create-secret \
         --name /myapp/client_credentials \
         --description "Client credentials for PDF services" \
         --secret-string file://client_credentials.json
     ```

6. **Connect to ECR**:
   - Ensure Docker Desktop is running, then execute:
     ```
     aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com
     ```

7. **Deploy the CDK Stack**:
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

## Contributing

Contributions to this project are welcome. Please fork the repository and submit a pull request with your changes
