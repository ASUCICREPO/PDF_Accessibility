# IAM Permissions Required for PDF Accessibility Solutions

This document outlines the IAM permissions required to deploy and operate each PDF accessibility solution.

Deployment policies are maintained as standalone JSON files in [`policies/`](../policies/):

| File | Type | Purpose |
|------|------|---------|
| [`deploy-policy.json`](../policies/deploy-policy.json) | Identity policy | Must be manually attached to the IAM user/role running `deploy.sh` |
| [`pdf2pdf-codebuild-policy.json`](../policies/pdf2pdf-codebuild-policy.json) | Identity policy | Loaded by `deploy.sh` and attached to the CodeBuild service role (pdf2pdf) |
| [`pdf2html-codebuild-policy.json`](../policies/pdf2html-codebuild-policy.json) | Identity policy | Loaded by `deploy.sh` and attached to the CodeBuild service role (pdf2html) |
| [`codebuild-trust-policy.json`](../policies/codebuild-trust-policy.json) | Trust policy | Loaded by `deploy.sh` when creating the CodeBuild service role |

The policy files are written for the commercial partition (`arn:aws:`). `deploy.sh` detects the partition of the account it runs in and rewrites the ARNs automatically (e.g. to `arn:aws-us-gov:` in AWS GovCloud) before creating the CodeBuild policies. The caller policy is attached by hand, so it must be rewritten by hand — see [AWS GovCloud](#aws-govcloud).

Validate any policy with:
```bash
aws accessanalyzer validate-policy \
  --policy-document file://policies/pdf2pdf-codebuild-policy.json \
  --policy-type IDENTITY_POLICY
```

---

## Caller Permissions (User Running `deploy.sh`)

The user or role that runs `deploy.sh` makes AWS API calls *before* CodeBuild starts. This includes both the backend deploy script and the UI deploy script (from the [PDF_accessability_UI](https://github.com/ASUCICREPO/PDF_accessability_UI) repo). Users with `AdministratorAccess` already have everything below.

See [`policies/deploy-policy.json`](../policies/deploy-policy.json) for the full document.

| Sid | Actions | Resources | Purpose |
|-----|---------|-----------|---------|
| CloudShellAccess | `cloudshell:*` | `*` | Access AWS CloudShell environment |
| STSAccess | `sts:GetCallerIdentity` | `*` | Verify AWS credentials and detect the partition |
| SecretsManagerAccess | `secretsmanager:CreateSecret`, `UpdateSecret` | `secret:/myapp/*` | Store Adobe API credentials (pdf2pdf only) |
| BedrockDataAutomationAccess | `bedrock:CreateDataAutomationProject` | `*` | Create BDA project (pdf2html only) |
| BedrockModelAccessCheck | `bedrock:InvokeModel` | `inference-profile/*openai.gpt-5.6-luna`, `foundation-model/openai.gpt-5.6-luna` | Pre-deployment check that the model is enabled in the region |
| IAMRoleManagement | `iam:GetRole`, `CreateRole` | `role/pdfremediation-*-codebuild-service-role`, `role/pdf-ui-*-service-role` | Create CodeBuild service roles (backend + UI) |
| IAMPolicyManagement | `iam:CreatePolicy`, `GetPolicy` | `policy/pdfremediation-*` | Create the backend CodeBuild policy from `policies/` |
| IAMAttachOwnPolicyToCodeBuildRole | `iam:AttachRolePolicy` | `role/pdfremediation-*-codebuild-service-role` (conditioned on `iam:PolicyARN`: `policy/pdfremediation-*`) | Attach only that policy to the backend CodeBuild role |
| IAMUIRoleInlinePolicy | `iam:PutRolePolicy` | `role/pdf-ui-*-service-role` | Inline policy for the UI CodeBuild role |
| IAMPassRoleToCodeBuild | `iam:PassRole` | `role/pdfremediation-*-codebuild-service-role`, `role/pdf-ui-*-service-role` (conditioned on `iam:PassedToService`: codebuild) | Pass role to CodeBuild projects |
| CodeBuildAccess | `codebuild:CreateProject`, `StartBuild`, `BatchGetBuilds` | `project/pdfremediation-*`, `project/pdf-ui-*` | Create and monitor CodeBuild projects (backend + UI) |
| CloudWatchLogsAccess | `logs:DescribeLogStreams`, `GetLogEvents`, `FilterLogEvents` | `log-group:/aws/codebuild/*` | Show build errors on failure |
| CloudFormationReadAccess | `cloudformation:DescribeStacks`, `ListStacks` | `*` | Retrieve stack outputs (bucket names, Cognito IDs, Amplify URLs) |
| S3ListBuckets | `s3:ListAllMyBuckets` | `*` | Find deployed bucket by name pattern |

---

## Deployment Permissions (CodeBuild Role)

The deploy script (`deploy.sh`) creates a CodeBuild service role and attaches a scoped IAM policy. The trust policy and identity policies are read from the `policies/` directory.

The CodeBuild role does **not** create the application resources (VPC, ECS, Lambda, Step Functions, IAM roles, etc.) itself. `cdk deploy` assumes the CDK bootstrap roles (`cdk-*-deploy-role`, `cdk-*-file-publishing-role`, `cdk-*-image-publishing-role`), and CloudFormation creates the stack resources with the bootstrap `cdk-*-cfn-exec-role`. The CodeBuild role therefore only needs to:

1. Write its own build logs.
2. Run `cdk bootstrap`, which creates or updates the `CDKToolkit` stack (an S3 bucket, an ECR repository, IAM roles and an SSM parameter, all named `cdk-*`).
3. Assume the CDK bootstrap roles for `cdk deploy`.
4. (PDF-to-HTML only) Create the S3 bucket and ECR repository and push the Lambda image, which the buildspec does before running CDK.

### PDF-to-PDF Deployment Policy

See [`policies/pdf2pdf-codebuild-policy.json`](../policies/pdf2pdf-codebuild-policy.json) for the full document.

| Sid | Actions | Resources | Purpose |
|-----|---------|-----------|---------|
| CodeBuildLogs | `logs:CreateLogGroup`, `CreateLogStream`, `PutLogEvents` | `log-group:/aws/codebuild/pdfremediation-*` | CodeBuild build logs |
| STSIdentity | `sts:GetCallerIdentity` | `*` | Resolve account for CDK |
| AssumeCDKBootstrapRoles | `sts:AssumeRole` | `role/cdk-*` | `cdk deploy` via the bootstrap roles |
| CloudFormationStacks | `cloudformation:*` | `stack/CDKToolkit/*`, `stack/PDFAccessibility*/*` | Bootstrap stack; app stack if CDK falls back to the build role's own credentials |
| CDKBootstrapBucket | `s3:*` | `cdk-*` | CDK assets bucket (bootstrap) |
| CDKBootstrapRepository | `ecr:*` | `repository/cdk-*` | CDK container assets repository (bootstrap) |
| ECRAuth | `ecr:GetAuthorizationToken` | `*` | Docker login to ECR |
| CDKBootstrapRoles | 14 IAM role actions | `role/cdk-*` | Create/update bootstrap roles |
| PassCDKExecutionRoleToCloudFormation | `iam:PassRole` | `role/cdk-*-cfn-exec-role-*` (conditioned on `iam:PassedToService`: cloudformation) | Pass the CDK execution role to CloudFormation |
| CDKBootstrapVersionParameter | `ssm:GetParameter`, `GetParameters`, `PutParameter`, `DeleteParameter` | `parameter/cdk-bootstrap/*` | CDK bootstrap version parameter |
| CodeConnectionsAccess | `codeconnections:GetConnectionToken`, `GetConnection`, `UseConnection` | `connection/*` (any partition) | Only used if the account has a GitHub source credential configured through CodeConnections |

### PDF-to-HTML Deployment Policy

See [`policies/pdf2html-codebuild-policy.json`](../policies/pdf2html-codebuild-policy.json) for the full document.

Same as PDF-to-PDF, except:

| Sid | Actions | Resources | Purpose |
|-----|---------|-----------|---------|
| CloudFormationStacks | `cloudformation:*` | `stack/CDKToolkit/*`, `stack/Pdf2HtmlStack/*` | Bootstrap stack and app stack |
| S3Buckets | `s3:*` | `cdk-*`, `pdf2html-bucket-*` | CDK assets bucket and the application bucket created by the buildspec |
| ECRRepositories | `ecr:*` | `repository/cdk-*`, `repository/pdf2html-lambda` | CDK assets repository and the Lambda image repository created by the buildspec |

---

## AWS GovCloud

The solutions deploy to AWS GovCloud (US) with the same `deploy.sh`. Partition-specific ARNs, Bedrock inference profile IDs and the BDA profile ARN are derived from the region at deploy and run time.

Before deploying:

1. **Caller policy** — if you are not using an administrator role, rewrite the partition in the caller policy before attaching it:
   ```bash
   sed "s/arn:aws:/arn:aws-us-gov:/g" policies/deploy-policy.json > /tmp/deploy-policy.json
   aws iam create-policy --policy-name pdf-accessibility-deploy \
     --policy-document file:///tmp/deploy-policy.json
   ```
   Then attach the policy to the user or role that runs `deploy.sh`.
2. **Bedrock model access** — confirm the models used by the solution are available and enabled:
   ```bash
   aws bedrock list-inference-profiles --region us-gov-west-1 \
     --query 'inferenceProfileSummaries[?contains(inferenceProfileId, `gpt-5.6-luna`)].inferenceProfileId'
   ```
   The solutions default to `us-gov.openai.gpt-5.6-luna` in GovCloud. To use different IDs, set these environment variables:
   - `BEDROCK_MODEL_ID` on the title generator Lambda (pdf2pdf) and on the `Pdf2HtmlPipeline` Lambda (pdf2html).
   - `BEDROCK_MODEL_ID_ALT_TEXT` and `BEDROCK_MODEL_ID_LINK_ALT_TEXT` on the alt-text ECS task (pdf2pdf).
3. **BDA profile (PDF-to-HTML)** — the default is `arn:aws-us-gov:bedrock:<region>:<account>:data-automation-profile/us-gov.data-automation-v1`. To override it, set `BDA_PROFILE_ARN` on the `Pdf2HtmlPipeline` Lambda.
4. **Frontend UI** — not available in GovCloud. AWS Amplify Hosting is not offered there, so `deploy.sh` skips the UI option. Upload PDFs directly to the S3 buckets instead.

---

## Runtime Permissions — PDF-to-PDF

These permissions are created by the CDK stack (`app.py`) and attached to roles at processing time.

### Required AWS Services
- Amazon S3 — File storage and processing
- AWS Lambda — Serverless compute (PDF splitter, merger, title generator, accessibility checkers)
- Amazon ECS (Fargate) — Containerized processing (Adobe Autotag, Alt-Text Generator)
- Amazon ECR — Container image registry
- AWS Step Functions — Workflow orchestration
- Amazon EC2 — VPC and networking infrastructure
- Amazon Bedrock — AI/ML model invocation
- AWS Secrets Manager — Adobe API credentials storage
- Amazon CloudWatch — Monitoring, logging, and dashboards
- Amazon Comprehend — Language detection

### ECS Task Role

```json
{
  "Statement": [
    {
      "Sid": "BedrockInvokeModel",
      "Effect": "Allow",
      "Action": ["bedrock:InvokeModel"],
      "Resource": "*"
    },
    {
      "Sid": "S3BucketAccess",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
      "Resource": ["arn:${Partition}:s3:::${BucketName}", "arn:${Partition}:s3:::${BucketName}/*"]
    },
    {
      "Sid": "ComprehendLanguageDetection",
      "Effect": "Allow",
      "Action": ["comprehend:DetectDominantLanguage"],
      "Resource": "*"
    },
    {
      "Sid": "SecretsManagerAccess",
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue"],
      "Resource": "arn:${Partition}:secretsmanager:${Region}:${AccountId}:secret:/myapp/*"
    }
  ]
}
```

> The ECS Task Execution Role also receives `AmazonECSTaskExecutionRolePolicy` (AWS managed) and S3 read/write on the processing bucket via `grant_read_write`.

### Lambda Function Permissions

All Lambda functions receive:
- S3 read/write on the processing bucket via `grant_read_write`
- `cloudwatch:PutMetricData` on `*` (no resource-level support)

Additional per-function permissions:

| Function | Extra Permissions | Resource |
|----------|-------------------|----------|
| Title Generator | `bedrock:InvokeModel` | `*` |
| Pre-Remediation Checker | `secretsmanager:GetSecretValue` | `secret:/myapp/*` |
| Post-Remediation Checker | `secretsmanager:GetSecretValue` | `secret:/myapp/*` |
| PDF Splitter | `states:StartExecution` | State machine ARN (via `grant_start_execution`) |

---

## Runtime Permissions — PDF-to-HTML

These permissions are created by the CDK stack (`pdf2html/cdk/lib/pdf2html-stack.js`).

### Required AWS Services
- Amazon S3 — File storage and processing
- AWS Lambda — Serverless compute
- Amazon ECR — Container image registry
- Amazon Bedrock — Model invocation and Data Automation
- Amazon CloudWatch — Monitoring and logging

### Lambda Role

```json
{
  "Statement": [
    {
      "Sid": "S3BucketAccess",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject", "s3:PutObject", "s3:ListBucket",
        "s3:DeleteObject", "s3:DeleteObjects", "s3:ListObjects",
        "s3:ListObjectsV2", "s3:GetBucketLocation",
        "s3:GetObjectVersion", "s3:GetBucketPolicy"
      ],
      "Resource": ["arn:${Partition}:s3:::${BucketName}", "arn:${Partition}:s3:::${BucketName}/*"]
    },
    {
      "Sid": "BedrockModelInvocation",
      "Effect": "Allow",
      "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
      "Resource": [
        "arn:${Partition}:bedrock:*::foundation-model/openai.gpt-5.6-luna",
        "arn:${Partition}:bedrock:*:${AccountId}:inference-profile/*openai.gpt-5.6-luna"
      ]
    },
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
        "arn:${Partition}:bedrock:${Region}:${AccountId}:data-automation-invocation/*"
      ]
    },
    {
      "Sid": "BedrockDataAutomationProfile",
      "Effect": "Allow",
      "Action": ["bedrock:InvokeDataAutomationAsync"],
      "Resource": "arn:${Partition}:bedrock:*:${AccountId}:data-automation-profile/*"
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
      "Resource": "arn:${Partition}:logs:${Region}:${AccountId}:log-group:/aws/lambda/Pdf2HtmlPipeline:*"
    }
  ]
}
```

> The Lambda role also receives the `AWSLambdaBasicExecutionRole` AWS managed policy.

---

## Security Considerations

### Principle of Least Privilege
- Runtime roles use scoped actions and resource ARNs wherever AWS supports them.
- Deployment (CodeBuild) policies only cover the CDK bootstrap resources (`cdk-*`) and, for PDF-to-HTML, the bucket and ECR repository the buildspec creates. Wildcard actions (`s3:*`, `ecr:*`, `cloudformation:*`) are scoped to those resource name patterns. Application resources are created by CloudFormation through the CDK bootstrap execution role.

### Services Without Resource-Level Permissions
These actions require `Resource: "*"`:
- `cloudwatch:PutMetricData`
- `comprehend:DetectDominantLanguage`
- `ecr:GetAuthorizationToken`
- `sts:GetCallerIdentity`
- `s3:ListAllMyBuckets`
- `cloudformation:ListStacks`
- `bedrock:CreateDataAutomationProject`

### Sensitive Data Protection
- Adobe API credentials stored in AWS Secrets Manager at `/myapp/client_credentials`
- All S3 buckets use server-side encryption (SSE-S3)
- VPC isolates ECS tasks in private subnets (PDF-to-PDF)
- IAM roles scoped to specific resource patterns

---

## Troubleshooting Permission Issues

### Common Errors

1. **CDK Bootstrap Failures** — Ensure CloudFormation and S3 permissions for `cdk-*` resources
2. **ECR Push Failures** — Verify ECR repository permissions and `ecr:GetAuthorizationToken`
3. **Stack Resource Failures (Lambda, ECS, VPC, IAM, ...)** — These are created by CloudFormation using the CDK bootstrap execution role, not the CodeBuild role. Check the stack events in the CloudFormation console, and confirm the account is bootstrapped (`CDKToolkit` stack exists)
4. **Step Function Execution Failures** — Verify Step Functions and ECS permissions
5. **Bedrock Access Denied** — Ensure model access is enabled in the console and IAM policy includes correct model ARNs
6. **BDA Project Creation Failures** — Verify `bedrock:CreateDataAutomationProject` in the caller policy (`deploy-policy.json`)
7. **`Partition "aws" is not valid for resource`** — An ARN was written for the commercial partition while deploying to AWS GovCloud. See [AWS GovCloud](#aws-govcloud)

### Permission Validation
```bash
aws sts get-caller-identity
aws iam get-user
aws bedrock list-foundation-models --region your-region
```

### Model ARN Formats
`${Partition}` is `aws` in commercial regions and `aws-us-gov` in AWS GovCloud.

- Foundation models: `arn:${Partition}:bedrock:${Region}::foundation-model/${ModelId}`
- Cross-region inference profiles: `arn:${Partition}:bedrock:${Region}:${AccountId}:inference-profile/${Prefix}.${ModelId}` (`Prefix` is `us`, `us-gov`, `eu` or `apac`)
- Data automation projects: `arn:${Partition}:bedrock:${Region}:${AccountId}:data-automation-project/${ProjectId}`
- Data automation invocations: `arn:${Partition}:bedrock:${Region}:${AccountId}:data-automation-invocation/${JobId}`
- Data automation profiles: `arn:${Partition}:bedrock:${Region}:${AccountId}:data-automation-profile/${ProfileId}`
