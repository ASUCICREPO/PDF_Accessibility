import os
import boto3
import json
from adobe.pdfservices.operation.auth.service_principal_credentials import ServicePrincipalCredentials
from adobe.pdfservices.operation.exception.exceptions import ServiceApiException, ServiceUsageException, SdkException
from adobe.pdfservices.operation.io.cloud_asset import CloudAsset
from adobe.pdfservices.operation.io.stream_asset import StreamAsset
from adobe.pdfservices.operation.pdf_services import PDFServices,ClientConfig
from adobe.pdfservices.operation.pdf_services_media_type import PDFServicesMediaType
from adobe.pdfservices.operation.pdfjobs.jobs.pdf_accessibility_checker_job import PDFAccessibilityCheckerJob
from adobe.pdfservices.operation.pdfjobs.result.pdf_accessibility_checker_result import PDFAccessibilityCheckerResult
from botocore.exceptions import ClientError
import re

def create_json_output_file_path():
        os.makedirs("/tmp/PDFAccessibilityChecker", exist_ok=True)
        return f"/tmp/PDFAccessibilityChecker/result_after_remidiation.json"

def download_file_from_s3(bucket_name,file_key, save_path, local_path):
    s3 = boto3.client('s3')
    print(f"Filename : {file_key} | File key in the function: {save_path}")

    s3.download_file(bucket_name, save_path, local_path)

    print(f"Filename : {file_key} | Downloaded {file_key} from {bucket_name} to {local_path}")

def save_to_s3(bucket_name, file_key):
    s3 = boto3.client('s3')
    local_path = "/tmp/PDFAccessibilityChecker/result_after_remidiation.json"

    file_key_without_extension = os.path.splitext(file_key)[0]
    file_key_without_compliant = file_key_without_extension.replace("COMPLIANT_", "", 1)
    
    bucket_save_path = f"temp/{file_key_without_compliant}/accessability-report/{file_key_without_extension}_accessibility_report_after_remidiation.json"
    with open(local_path, "rb") as data:
        s3.upload_fileobj(data, bucket_name, bucket_save_path)
    print(f"Filename {file_key} | Uploaded {file_key} to {bucket_name} at path {bucket_save_path} after remidiation")
    return bucket_save_path

        
def get_secret(basefilename):
    secret_name = "/myapp/client_credentials"
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager'
    )
    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
        secret = get_secret_value_response['SecretString']
        secret_dict = json.loads(secret)
        
        client_id = secret_dict['client_credentials']['PDF_SERVICES_CLIENT_ID']
        client_secret = secret_dict['client_credentials']['PDF_SERVICES_CLIENT_SECRET']
        return client_id, client_secret

    except ClientError as e:
        print(f'Filename : {basefilename} | Error: {e}')
        raise  # Re-raise the exception to indicate failure

    except KeyError as e:
        print(f"Filename : {basefilename} | KeyError: Missing key in the secret data: {e}")
        raise  # Re-raise KeyError to indicate malformed secret structure

    except Exception as e:
        print(f"Filename : {basefilename} | Unexpected error: {e}")
        raise  # Re-raise unexpected exceptions for debugging
     

def lambda_handler(event, context):
    print("Received event:", event)
    
    # Extracting nested values from the event
    payload = event.get('Payload', {})
    body = payload.get('body', {})
    s3_bucket = body.get('bucket')
    save_path = body.get('save_path')

    # Validate inputs
    if not s3_bucket or not save_path:
        raise ValueError("Missing required inputs: 's3_bucket' or 'save_path'")

    print(f"s3_bucket: {s3_bucket}, save_path: {save_path}")

    # Extract file basename using regex
    pattern = r"COMPLIANT_[^/]*"
    match = re.search(pattern, save_path)
    if not match:
        raise ValueError(f"Pattern '{pattern}' not found in save_path: {save_path}")
    
    file_basename = match.group(0)
    print("File basename:", file_basename)


    local_path = f"/tmp/{file_basename}"
    download_file_from_s3(s3_bucket,file_basename ,save_path, local_path)

    try:
        pdf_file = open(local_path, 'rb')
        input_stream = pdf_file.read()
        pdf_file.close()
        client_config = ClientConfig(
                    connect_timeout=8000,
                    read_timeout=40000
                )
        client_id, client_secret = get_secret(file_basename)
        # Initial setup, create credentials instance
        credentials = ServicePrincipalCredentials(
            client_id=client_id,
            client_secret=client_secret)

        # Creates a PDF Services instance
        pdf_services = PDFServices(credentials=credentials, client_config=client_config)

        # Creates an asset(s) from source file(s) and upload
        input_asset = pdf_services.upload(input_stream=input_stream, mime_type=PDFServicesMediaType.PDF)

        # Creates a new job instance
        pdf_accessibility_checker_job = PDFAccessibilityCheckerJob(input_asset=input_asset)

        # Submit the job and gets the job result
        location = pdf_services.submit(pdf_accessibility_checker_job)
        pdf_services_response = pdf_services.get_job_result(location, PDFAccessibilityCheckerResult)

        # Get content from the resulting asset(s)
        report_asset: CloudAsset = pdf_services_response.get_result().get_report()
        stream_report: StreamAsset = pdf_services.get_content(report_asset)
        output_file_path_json = create_json_output_file_path()
        
        with open(output_file_path_json, "wb") as file:
            file.write(stream_report.get_input_stream())

        bucket_save_path = save_to_s3(s3_bucket, file_basename)
        print(f"Filename : {file_basename} | Saved accessibility report to {bucket_save_path}")

    except (ServiceApiException, ServiceUsageException, SdkException) as e:
        print(f'Filename : {file_basename} | Exception encountered while executing operationat post accessability check: {e}')
        return f"Filename : {file_basename} | Exception encountered while executing operation at post accessability check: {e}"
    return f"Filename : {file_basename} | Saved accessibility report to {bucket_save_path}"
    
