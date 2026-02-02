import aws_cdk as cdk
from aws_cdk import (
    Duration,
    Stack,
    aws_lambda as lambda_,
    aws_s3 as s3,
    aws_s3_notifications as s3n,
    aws_s3_deployment as s3deploy,
    aws_iam as iam,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecr as ecr,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_logs as logs,
    aws_ecr_assets as ecr_assets,
    aws_cloudwatch as cloudwatch,
)
from constructs import Construct
import platform
import datetime

class PDFAccessibility(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # S3 Bucket
        pdf_processing_bucket = s3.Bucket(self, "pdfaccessibilitybucket1", 
                          encryption=s3.BucketEncryption.S3_MANAGED, 
                          enforce_ssl=True,
                          cors=[s3.CorsRule(
                              allowed_headers=["*"],
                              allowed_methods=[s3.HttpMethods.GET, s3.HttpMethods.HEAD, s3.HttpMethods.PUT, s3.HttpMethods.POST, s3.HttpMethods.DELETE],
                              allowed_origins=["*"],
                              exposed_headers=[]
                          )])
    
        # Create pdf/ folder in the bucket
        s3deploy.BucketDeployment(self, "CreatePdfFolder",
            sources=[s3deploy.Source.data("pdf/.keep", "")],
            destination_bucket=pdf_processing_bucket,
        )
        
        # Get account and region for use throughout the stack
        account_id = Stack.of(self).account
        region = Stack.of(self).region

        # Docker images with zstd compression for faster Fargate cold starts
        # zstd decompresses ~2-3x faster than gzip, reducing container startup time
        adobe_autotag_image_asset = ecr_assets.DockerImageAsset(self, "AdobeAutotagImage",
                                                         directory="adobe-autotag-container",
                                                         platform=ecr_assets.Platform.LINUX_AMD64,
                                                         # Enable zstd compression for faster decompression on Fargate
                                                         cache_to=ecr_assets.DockerCacheOption(
                                                             type="inline"
                                                         ),
                                                         outputs=["type=image,compression=zstd,compression-level=3,force-compression=true"])

        alt_text_generator_image_asset = ecr_assets.DockerImageAsset(self, "AltTextGeneratorImage",
                                                             directory="alt-text-generator-container",
                                                             platform=ecr_assets.Platform.LINUX_AMD64,
                                                             # Enable zstd compression for faster decompression on Fargate
                                                             cache_to=ecr_assets.DockerCacheOption(
                                                                 type="inline"
                                                             ),
                                                             outputs=["type=image,compression=zstd,compression-level=3,force-compression=true"])

        # VPC with Public and Private Subnets
        pdf_processing_vpc = ec2.Vpc(self, "PdfProcessingVpc",
            max_azs=2,
            nat_gateways=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    subnet_type=ec2.SubnetType.PUBLIC,
                    name="PdfProcessingPublic",
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    name="PdfProcessingPrivate",
                    cidr_mask=24,
                ),
            ]
        )

        # VPC Endpoints for faster ECR image pulls (reduces cold start by 10-15s)
        pdf_processing_vpc.add_interface_endpoint("EcrApiEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.ECR
        )
        pdf_processing_vpc.add_interface_endpoint("EcrDockerEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.ECR_DOCKER
        )
        pdf_processing_vpc.add_gateway_endpoint("S3Endpoint",
            service=ec2.GatewayVpcEndpointAwsService.S3
        )

        # ECS Cluster
        pdf_remediation_cluster = ecs.Cluster(self, "PdfRemediationCluster", vpc=pdf_processing_vpc)

        ecs_task_execution_role = iam.Role(self, "EcsTaskRole",
                                 assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
                                 managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy")
            ])

        ecs_task_role = iam.Role(self, "EcsTaskExecutionRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy"),
            ]
        )
        
        # Bedrock permissions for alt-text generation models
        ecs_task_role.add_to_policy(iam.PolicyStatement(
            actions=["bedrock:InvokeModel"],
            resources=["*"],
        ))
        
        # S3 permissions - scoped to the processing bucket only
        ecs_task_role.add_to_policy(iam.PolicyStatement(
            actions=[
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
            ],
            resources=[
                pdf_processing_bucket.bucket_arn,
                f"{pdf_processing_bucket.bucket_arn}/*",
            ],
        ))
        
        # Comprehend permissions for language detection (no resource-level permissions supported)
        ecs_task_role.add_to_policy(iam.PolicyStatement(
            actions=["comprehend:DetectDominantLanguage"],
            resources=["*"],  # Comprehend DetectDominantLanguage does not support resource-level permissions
        ))
        
        # Secrets Manager permissions - scoped to Adobe API credentials
        ecs_task_role.add_to_policy(iam.PolicyStatement(
            actions=["secretsmanager:GetSecretValue"],
            resources=[f"arn:aws:secretsmanager:{region}:{account_id}:secret:/myapp/*"],
        ))
        # Grant S3 read/write access to ECS Task Role
        pdf_processing_bucket.grant_read_write(ecs_task_execution_role)
        # Create ECS Task Log Groups explicitly
        adobe_autotag_log_group = logs.LogGroup(self, "AdobeAutotagContainerLogs",
                                                log_group_name="/ecs/pdf-remediation/adobe-autotag",
                                                retention=logs.RetentionDays.ONE_MONTH,
                                                removal_policy=cdk.RemovalPolicy.DESTROY)

        alt_text_generator_log_group = logs.LogGroup(self, "AltTextGeneratorContainerLogs",
                                                    log_group_name="/ecs/pdf-remediation/alt-text-generator",
                                                    retention=logs.RetentionDays.ONE_MONTH,
                                                    removal_policy=cdk.RemovalPolicy.DESTROY)
        # ECS Task Definitions
        adobe_autotag_task_def = ecs.FargateTaskDefinition(self, "AdobeAutotagTaskDefinition",
                                                      memory_limit_mib=1024,
                                                      cpu=256, execution_role=ecs_task_execution_role, task_role=ecs_task_role,
                                                     )

        adobe_autotag_container_def = adobe_autotag_task_def.add_container("adobe-autotag-container",
                                                                  image=ecs.ContainerImage.from_registry(adobe_autotag_image_asset.image_uri),
                                                                  memory_limit_mib=1024,
                                                                  logging=ecs.LogDrivers.aws_logs(
        stream_prefix="AdobeAutotagLogs",
        log_group=adobe_autotag_log_group,
    ))

        alt_text_task_def = ecs.FargateTaskDefinition(self, "AltTextGenerationTaskDefinition",
                                                      memory_limit_mib=1024,
                                                      cpu=256, execution_role=ecs_task_execution_role, task_role=ecs_task_role,
                                                      )

        alt_text_container_def = alt_text_task_def.add_container("alt-text-llm-container",
                                                                  image=ecs.ContainerImage.from_registry(alt_text_generator_image_asset.image_uri),
                                                                  memory_limit_mib=1024,
                                                                   logging=ecs.LogDrivers.aws_logs(
        stream_prefix="AltTextGeneratorLogs",
        log_group=alt_text_generator_log_group
    ))
        # ECS Tasks in Step Functions
        adobe_autotag_task = tasks.EcsRunTask(self, "RunAdobeAutotagTask",
                                      integration_pattern=sfn.IntegrationPattern.RUN_JOB,
                                      cluster=pdf_remediation_cluster,
                                      task_definition=adobe_autotag_task_def,
                                      assign_public_ip=False,
                                      
                                      container_overrides=[tasks.ContainerOverride(
                                       container_definition = adobe_autotag_container_def,
                                          environment=[
                                              tasks.TaskEnvironmentVariable(
                                                  name="S3_BUCKET_NAME",
                                                  value=sfn.JsonPath.string_at("$.s3_bucket")
                                              ),
                                              tasks.TaskEnvironmentVariable(
                                                  name="S3_FILE_KEY",
                                                  value=sfn.JsonPath.string_at("$.s3_key")
                                              ),
                                              tasks.TaskEnvironmentVariable(
                                                  name="S3_CHUNK_KEY",
                                                  value=sfn.JsonPath.string_at("$.chunk_key")
                                              ),
                                            tasks.TaskEnvironmentVariable(
                                                  name="AWS_REGION",
                                                  value=region
                                              ),
                                          ]
                                      )],
                                      launch_target=tasks.EcsFargateLaunchTarget(
                                          platform_version=ecs.FargatePlatformVersion.LATEST
                                      ),
                                      propagated_tag_source=ecs.PropagatedTagSource.TASK_DEFINITION,
                                     )

        alt_text_generation_task = tasks.EcsRunTask(self, "RunAltTextGenerationTask",
                                      integration_pattern=sfn.IntegrationPattern.RUN_JOB,
                                      cluster=pdf_remediation_cluster,
                                      task_definition=alt_text_task_def,
                                      assign_public_ip=False,
                                    
                                      container_overrides=[tasks.ContainerOverride(
                                          container_definition=alt_text_container_def,
                                          environment=[
                                              tasks.TaskEnvironmentVariable(
                                                  name="S3_BUCKET_NAME",
                                                  value=sfn.JsonPath.string_at("$.Overrides.ContainerOverrides[0].Environment[0].Value")
                                              ),
                                              tasks.TaskEnvironmentVariable(
                                                  name="S3_FILE_KEY",
                                                  value=sfn.JsonPath.string_at("$.Overrides.ContainerOverrides[0].Environment[1].Value")
                                              ),
                                              tasks.TaskEnvironmentVariable(
                                                  name="AWS_REGION",
                                                  value=region
                                              ),
                                          ]
                                      )],
                                      launch_target=tasks.EcsFargateLaunchTarget(
                                          platform_version=ecs.FargatePlatformVersion.LATEST
                                      ),
                                      propagated_tag_source=ecs.PropagatedTagSource.TASK_DEFINITION,
                                      )

        # Step Function Map State
        pdf_chunks_map_state = sfn.Map(self, "ProcessPdfChunksInParallel",
                            max_concurrency=100,
                            items_path=sfn.JsonPath.string_at("$.chunks"),
                            result_path="$.MapResults")

        pdf_chunks_map_state.iterator(adobe_autotag_task.next(alt_text_generation_task))

        cloudwatch_metrics_policy = iam.PolicyStatement(
                    actions=["cloudwatch:PutMetricData"],  # Allow PutMetricData action
                    resources=["*"],  # All CloudWatch resources # All CloudWatch Logs resources
        )
        pdf_merger_lambda = lambda_.Function(
            self, 'PdfMergerLambda',
            runtime=lambda_.Runtime.JAVA_21,
            handler='com.example.App::handleRequest',
            code=lambda_.Code.from_asset('lambda/pdf-merger-lambda/PDFMergerLambda/target/PDFMergerLambda-1.0-SNAPSHOT.jar'),
            environment={
                'BUCKET_NAME': pdf_processing_bucket.bucket_name  # this line sets the environment variable
            },
            timeout=Duration.seconds(900),
            memory_size=1024
        )

        pdf_merger_lambda.add_to_role_policy(cloudwatch_metrics_policy)
        pdf_merger_lambda_task = tasks.LambdaInvoke(self, "MergePdfChunks",
                                      lambda_function=pdf_merger_lambda,
                                      payload=sfn.TaskInput.from_object({
        "fileNames.$": "$.chunks[*].s3_key"
                     }),
                                      output_path=sfn.JsonPath.string_at("$.Payload"))
        pdf_processing_bucket.grant_read_write(pdf_merger_lambda)

        # Define the Add Title Lambda function
        host_machine = platform.machine().lower()
        print("Architecture of Machine:",host_machine)
        if "arm" in host_machine:
            lambda_arch = lambda_.Architecture.ARM_64
        else:
            lambda_arch = lambda_.Architecture.X86_64

        title_generator_lambda = lambda_.Function(
            self, 'BedrockTitleGeneratorLambda',
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler='title_generator.lambda_handler',
            code=lambda_.Code.from_docker_build('lambda/title-generator-lambda'),
            timeout=Duration.seconds(900),
            memory_size=1024,
            # architecture=lambda_.Architecture.ARM_64
            architecture=lambda_arch,
        )

        # Grant the Lambda function read/write permissions to the S3 bucket
        pdf_processing_bucket.grant_read_write(title_generator_lambda)

        # Define the task to invoke the Add Title Lambda function
        title_generator_lambda_task = tasks.LambdaInvoke(
            self, "GenerateAccessibleTitle",
            lambda_function=title_generator_lambda,
            payload=sfn.TaskInput.from_object({
                "Payload.$": "$"
            })
        )

        # Add the necessary policy to the Lambda function's role
        title_generator_lambda.add_to_role_policy(cloudwatch_metrics_policy)
        
        # Bedrock permissions for title generation models
        title_generator_lambda.add_to_role_policy(iam.PolicyStatement(
            actions=["bedrock:InvokeModel"],
            resources=["*"],
        ))

        # Chain the tasks in the state machine
        # chain = pdf_chunks_map_state.next(pdf_merger_lambda_task).next(title_generator_lambda_task)
        
        pre_remediation_accessibility_checker = lambda_.Function(
            self,'PreRemediationAccessibilityAuditor',
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler='main.lambda_handler',
            code=lambda_.Code.from_docker_build('lambda/pre-remediation-accessibility-checker'),
            timeout=Duration.seconds(900),
            memory_size=512,
            architecture=lambda_arch,
        )
        
        pre_remediation_accessibility_checker.add_to_role_policy(
            iam.PolicyStatement(
            actions=["secretsmanager:GetSecretValue"],
            resources=[f"arn:aws:secretsmanager:{region}:{account_id}:secret:/myapp/*"]
        ))
        pdf_processing_bucket.grant_read_write(pre_remediation_accessibility_checker)
        pre_remediation_accessibility_checker.add_to_role_policy(cloudwatch_metrics_policy)

        pre_remediation_accessibility_checker_task = tasks.LambdaInvoke(
            self, 
            "AuditPreRemediationAccessibility",
            lambda_function=pre_remediation_accessibility_checker,
            payload=sfn.TaskInput.from_json_path_at("$"),
            output_path="$.Payload"
        )

        post_remediation_accessibility_checker = lambda_.Function(
            self,'PostRemediationAccessibilityAuditor',
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler='main.lambda_handler',
            code=lambda_.Code.from_docker_build('lambda/post-remediation-accessibility-checker'),
            timeout=Duration.seconds(900),
            memory_size=512,
            architecture=lambda_arch,
        )
        
        post_remediation_accessibility_checker.add_to_role_policy(
            iam.PolicyStatement(
            actions=["secretsmanager:GetSecretValue"],
            resources=[f"arn:aws:secretsmanager:{region}:{account_id}:secret:/myapp/*"]
        ))
        pdf_processing_bucket.grant_read_write(post_remediation_accessibility_checker)
        post_remediation_accessibility_checker.add_to_role_policy(cloudwatch_metrics_policy)

        post_remediation_accessibility_checker_task = tasks.LambdaInvoke(
            self, 
            "AuditPostRemediationAccessibility",
            lambda_function=post_remediation_accessibility_checker,
            payload=sfn.TaskInput.from_json_path_at("$"),
            output_path="$.Payload"
        )
        
        remediation_chain = pdf_chunks_map_state.next(pdf_merger_lambda_task).next(title_generator_lambda_task).next(post_remediation_accessibility_checker_task)

        parallel_accessibility_workflow = sfn.Parallel(self, "ParallelAccessibilityWorkflow",
                                      result_path="$.ParallelResults")
        parallel_accessibility_workflow.branch(remediation_chain)
        parallel_accessibility_workflow.branch(pre_remediation_accessibility_checker_task)

        pdf_remediation_workflow_log_group = logs.LogGroup(self, "PdfRemediationWorkflowLogs",
            log_group_name="/aws/states/pdf-accessibility-remediation-workflow",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=cdk.RemovalPolicy.DESTROY
        )
        # State Machine

        pdf_remediation_state_machine = sfn.StateMachine(self, "PdfAccessibilityRemediationWorkflow",
                                         definition=parallel_accessibility_workflow,
                                         timeout=Duration.minutes(150),
                                         logs=sfn.LogOptions(
                                             destination=pdf_remediation_workflow_log_group,
                                             level=sfn.LogLevel.ALL
                                         ))
        
        # Lambda Function
        pdf_splitter_lambda = lambda_.Function(
            self, 'PdfChunkSplitterLambda',
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler='main.lambda_handler',
            code=lambda_.Code.from_docker_build("lambda/pdf-splitter-lambda"),
            timeout=Duration.seconds(900),
            memory_size=1024
        )

        pdf_splitter_lambda.add_to_role_policy(cloudwatch_metrics_policy)

        # S3 Permissions for Lambda
        pdf_processing_bucket.grant_read_write(pdf_splitter_lambda)

        # Trigger Lambda on S3 Event
        pdf_processing_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(pdf_splitter_lambda),
            s3.NotificationKeyFilter(prefix="pdf/"),
            s3.NotificationKeyFilter(suffix=".pdf")
        )

        # Step Function Execution Permissions
        pdf_remediation_state_machine.grant_start_execution(pdf_splitter_lambda)

        # Pass State Machine ARN to Lambda as an Environment Variable
        pdf_splitter_lambda.add_environment("STATE_MACHINE_ARN", pdf_remediation_state_machine.state_machine_arn)
        # Store log group names dynamically
        pdf_splitter_lambda_log_group_name = f"/aws/lambda/{pdf_splitter_lambda.function_name}"
        pdf_merger_lambda_log_group_name = f"/aws/lambda/{pdf_merger_lambda.function_name}"
        title_generator_lambda_log_group_name = f"/aws/lambda/{title_generator_lambda.function_name}"
        pre_remediation_checker_log_group_name = f"/aws/lambda/{pre_remediation_accessibility_checker.function_name}"
        post_remediation_checker_log_group_name = f"aws/lambda/{post_remediation_accessibility_checker.function_name}"



        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        dashboard_name = f"PDF_Processing_Dashboard-{timestamp}"
        dashboard = cloudwatch.Dashboard(self, "PdfRemediationMonitoringDashboard", dashboard_name=dashboard_name,
                                         variables=[cloudwatch.DashboardVariable(
                                            id="filename",
                                            type=cloudwatch.VariableType.PATTERN,
                                            label="File Name",
                                            input_type=cloudwatch.VariableInputType.INPUT,
                                            value="filename",
                                            visible=True,
                                            default_value=cloudwatch.DefaultValue.value(".*"),
                                        )]
                                         )
        # Add Widgets to the Dashboard
        dashboard.add_widgets(
            cloudwatch.LogQueryWidget(
                title="File status",
                log_group_names=[pdf_splitter_lambda_log_group_name, pdf_merger_lambda_log_group_name, adobe_autotag_log_group.log_group_name,  alt_text_generator_log_group.log_group_name],
                query_string='''fields @timestamp, @message
                    | parse @message "File: *, Status: *" as file, status
                    | stats latest(status) as latestStatus by file
                    | sort file asc ''',
                width=24,
                height=6
            ),
            cloudwatch.LogQueryWidget(
                title="Split PDF Lambda Logs",
                log_group_names=[pdf_splitter_lambda_log_group_name],
                query_string='''fields @message 
                                | filter @message like /filename/''',
                width=24,
                height=6
            ),
            cloudwatch.LogQueryWidget(
                title="Step Function Execution Logs",
                log_group_names=[pdf_remediation_workflow_log_group.log_group_name],
                query_string='''fields @message 
                                | filter @message like /filename/''',
                width=24,
                height=6
            ),
            cloudwatch.LogQueryWidget(
                title="Adobe Autotag Processing Logs",
                log_group_names=[adobe_autotag_log_group.log_group_name],
                query_string='''fields @message 
                                | filter @message like /filename/''',
                width=24,
                height=6
            ),
            cloudwatch.LogQueryWidget(
                title="Alt Text Generation Logs",
                log_group_names=[alt_text_generator_log_group.log_group_name],
                query_string='''fields @message 
                                | filter @message like /filename/''',
                width=24,
                height=6
            ),
            cloudwatch.LogQueryWidget(
                title="PDF Merger Lambda Logs",
                log_group_names=[pdf_merger_lambda_log_group_name],
                query_string='''fields @message 
                                | filter @message like /filename/''',
                width=24,
                height=6
            ),
        )

app = cdk.App()
PDFAccessibility(app, "PDFAccessibility")
app.synth()
