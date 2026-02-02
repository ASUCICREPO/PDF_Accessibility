# IAM Permissions Required for PDF Accessibility Solutions

This document outlines the specific IAM permissions required to deploy and operate each PDF accessibility solution. All permissions follow the **principle of least privilege** with scoped resources.

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
- **Amazon Comprehend** - Language detection

### Runtime Permissions (ECS Task Role)

#### Bedrock Permissions (Scoped to specific models)
```json
{
    "Sid": "BedrockInvokeModel",
    "Effect": "Allow",
    "Action": ["bedrock:InvokeModel"],
    "Resource": [
        "arn:aws:bedrock:${Region}::foundation-model/us.amazon.nova-pro-v1:0",
        "arn:aws:bedrock:${Region}::foundation-model/amazon.nova-pro-v1:0"
    ]
}
```

#### S3 Permissions (Scoped to processing bucket)
```json
{
    "Sid": "S3BucketAccess",
    "Effect": "Allow",
    "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
    ],
    "Resource": [
        "arn:aws:s3:::${BucketName}",
        "arn:aws:s3:::${BucketName}/*"
    ]
}
```

#### Comprehend Permissions
```json
{
    "Sid": "ComprehendLanguageDetection",
    "Effect": "Allow",
    "Action": ["comprehend:DetectDominantLanguage"],
    "Resource": "*"
}
```
> **Note:** Comprehend's `DetectDominantLanguage` action does not support resource-level permissions.

#### Secrets Manager Permissions (Scoped to app secrets)
```json
{
    "Sid": "SecretsManagerAccess",
    "Effect": "Allow",
    "Action": ["secretsmanager:GetSecretValue"],
    "Resource": "arn:aws:secretsmanager:${Region}:${AccountId}:secret:/myapp/*"
}
```

### Lambda Function Permissions

#### Title Generator Lambda - Bedrock Access
```json
{
    "Sid": "BedrockInvokeModel",
    "Effect": "Allow",
    "Action": ["bedrock:InvokeModel"],
    "Resource": [
        "arn:aws:bedrock:${Region}::foundation-model/us.amazon.nova-pro-v1:0",
        "arn:aws:bedrock:${Region}::foundation-model/amazon.nova-pro-v1:0"
    ]
}
```

#### CloudWatch Metrics (All Lambdas)
```json
{
    "Sid": "CloudWatchMetrics",
    "Effect": "Allow",
    "Action": ["cloudwatch:PutMetricData"],
    "Resource": "*"
}
```
> **Note:** CloudWatch `PutMetricData` does not support resource-level permissions.

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

### Runtime Permissions (Lambda Role)

#### S3 Permissions (Scoped to processing bucket)
```json
{
    "Sid": "S3BucketAccess",
    "Effect": "Allow",
    "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket",
        "s3:DeleteObject",
        "s3:DeleteObjects",
        "s3:ListObjects",
        "s3:ListObjectsV2",
        "s3:GetBucketLocation",
        "s3:GetObjectVersion",
        "s3:GetBucketPolicy"
    ],
    "Resource": [
        "arn:aws:s3:::${BucketName}",
        "arn:aws:s3:::${BucketName}/*"
    ]
}
```

#### Bedrock Model Invocation (Scoped to specific models)
```json
{
    "Sid": "BedrockModelInvocation",
    "Effect": "Allow",
    "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
    ],
    "Resource": [
        "arn:aws:bedrock:${Region}::foundation-model/us.amazon.nova-lite-v1:0",
        "arn:aws:bedrock:${Region}::foundation-model/amazon.nova-lite-v1:0",
        "arn:aws:bedrock:${Region}::foundation-model/us.amazon.nova-pro-v1:0",
        "arn:aws:bedrock:${Region}::foundation-model/amazon.nova-pro-v1:0"
    ]
}
```

#### Bedrock Data Automation (Scoped to project)
```json
{
    "Sid": "BedrockDataAutomation",
    "Effect": "Allow",
    "Action": [
        "bedrock:InvokeDataAutomationAsync",
        "bedrock:GetDataAutomationStatus",
        "bedrock:GetDataAutomationProject"
    ],
    "Resource": [
        "${BdaProjectArn}",
        "arn:aws:bedrock:${Region}:${AccountId}:data-automation-invocation/*",
        "arn:aws:bedrock:${Region}:${AccountId}:data-automation-profile/*"
    ]
}
```

#### CloudWatch Logs (Scoped to Lambda log group)
```json
{
    "Sid": "CloudWatchLogs",
    "Effect": "Allow",
    "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
    ],
    "Resource": "arn:aws:logs:${Region}:${AccountId}:log-group:/aws/lambda/Pdf2HtmlPipeline:*"
}
```

---

## Deployment Permissions (CodeBuild Role)

The CodeBuild role requires permissions to deploy CDK stacks. These are scoped to specific resource patterns.

### PDF-to-PDF Deployment

