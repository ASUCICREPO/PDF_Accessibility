# Configuring Document Limits and Defaults

This guide explains the configurable limits across the PDF Accessibility solution and how to modify them. Limits exist at two levels:

1. **User-Facing Limits (UI)** — Per-user quotas for file uploads, page counts, and file size, managed through Cognito custom attributes in the [PDF_accessability_UI](https://github.com/ASUCICREPO/PDF_accessability_UI) repository.
2. **Infrastructure Limits (Backend)** — Resource-level settings such as Lambda timeouts, memory, chunk sizes, and concurrency, managed in this repository.

---

## Table of Contents

| Section | Description |
|---|---|
| [User-Facing Limits (UI)](#user-facing-limits-ui) | File upload quotas, page limits, and size limits per user |
| [Modifying User Limits via Cognito Console](#modifying-user-limits-via-the-cognito-console) | How to change limits for an individual user |
| [Modifying Default Group Limits in Code](#modifying-default-group-limits-in-code) | How to change the defaults assigned to new users |
| [Infrastructure Limits (Backend)](#infrastructure-limits-backend) | Lambda, ECS, Step Functions, and processing settings |
| [PDF-to-HTML Processing Defaults](#pdf-to-html-processing-defaults) | Configuration defaults for the PDF-to-HTML pipeline |

---

## User-Facing Limits (UI)

When the [PDF Accessibility UI](https://github.com/ASUCICREPO/PDF_accessability_UI) is deployed, each user is assigned limits via Cognito custom attributes. These limits control what users can upload through the web interface.

### Custom Cognito Attributes

| Attribute | Description | Default (DefaultUsers) |
|---|---|---|
| `custom:max_files_allowed` | Maximum number of files a user can upload | `8` |
| `custom:max_pages_allowed` | Maximum number of pages per PDF | `10` |
| `custom:max_size_allowed_MB` | Maximum file size in MB | `25` |
| `custom:total_files_uploaded` | Current upload count (tracked automatically) | `0` |

### Default Limits by User Group

The UI creates three Cognito user groups, each with different default limits:

| Attribute | DefaultUsers | AmazonUsers | AdminUsers |
|---|---|---|---|
| `max_files_allowed` | 8 | 15 | 100 |
| `max_pages_allowed` | 10 | 10 | 2500 |
| `max_size_allowed_MB` | 25 | 25 | 1000 |

These defaults are set when a user first signs up and is automatically assigned to a group. Users with an `@amazon.com` email are assigned to **AmazonUsers**; all others go to **DefaultUsers**. Administrators can move users to **AdminUsers** manually through the Cognito console.

---

## Modifying User Limits via the Cognito Console

To change limits for a **specific user** without redeploying:

1. Open the [Amazon Cognito Console](https://console.aws.amazon.com/cognito/).
2. Select the user pool named **`PDF-Accessability-User-Pool`**.
3. Navigate to **Users** and search for the user by email or username.
4. Select the user and scroll to **User attributes**.
5. Click **Edit** and modify any of the following attributes:
   - `custom:max_files_allowed` — Set the new file upload limit
   - `custom:max_pages_allowed` — Set the new page limit per PDF
   - `custom:max_size_allowed_MB` — Set the new file size limit in MB
   - `custom:total_files_uploaded` — Reset to `0` to restore a user's quota
6. Click **Save changes**.

The updated limits take effect immediately on the user's next upload attempt.

> **Note:** Changing a user's group membership (e.g., moving them from DefaultUsers to AdminUsers) will automatically apply that group's default limits via an EventBridge-triggered Lambda function.

---

## Modifying Default Group Limits in Code

To change the **default limits** that are assigned to all new users, you need to update two Lambda functions in the [PDF_accessability_UI](https://github.com/ASUCICREPO/PDF_accessability_UI) repository and redeploy.

### File 1: Post-Confirmation Lambda

**Path:** `cdk_backend/lambda/postConfirmation/index.py`

This Lambda runs when a new user signs up and sets their initial attributes. Edit the `group_attributes` dictionary:

```python
group_attributes = {
    DEFAULT_GROUP: {
        'custom:first_sign_in': 'true',
        'custom:total_files_uploaded': '0',
        'custom:max_files_allowed': '8',       # Change this value
        'custom:max_pages_allowed': '10',       # Change this value
        'custom:max_size_allowed_MB': '25'      # Change this value
    },
    AMAZON_GROUP: {
        'custom:first_sign_in': 'true',
        'custom:total_files_uploaded': '0',
        'custom:max_files_allowed': '15',       # Change this value
        'custom:max_pages_allowed': '10',       # Change this value
        'custom:max_size_allowed_MB': '25'      # Change this value
    },
    ADMIN_GROUP: {
        'custom:first_sign_in': 'true',
        'custom:total_files_uploaded': '0',
        'custom:max_files_allowed': '100',      # Change this value
        'custom:max_pages_allowed': '2500',     # Change this value
        'custom:max_size_allowed_MB': '1000'    # Change this value
    }
}
```

### File 2: Update Attributes Groups Lambda

**Path:** `cdk_backend/lambda/UpdateAttributesGroups/index.py`

This Lambda runs when a user is moved between groups (via EventBridge) and applies the new group's limits. Edit the `GROUP_LIMITS` dictionary:

```python
GROUP_LIMITS = {
    'DefaultUsers': {
        'custom:max_files_allowed': '3',        # Change this value
        'custom:max_pages_allowed': '10',       # Change this value
        'custom:max_size_allowed_MB': '25'      # Change this value
    },
    'AmazonUsers': {
        'custom:max_files_allowed': '5',        # Change this value
        'custom:max_pages_allowed': '10',       # Change this value
        'custom:max_size_allowed_MB': '25'      # Change this value
    },
    'AdminUsers': {
        'custom:max_files_allowed': '500',      # Change this value
        'custom:max_pages_allowed': '1500',     # Change this value
        'custom:max_size_allowed_MB': '1000'    # Change this value
    }
}
```

> **Important:** Make sure the values in both files are consistent for each group. After editing, redeploy the UI stack for changes to take effect. Only **newly registered users** or **users whose group changes** will receive the updated defaults. Existing users retain their current attribute values unless manually updated via the Cognito console.

### Redeploying After Changes

From the `PDF_accessability_UI` repository root:

```bash
cd cdk_backend
npx cdk deploy
```

Or re-run the deployment script:

```bash
chmod +x deploy.sh
./deploy.sh
```

---

## Infrastructure Limits (Backend)

The following limits are configured in this repository's infrastructure code (`app.py`) and affect processing capacity. Modifying these requires a redeployment of the backend stack.

### Lambda Function Limits

| Lambda Function | Timeout | Memory | File |
|---|---|---|---|
| PDF Splitter | 900s (15 min) | 1024 MB | `app.py` |
| PDF Merger | 900s (15 min) | 1024 MB | `app.py` |
| Title Generator | 900s (15 min) | 1024 MB | `app.py` |
| Pre-Remediation Checker | 900s (15 min) | 512 MB | `app.py` |
| Post-Remediation Checker | 900s (15 min) | 512 MB | `app.py` |

To modify, edit the `timeout` and `memory_size` parameters in `app.py`. For example:

```python
pdf_splitter_lambda = lambda_.Function(
    self, 'PdfChunkSplitterLambda',
    runtime=lambda_.Runtime.PYTHON_3_12,
    handler='main.lambda_handler',
    code=lambda_.Code.from_docker_build("lambda/pdf-splitter-lambda"),
    timeout=Duration.seconds(900),    # Maximum is 900 seconds (15 min)
    memory_size=1024                  # In MB, range: 128–10240
)
```

### ECS Task Limits

| Task | Memory | CPU | File |
|---|---|---|---|
| Adobe AutoTag | 1024 MiB | 256 (0.25 vCPU) | `app.py` |
| Alt Text Generator | 1024 MiB | 256 (0.25 vCPU) | `app.py` |

To modify, edit the `memory_limit_mib` and `cpu` parameters in `app.py`:

```python
adobe_autotag_task_def = ecs.FargateTaskDefinition(
    self, "AdobeAutotagTaskDefinition",
    memory_limit_mib=1024,   # Supported values: 512, 1024, 2048, 4096, ...
    cpu=256,                 # Supported values: 256, 512, 1024, 2048, 4096
    ...
)
```

### Step Functions Limits

| Setting | Value | File |
|---|---|---|
| State Machine Timeout | 150 minutes | `app.py` |
| Map State Max Concurrency | 100 | `app.py` |

To modify:

```python
# State Machine overall timeout
pdf_remediation_state_machine = sfn.StateMachine(
    self, "PdfAccessibilityRemediationWorkflow",
    definition=parallel_accessibility_workflow,
    timeout=Duration.minutes(150),    # Change this value
    ...
)

# Maximum parallel chunk processing
pdf_chunks_map_state = sfn.Map(
    self, "ProcessPdfChunksInParallel",
    max_concurrency=100,              # Change this value
    ...
)
```

### PDF Chunk Size (Pages Per Chunk)

The PDF splitter Lambda splits uploaded PDFs into chunks for parallel processing. The number of pages per chunk is set in `lambda/pdf-splitter-lambda/main.py`:

```python
# Line 146 in lambda/pdf-splitter-lambda/main.py
chunks = split_pdf_into_pages(pdf_file_content, pdf_file_key, s3, bucket_name, 200)
```

The last argument (`200`) is the number of pages per chunk. To process in smaller or larger batches, change this value.

### Image Size Limit

The maximum image size for Bedrock model invocation is set in `pdf2html/content_accessibility_utility_on_aws/remediate/services/bedrock_client.py`:

```python
MAX_IMAGE_SIZE = 4_000_000  # 4 MB — maximum allowed image size in bytes
```

Images exceeding this limit are automatically resized before being sent to Bedrock.

### Redeploying After Infrastructure Changes

After modifying any values in `app.py` or Lambda source code, redeploy the backend:

```bash
cdk deploy
```

Or re-run the deployment script:

```bash
chmod +x deploy.sh
./deploy.sh
```

---

## PDF-to-HTML Processing Defaults

The PDF-to-HTML pipeline has its own set of configurable defaults defined in `pdf2html/content_accessibility_utility_on_aws/utils/config_defaults.yaml`:

```yaml
pdf:
  extract_images: true
  image_format: "png"
  embed_fonts: false
  single_file: false
  continuous: true
  embed_images: false
  exclude_images: false
  cleanup_bda_output: false

audit:
  severity_threshold: "minor"
  detailed_context: true
  skip_automated_checks: false

remediate:
  severity_threshold: "minor"
  model_id: "us.amazon.nova-lite-v1:0"

aws:
  region: null
  create_bda_project: false
```

These defaults can be overridden in three ways (in order of precedence, highest first):

1. **Command-line arguments** — When using the CLI directly
2. **Configuration file** — Pass a custom YAML file with `--config my-config.yaml`
3. **Environment variables** — Prefix with `DOC_ACCESS_` (e.g., `DOC_ACCESS_PDF_IMAGE_FORMAT=jpg`)

For details on CLI options and configuration file format, see the [pdf2html README](../pdf2html/README.md#configuration).

---

## Support

For questions or assistance with configuration:

- **Email**: ai-cic@amazon.com
- **Issues**: [GitHub Issues](https://github.com/ASUCICREPO/PDF_Accessibility/issues)
