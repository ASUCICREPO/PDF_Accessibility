import boto3
import json
import os
import time
import random
import fitz  # PyMuPDF

# Helper function for exponential backoff and retry
def exponential_backoff_retry(
    func,
    *args,
    retries=3,
    base_delay=1,
    backoff_factor=2,
    **kwargs
):
    """
    Retries a given function using exponential backoff in case of exception.

    :param func: The function (or method) to be executed.
    :param args: Positional arguments to pass to the function.
    :param retries: Maximum number of retries before failing.
    :param base_delay: Initial delay (in seconds).
    :param backoff_factor: Multiplicative factor by which the delay increases each retry.
    :param kwargs: Keyword arguments to pass to the function.
    :return: Whatever `func` returns if it succeeds.
    :raises: The last exception if all retries fail.
    """
    attempt = 0
    while True:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            attempt += 1
            if attempt >= retries:
                print(f"[ExponentialBackoff] Exhausted retries for {func.__name__}. Error: {e}")
                raise
            sleep_time = base_delay * (backoff_factor ** (attempt - 1)) + random.uniform(0, 1)
            print(f"[ExponentialBackoff] Attempt {attempt}/{retries} for {func.__name__} failed with error: {e}. "
                  f"Sleeping for {sleep_time:.2f} seconds.")
            time.sleep(sleep_time)


def inference_profile_prefix(region):
    """Cross-region inference profile prefix for the region (us., us-gov., eu., apac.)."""
    if region.startswith('us-gov-'):
        return 'us-gov.'
    if region.startswith('eu-'):
        return 'eu.'
    if region.startswith('ap-'):
        return 'apac.'
    return 'us.'


def model_request_fields(model_id):
    """Per-provider Converse request fields."""
    if 'openai.' in model_id:
        effort = os.environ.get('BEDROCK_REASONING_EFFORT', 'low')
        return {'additionalModelRequestFields': {'reasoning': {'effort': effort}}}
    return {}


def download_file_from_s3(bucket_name, file_key, local_path, filename):
    s3 = boto3.client('s3')
    # Wrap the S3 download_file call with exponential_backoff_retry
    exponential_backoff_retry(
        s3.download_file,
        bucket_name,
        file_key,
        local_path,
        retries=3,
        base_delay=1,
        backoff_factor=2
    )
    print(f"Filename: {filename}| Downloaded {file_key} from {bucket_name} to {local_path}")


def save_to_s3(local_path, bucket_name, file_key):
    s3 = boto3.client('s3')
    save_path = f"result/COMPLIANT_{file_key}"
    with open(local_path, "rb") as data:
        # Wrap the S3 upload_fileobj call with exponential_backoff_retry
        exponential_backoff_retry(
            s3.upload_fileobj,
            data,
            bucket_name,
            save_path,
            retries=3,
            base_delay=1,
            backoff_factor=2
        )
    return save_path


def set_custom_metadata(pdf_document, filename, title):
    # Set XML metadata for the PDF
    xmp_metadata = f'''<?xml version="1.0" encoding="UTF-8"?>
    <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
            xmlns:dc="http://purl.org/dc/elements/1.1/"
            xmlns:xmp="http://ns.adobe.com/xap/1.0/"
            xmlns:pdfuaid="http://www.aiim.org/pdfua/ns/id/">
        <rdf:Description rdf:about=""
            xmlns:dc="http://purl.org/dc/elements/1.1/">
            <dc:title>{title}</dc:title>
            <pdfuaid:part>1</pdfuaid:part>
            <pdfuaid:conformance>B</pdfuaid:conformance>
        </rdf:Description>
    </rdf:RDF>
    '''
    pdf_document.set_xml_metadata(xmp_metadata)
    
    # Update PDF metadata
    current_metadata = pdf_document.metadata
    current_metadata['title'] = title  # Update the title in the metadata
    pdf_document.set_metadata(current_metadata)
    print(f'Filename : {filename} | Metadata updated for the PDF with Title: {title}')


def parse_payload(payload):
    lines = payload.strip().split('\n')
    data = {}
    for line in lines:
        if line.startswith("Bucket:"):
            data['bucket'] = line.split("Bucket:")[1].strip()
        elif line.startswith("Merged File Key:"):
            data['merged_file_key'] = line.split("Merged File Key:")[1].strip()
        elif line.startswith("Merged File Name:"):
            data['merged_file_name'] = line.split("Merged File Name:")[1].strip()
        else:
            data['status'] = line.strip()
    return data


def extract_text_from_pdf(pdf_document):
    """
    Extracts text from the first page of a PDF. If the text on the first page
    has fewer than 50 words, extracts text from the second and third pages as well.

    Args:
        pdf_document (fitz.Document): PyMuPDF Document object.

    Returns:
        str: Extracted text from the relevant pages.
    """
    try:
        # Extract text from the first page
        first_page_text = pdf_document[0].get_text() if len(pdf_document) > 0 else ""
        word_count_first_page = len(first_page_text.split())
        
        if word_count_first_page >= 50 or len(pdf_document) == 1:
            # Return the first page text if it has enough words or if it's the only page
            return first_page_text
        else:
            # Extract text from the second and third pages if the first page is insufficient
            second_page_text = pdf_document[1].get_text() if len(pdf_document) > 1 else ""
            third_page_text = pdf_document[2].get_text() if len(pdf_document) > 2 else ""
            return "\n\n".join([first_page_text, second_page_text, third_page_text]).strip()
    except Exception as e:
        return f"An error occurred: {e}"


