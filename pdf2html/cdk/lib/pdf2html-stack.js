const { Stack, Duration, CfnOutput, CfnParameter, RemovalPolicy } = require('aws-cdk-lib');
const s3 = require('aws-cdk-lib/aws-s3');
const lambda = require('aws-cdk-lib/aws-lambda');
const ecr = require('aws-cdk-lib/aws-ecr');
const iam = require('aws-cdk-lib/aws-iam');
const s3n = require('aws-cdk-lib/aws-s3-notifications');

class Pdf2HtmlStack extends Stack {
  constructor(scope, id, props) {
    super(scope, id, props);

    // Parameters
    const bucketName = new CfnParameter(this, 'BucketName', {
      type: 'String',
      description: 'Name of the pre-created S3 bucket for PDF processing',
      default: `pdf2html-bucket-${this.account}-${this.region}`
    });

    const bdaProjectArn = new CfnParameter(this, 'BdaProjectArn', {
      type: 'String',
      description: 'ARN of the pre-created BDA project',
      default: ''
    });

    // Import existing S3 bucket
    const bucket = s3.Bucket.fromBucketName(this, 'Pdf2HtmlBucket', bucketName.valueAsString);

    // Import existing ECR repository
    const repository = ecr.Repository.fromRepositoryName(this, 'Pdf2HtmlRepository', 'pdf2html-lambda');

    // Create IAM role for Lambda
    const lambdaRole = new iam.Role(this, 'Pdf2HtmlLambdaRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
      ],
    });

    // Add permissions for S3
    // Add permissions for S3
    lambdaRole.addToPolicy(new iam.PolicyStatement({
      actions: [
        's3:GetObject',
        's3:PutObject',
        's3:ListBucket',
        's3:DeleteObject',
        's3:DeleteObjects',
        's3:ListObjects',
        's3:ListObjectsV2',
        's3:GetBucketLocation',
        's3:GetObjectVersion',
        's3:GetBucketPolicy'
      ],
      resources: [`arn:aws:s3:::${bucketName.valueAsString}`, `arn:aws:s3:::${bucketName.valueAsString}/*`],
    }));

    // Add permissions for Bedrock - scoped to specific actions needed
    lambdaRole.addToPolicy(new iam.PolicyStatement({
      actions: [
        'bedrock:InvokeModel',
        'bedrock:InvokeModelWithResponseStream',
      ],
      resources: [
        `arn:aws:bedrock:${this.region}::foundation-model/us.amazon.nova-lite-v1:0`,
        `arn:aws:bedrock:${this.region}::foundation-model/amazon.nova-lite-v1:0`,
        `arn:aws:bedrock:${this.region}::foundation-model/us.amazon.nova-pro-v1:0`,
        `arn:aws:bedrock:${this.region}::foundation-model/amazon.nova-pro-v1:0`,
      ],
    }));
    
    // Bedrock Data Automation permissions - scoped to specific project
    lambdaRole.addToPolicy(new iam.PolicyStatement({
      actions: [
        'bedrock:InvokeDataAutomationAsync',
        'bedrock:GetDataAutomationStatus',
        'bedrock:GetDataAutomationProject',
      ],
      resources: [
        bdaProjectArn.valueAsString,
        `arn:aws:bedrock:${this.region}:${this.account}:data-automation-invocation/*`,
      ],
    }));
    
    // Bedrock Data Automation profile access (required for BDA operations)
    // Note: BDA uses managed profiles (e.g. us.data-automation-v1) that may reside
    // in a different region (us-east-1), so we use wildcard for region
    lambdaRole.addToPolicy(new iam.PolicyStatement({
      actions: [
        'bedrock:InvokeDataAutomationAsync',
      ],
      resources: [
        `arn:aws:bedrock:*:${this.account}:data-automation-profile/*`,
      ],
    }));
    
    // Add CloudWatch Logs permissions - scoped to Lambda log group
    lambdaRole.addToPolicy(new iam.PolicyStatement({
      actions: [
        'logs:CreateLogGroup',
        'logs:CreateLogStream',
        'logs:PutLogEvents'
      ],
      resources: [
        `arn:aws:logs:${this.region}:${this.account}:log-group:/aws/lambda/Pdf2HtmlPipeline:*`,
      ],
    }));

    // Create Lambda function
    const lambdaFunction = new lambda.DockerImageFunction(this, 'Pdf2HtmlFunction', {
      functionName: 'Pdf2HtmlPipeline',
      code: lambda.DockerImageCode.fromEcr(repository, {
        tagOrDigest: 'latest'
      }),
      role: lambdaRole,
      timeout: Duration.minutes(15),
      memorySize: 1024,
      environment: {
        BDA_PROJECT_ARN: bdaProjectArn.valueAsString,
        BDA_S3_BUCKET: bucketName.valueAsString,
        BDA_OUTPUT_PREFIX: 'bda-processing',  // Use the new prefix for BDA output
        CLEANUP_INTERMEDIATE_FILES: 'true'    // Enable cleanup of intermediate files
      },
    });

    // Configure S3 event notification to trigger Lambda
    bucket.addEventNotification(
      s3.EventType.OBJECT_CREATED,
      new s3n.LambdaDestination(lambdaFunction),
      { prefix: 'uploads/' },
      { suffix: '.pdf' }
    );

    // Outputs
    new CfnOutput(this, 'BucketNameOutput', {
      value: bucketName.valueAsString,
      description: 'Name of the S3 bucket for PDF processing',
    });

    new CfnOutput(this, 'RepositoryUriOutput', {
      value: `${this.account}.dkr.ecr.${this.region}.amazonaws.com/pdf2html-lambda`,
      description: 'URI of the ECR repository',
    });

    new CfnOutput(this, 'LambdaFunctionNameOutput', {
      value: lambdaFunction.functionName,
      description: 'Name of the Lambda function',
    });

    new CfnOutput(this, 'BdaProjectArnOutput', {
      value: bdaProjectArn.valueAsString,
      description: 'ARN of the BDA project',
    });
  }
}

module.exports = { Pdf2HtmlStack };
