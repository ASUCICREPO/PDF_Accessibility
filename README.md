# PDF Accessibility Pipeline using AWS CDK

This project implements a serverless architecture for processing and enhancing the accessibility of PDF files, leveraging AWS services such as Lambda, Step Functions, ECS, S3, and CloudWatch. The pipeline automatically tags PDF files with accessibility metadata and generates alternative text for images and links using Large Language Models (LLM).

## Architecture Overview

1. **S3 Bucket**: Stores the PDF files to be processed.
2. **Lambda Functions**: 
   - **Split PDF Lambda**: Splits large PDF files into smaller chunks and triggers further processing.
   - **Java Lambda (PDF Merger)**: Merges processed chunks back into a single PDF.
3. **ECS Tasks**: 
   - **Task 1 (Adobe Autotag & Extract)**: Adds tags to improve PDF accessibility.
   - **Task 2 (LLM Alt Text Generation)**: Generates alternative text for images in the PDF.
4. **Step Functions**: Orchestrates the entire workflow from splitting the PDF to generating accessibility metadata and merging the results.
5. **CloudWatch Dashboard**: Monitors the entire process, with logs and metrics displayed for easy debugging and tracking.

## Key Components

### AWS CDK (Cloud Development Kit)

This project is built using AWS CDK (Python), which allows you to define your cloud infrastructure as code.

### Services Used

- **S3**: For storing PDFs and processing results.
- **Lambda**: To handle splitting and merging PDFs.
- **ECS (Fargate)**: For running Docker containers that perform autotagging and alt text generation.
- **Step Functions**: To orchestrate the workflow.
- **Secrets Manager**: To store sensitive information securely.
- **CloudWatch**: For logging and monitoring.
- **Adobe API**: For autotagging.


### Installation

1. Clone the repository:
git clone git@github.com:ASUCICREPO/PDF_Accessibility.git

2. Bootstrap your AWS environment (if not already done)

3. Build and deploy the CDK stack:
cdk deploy

## Monitoring and Logs

CloudWatch Logs and Metrics are configured for all Lambda functions, ECS tasks, and Step Functions. The logs are visible in the CloudWatch console, and a custom dashboard is created to track the status of files and the overall workflow.

## Contributions

Contributions are welcome! Please submit pull requests or open issues for any changes or enhancements.