def generate_title(extracted_text, current_title):
    session = boto3.Session()
    region = session.region_name
    # Region for Bedrock calls (S3 stays in-region)
    bedrock_region = os.environ.get('BEDROCK_REGION') or region

    model_id = os.environ.get('BEDROCK_MODEL_ID') or f'{inference_profile_prefix(bedrock_region)}openai.gpt-5.6-luna'
    print(f"(generate_title) Model ID: {model_id} (region {bedrock_region})")

    client = boto3.client('bedrock-runtime', region_name=bedrock_region)
    prompt = f'''
    Using the following content extracted from the first two to three pages of a PDF document, generate a clear, concise, and descriptive title for the file. 
    The title should accurately summarize the primary focus of the document, be free of unnecessary jargon, and comply with WCAG 2.1 AA accessibility guidelines by being understandable and distinguishable.

    The current title below is the document's file name, not a real title. Replace it with a proper title based on the context unless it already reads as a complete, descriptive document title; a bare file name (with hyphens, underscores or a .pdf extension) never does.

    Current File Title: {current_title}
    Context for title generation: {extracted_text}
    Output only the title as the response and please do not reply with anything else except the generated title.
    '''

    # Construct the request payload
    request_payload = {
        'modelId': model_id,
        'messages': [
            {
                'role': 'user',
                'content': [{'text': prompt}]
            }
        ]
    }

    # Wrap the Bedrock client call with exponential_backoff_retry
    response = exponential_backoff_retry(
        client.converse,
        modelId=model_id,
        messages=request_payload['messages'],
        inferenceConfig={'maxTokens': 300},
        retries=3,
        base_delay=1,
        backoff_factor=2,
        **model_request_fields(model_id)
    )

    # Join all text blocks
    generated_title = "".join(block.get('text', '') for block in response['output']['message']['content'])
    if not generated_title.strip():
        raise ValueError(f"Model returned no text content (stopReason={response.get('stopReason')})")
    return generated_title.strip().strip('"')


def lambda_handler(event, context):
    try:
        payload = event.get("Payload")
        file_info = parse_payload(payload)
        print(f"(lambda_handler | Parsed file information: {file_info})")

        file_name = file_info['merged_file_name']
        local_path = f'/tmp/{file_name}'
        download_file_from_s3(file_info['bucket'], file_info['merged_file_key'], local_path, file_info['merged_file_name'])

        try:
            pdf_document = fitz.open(local_path)
        except Exception as e:
            print(f"(lambda_handler | Failed to open PDF file {file_name}: {e})")
            return {
                "statusCode": 500,
                "body": {
                    "error": f"Failed to open PDF file {file_name}.",
                    "details": f"{file_name} - {str(e)}"
                }
            }

        try:
            extracted_text = extract_text_from_pdf(pdf_document)
            print(f"(lambda_handler | Extracted text: {extracted_text})")
        except Exception as e:
            print(f"(lambda_handler | Failed to extract text from PDF: {e})")
            pdf_document.close()
            return {
                "statusCode": 500,
                "body": {
                    "error": "Failed to extract text from PDF.",
                    "details": f"{file_name} - {str(e)}"
                }
            }

        try:
            title = generate_title(extracted_text, file_name)
            print(f"(lambda_handler | Generated title: {title})")
        except Exception as e:
            print(f"(lambda_handler | Failed to generate title: {e})")
            pdf_document.close()
            return {
                "statusCode": 500,
                "body": {
                    "error": "Failed to generate title.",
                    "details": f"{file_name} - {str(e)}"
                }
            }

        try:
            set_custom_metadata(pdf_document, file_name, title)
            pdf_document.saveIncr()
            pdf_document.close()
        except Exception as e:
            print(f"(lambda_handler | Failed to set metadata or save PDF: {e})")
            pdf_document.close()
            return {
                "statusCode": 500,
                "body": {
                    "error": "Failed to set metadata or save PDF.",
                    "details": f"{file_name} - {str(e)}"
                }
            }

        try:
            save_path = save_to_s3(local_path, file_info['bucket'], file_name)
            print(f"(lambda_handler | Saved file to S3 at: {save_path})")
        except Exception as e:
            print(f"(lambda_handler | Failed to save file to S3: {e})")
            return {
                "statusCode": 500,
                "body": {
                    "error": "Failed to save file to S3.",
                    "details": f"{file_name} - {str(e)}"
                }
            }

        return {
            "statusCode": 200,
            "body": {
                "bucket": file_info['bucket'],
                "save_path": save_path,
                "title": title
            }
        }
    except Exception as e:
        print(f"(lambda_handler | General error in lambda_handler: {e})")
        return {
            "statusCode": 500,
            "body": {
                "error": "An unexpected error occurred.",
                "details": f"Filename: {file_info.get('merged_file_name','Unknown')} - {str(e)}"
            }
        }