#### S3 (CDK and Application Buckets)
```json
{
    "Sid": "S3CDKAndBucketAccess",
    "Effect": "Allow",
    "Action": [
        "s3:CreateBucket",
        "s3:DeleteBucket",
        "s3:PutBucketPolicy",
        "s3:GetBucketPolicy",
        "s3:DeleteBucketPolicy",
        "s3:PutBucketPublicAccessBlock",
        "s3:GetBucketPublicAccessBlock",
        "s3:PutEncryptionConfiguration",
        "s3:GetEncryptionConfiguration",
        "s3:PutBucketVersioning",
        "s3:GetBucketVersioning",
        "s3:PutBucketCORS",
        "s3:GetBucketCORS",
        "s3:PutBucketNotification",
        "s3:GetBucketNotification",
        "s3:PutBucketTagging",
        "s3:GetBucketTagging",
        "s3:GetBucketLocation",
        "s3:ListBucket",
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:GetObjectVersion",
        "s3:DeleteObjectVersion",
        "s3:ListBucketVersions"
    ],
    "Resource": [
        "arn:aws:s3:::cdk-*",
        "arn:aws:s3:::cdk-*/*",
        "arn:aws:s3:::pdfaccessibility*",
        "arn:aws:s3:::pdfaccessibility*/*"
    ]
}
```

#### IAM (Scoped to stack-specific roles)
```json
{
    "Sid": "IAMRoleAndPolicyAccess",
    "Effect": "Allow",
    "Action": [
        "iam:CreateRole",
        "iam:DeleteRole",
        "iam:GetRole",
        "iam:UpdateRole",
        "iam:PassRole",
        "iam:AttachRolePolicy",
        "iam:DetachRolePolicy",
        "iam:PutRolePolicy",
        "iam:GetRolePolicy",
        "iam:DeleteRolePolicy",
        "iam:ListRolePolicies",
        "iam:ListAttachedRolePolicies",
        "iam:TagRole",
        "iam:UntagRole",
        "iam:ListRoleTags",
        "iam:UpdateAssumeRolePolicy"
    ],
    "Resource": [
        "arn:aws:iam::*:role/PDFAccessibility*",
        "arn:aws:iam::*:role/cdk-*"
    ]
}
```

#### CloudFormation (Scoped to stack names)
```json
{
    "Sid": "CloudFormationStackAccess",
    "Effect": "Allow",
    "Action": [
        "cloudformation:CreateStack",
        "cloudformation:DeleteStack",
        "cloudformation:UpdateStack",
        "cloudformation:DescribeStacks",
        "cloudformation:DescribeStackEvents",
        "cloudformation:DescribeStackResources",
        "cloudformation:GetTemplate",
        "cloudformation:GetTemplateSummary",
        "cloudformation:ListStacks",
        "cloudformation:ValidateTemplate",
        "cloudformation:CreateChangeSet",
        "cloudformation:DeleteChangeSet",
        "cloudformation:DescribeChangeSet",
        "cloudformation:ExecuteChangeSet",
        "cloudformation:ListChangeSets"
    ],
    "Resource": [
        "arn:aws:cloudformation:*:*:stack/PDFAccessibility*/*",
        "arn:aws:cloudformation:*:*:stack/CDKToolkit/*"
    ]
}
```

---

## Security Considerations

### Principle of Least Privilege
All IAM policies in this solution follow the principle of least privilege:
- **Actions** are limited to only those required for the specific operation
- **Resources** are scoped to specific ARN patterns where possible
- **Wildcards** are only used where AWS does not support resource-level permissions

### Services Without Resource-Level Permissions
The following actions require `Resource: "*"` because AWS does not support resource-level permissions:
- `cloudwatch:PutMetricData`
- `comprehend:DetectDominantLanguage`
- `ecr:GetAuthorizationToken`
- `sts:GetCallerIdentity`
- EC2 VPC-related actions (describe operations)
- ECS cluster and task definition operations

### Sensitive Data Protection
- Adobe API credentials are stored securely in AWS Secrets Manager at `/myapp/client_credentials`
- All S3 buckets use server-side encryption (SSE-S3)
- VPC configuration isolates ECS tasks in private subnets (PDF-to-PDF solution)
- IAM roles are scoped to specific resource patterns

### Monitoring and Auditing
- CloudWatch logs capture all function executions
- CloudTrail can be enabled for API call auditing
- Custom CloudWatch dashboards provide operational visibility

---

## Troubleshooting Permission Issues

### Common Permission Errors

1. **CDK Bootstrap Failures**: Ensure CloudFormation and S3 permissions for `cdk-*` resources
2. **ECR Push Failures**: Verify ECR repository permissions and `ecr:GetAuthorizationToken`
3. **Lambda Deployment Failures**: Check Lambda and IAM role creation permissions
4. **Step Function Execution Failures**: Verify Step Functions and ECS permissions
5. **Bedrock Access Denied**: Ensure Bedrock model access is enabled in the console and IAM policy includes the correct model ARNs

### Permission Validation
Before deployment, verify your AWS credentials have the required permissions:
```bash
aws sts get-caller-identity
aws iam get-user
aws bedrock list-foundation-models --region your-region
```

### Model ARN Formats
When scoping Bedrock permissions, use the correct ARN format:
- Foundation models: `arn:aws:bedrock:${Region}::foundation-model/${ModelId}`
- Data automation projects: `arn:aws:bedrock:${Region}:${AccountId}:data-automation-project/${ProjectId}`
- Data automation invocations: `arn:aws:bedrock:${Region}:${AccountId}:data-automation-invocation/${JobId}`
