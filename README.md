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
   - Please checkout Troubleshooting if you would like to know more about this.
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
- If you encounter issues with the 9th step, refer to the related discussion on the AWS CDK GitHub repository for further troubleshooting: [CDK Github Issue](https://github.com/aws/aws-cdk/issues/30258)

## Contributing

Contributions to this project are welcome. Please fork the repository and submit a pull request with your changes