# IAM Permissions Required for PDF Accessibility Solutions

This document outlines the specific IAM permissions required to deploy and operate each PDF accessibility solution.

## PDF-to-PDF Remediation Solution

### Required AWS Services
- **Amazon S3** - File storage and processing
- **AWS Lambda** - Serverless compute functions
- **Amazon ECS** - Containerized processing tasks
- **Amazon ECR** - Container image registry
- **AWS Step Functions** - Workflow orchestration
- **Amazon EC2** - VPC and networking infrastructure
- **AWS IAM** - Role and policy management
- **AWS CloudFormation** - Infrastructure deployment
- **Amazon Bedrock** - AI/ML model access
- **AWS Secrets Manager** - Adobe API credentials storage
- **Amazon CloudWatch** - Monitoring and logging
- **AWS Systems Manager** - Parameter storage

### Detailed IAM Permissions

#### S3 Permissions
```json
{
    "Sid": "S3FullAccess",
    "Effect": "Allow",
    "Action": ["s3:*"],
    "Resource": "*"
}
```

#### ECR Permissions
```json
{
    "Sid": "ECRFullAccess",
    "Effect": "Allow",
    "Action": ["ecr:*"],
    "Resource": "*"
}
```

#### Lambda Permissions
```json
{
    "Sid": "LambdaFullAccess",
    "Effect": "Allow",
    "Action": ["lambda:*"],
    "Resource": "*"
}
```

#### ECS Permissions
```json
{
    "Sid": "ECSFullAccess",
    "Effect": "Allow",
    "Action": ["ecs:*"],
    "Resource": "*"
}
```

#### EC2 Permissions
```json
{
    "Sid": "EC2FullAccess",
    "Effect": "Allow",
    "Action": ["ec2:*"],
    "Resource": "*"
}
```

#### Step Functions Permissions
```json
{
    "Sid": "StepFunctionsFullAccess",
    "Effect": "Allow",
    "Action": ["states:*"],
    "Resource": "*"
}
```

#### IAM Permissions
```json
{
    "Sid": "IAMFullAccess",
    "Effect": "Allow",
    "Action": ["iam:*"],
    "Resource": "*"
}
```

#### CloudFormation Permissions
```json
{
    "Sid": "CloudFormationFullAccess",
    "Effect": "Allow",
    "Action": ["cloudformation:*"],
    "Resource": "*"
}
```

#### Bedrock Permissions
```json
{
    "Sid": "BedrockFullAccess",
    "Effect": "Allow",
    "Action": [
        "bedrock:*",
        "bedrock-data-automation:*",
        "bedrock-data-automation-runtime:*"
    ],
    "Resource": "*"
}
```

#### CloudWatch Permissions
```json
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
}
```

#### Secrets Manager Permissions
```json
{
    "Sid": "SecretsManagerFullAccess",
    "Effect": "Allow",
    "Action": ["secretsmanager:*"],
    "Resource": "*"
}
```

#### STS Permissions
```json
{
    "Sid": "STSAccess",
    "Effect": "Allow",
    "Action": [
        "sts:GetCallerIdentity",
        "sts:AssumeRole"
    ],
    "Resource": "*"
}
```

#### Systems Manager Permissions
```json
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
```

---

## PDF-to-HTML Remediation Solution

### Required AWS Services
- **Amazon S3** - File storage and processing
- **AWS Lambda** - Serverless compute functions
- **Amazon ECR** - Container image registry
- **AWS IAM** - Role and policy management
- **AWS CloudFormation** - Infrastructure deployment
- **Amazon Bedrock** - AI/ML model access and Data Automation
- **Amazon CloudWatch** - Monitoring and logging
- **AWS Systems Manager** - Parameter storage

### Detailed IAM Permissions

#### S3 Permissions
```json
{
    "Sid": "S3FullAccess",
    "Effect": "Allow",
    "Action": ["s3:*"],
    "Resource": "*"
}
```

#### ECR Permissions
```json
{
    "Sid": "ECRFullAccess",
    "Effect": "Allow",
    "Action": ["ecr:*"],
    "Resource": "*"
}
```

#### Lambda Permissions
```json
{
    "Sid": "LambdaFullAccess",
    "Effect": "Allow",
    "Action": ["lambda:*"],
    "Resource": "*"
}
```

#### IAM Permissions
```json
{
    "Sid": "IAMFullAccess",
    "Effect": "Allow",
    "Action": ["iam:*"],
    "Resource": "*"
}
```

#### CloudFormation Permissions
```json
{
    "Sid": "CloudFormationFullAccess",
    "Effect": "Allow",
    "Action": ["cloudformation:*"],
    "Resource": "*"
}
```

#### Bedrock Permissions
```json
{
    "Sid": "BedrockFullAccess",
    "Effect": "Allow",
    "Action": [
        "bedrock:*",
        "bedrock-data-automation:*",
        "bedrock-data-automation-runtime:*"
    ],
    "Resource": "*"
}
```

#### CloudWatch Logs Permissions
```json
{
    "Sid": "CloudWatchLogsFullAccess",
    "Effect": "Allow",
    "Action": ["logs:*"],
    "Resource": "*"
}
```

#### STS Permissions
```json
{
    "Sid": "STSAccess",
    "Effect": "Allow",
    "Action": [
        "sts:GetCallerIdentity",
        "sts:AssumeRole"
    ],
    "Resource": "*"
}
```

#### Systems Manager Permissions
```json
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
```

---

## Runtime Permissions

### PDF-to-PDF Solution Runtime Roles

#### ECS Task Role Permissions
- **Bedrock**: Full access for AI model inference
- **S3**: Read/write access to processing bucket
- **Secrets Manager**: Read access to Adobe API credentials

#### Lambda Function Permissions
- **S3**: Read/write access to processing bucket
- **Step Functions**: Start execution permissions
- **Bedrock**: Full access for AI model inference
- **CloudWatch**: Metrics and logging permissions
- **Secrets Manager**: Read access to Adobe API credentials

### PDF-to-HTML Solution Runtime Roles

#### Lambda Function Permissions
- **S3**: Read/write access to processing bucket
- **Bedrock**: Full access including Data Automation
- **CloudWatch**: Logging permissions

---

## Security Considerations

### Sensitive Data Protection
- Adobe API credentials are stored securely in AWS Secrets Manager
- All S3 buckets use server-side encryption
- VPC configuration isolates ECS tasks in private subnets (PDF-to-PDF solution)

### Monitoring and Auditing
- CloudWatch logs capture all function executions
- CloudTrail can be enabled for API call auditing
- Custom CloudWatch dashboards provide operational visibility

---

## Troubleshooting Permission Issues

### Common Permission Errors

1. **CDK Bootstrap Failures**: Ensure CloudFormation and S3 permissions
2. **ECR Push Failures**: Verify ECR repository permissions and Docker login
3. **Lambda Deployment Failures**: Check Lambda and IAM role creation permissions
4. **Step Function Execution Failures**: Verify Step Functions and ECS permissions
5. **Bedrock Access Denied**: Ensure Bedrock model access is enabled in the console

### Permission Validation
Before deployment, verify your AWS credentials have the required permissions by running:
```bash
aws sts get-caller-identity
aws iam get-user
aws bedrock list-foundation-models --region your-region
```
