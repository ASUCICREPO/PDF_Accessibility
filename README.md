# PDF Processing AWS Infrastructure

This project builds an AWS infrastructure using AWS CDK (Cloud Development Kit) to split a PDF into chunks, process the chunks via AWS Step Functions, and merge the resulting chunks back using ECS tasks. The infrastructure also includes monitoring via CloudWatch dashboards and metrics for tracking progress.

## Prerequisites

Before running the AWS CDK stack, ensure the following are installed and configured:

1. **AWS Bedrock Access**: Ensure your AWS account has access to the Claude 3.5 model in Amazon Bedrock.
   - Request access through the AWS console if not already enabled

2. **Adobe API Access**: An enterprise-level contract or trial account for Adobe's API is required.
   - Sign up for an Adobe enterprise account or request a trial
   - Obtain the necessary API credentials (key, secret, etc.)

3. **Python**:
   - Install Python (version 3.7 or later)
   - Set up a virtual environment for the project

4. **AWS CLI**: To interact with AWS services and set up credentials.
   - Install AWS CLI

5. **AWS CDK**: For defining cloud infrastructure in code.
   - Install AWS CDK

6. **Docker**: Required to build and run Docker images for the ECS tasks.
   - Install Docker

7. **AWS Account Permissions**: Ensure your AWS account has the necessary permissions to create and manage the required resources (S3, Lambda, Step Functions, ECS, ECR, CloudWatch, etc.)

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

1. **Set Up CDK Environment**:
   - Bootstrap your AWS environment for CDK (run only once per AWS account/region):
     ```
     cdk bootstrap
     ```

2. **Clone the Repository**:
   - Clone this repository containing the CDK code, Docker configurations, and Lambda functions.

3. **Set Up Your Environment**:
   - Configure AWS CLI with your AWS account credentials:
     ```
     aws configure
     ```

4. **Initialize CDK**:
   - Ensure your environment is initialized:
     ```
     cdk init app --language python
     ```

5. **Create Adobe API Credentials**:
   - Create a file called `client_credentials.json` in the root directory with the following structure:
     ```json
     {
       "client_credentials": {
         "PDF_SERVICES_CLIENT_ID": "<Your client ID here>",
         "PDF_SERVICES_CLIENT_SECRET": "<Your secret ID here>"
       }
     }
     ```

6. **Upload Credentials to Secrets Manager**:
   - Run this command in the terminal of the project:
     ```
     aws secretsmanager create-secret \
         --name /myapp/client_credentials \
         --description "Client credentials for PDF services" \
         --secret-string file://client_credentials.json
     ```

7. **Connect to ECR**:
   - Ensure Docker Desktop is running, then execute:
     ```
     aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com
     ```

8. **Deploy the CDK Stack**:
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
