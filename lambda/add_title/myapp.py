import boto3
import json
import os

def download_file_from_s3(bucket_name, file_key, local_path,filename):
    s3 = boto3.client('s3')
    s3.download_file(bucket_name, file_key, local_path)
    print(f"Filename: {filename}| Downloaded {file_key} from {bucket_name} to {local_path}")

def save_to_s3(local_path, bucket_name, file_key):
    s3 = boto3.client('s3')
    save_path = f"result/COMPLIANT_{file_key}"
    with open(local_path, "rb") as data:
        s3.upload_fileobj(data, bucket_name, save_path)
    return save_path
    
def set_custom_metadata(pdf_document,filename, title):
    # Set XML metadata for the PDF
    xmp_metadata = f'''<?xml version="1.0" encoding="UTF-8"?>
    <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
            xmlns:dc="http://purl.org/dc/elements/1.1/"
            xmlns:xmp="http://ns.adobe.com/xap/1.0/">
        <rdf:Description rdf:about=""
            xmlns:dc="http://purl.org/dc/elements/1.1/">
            <dc:title>{title}</dc:title>
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
    has fewer than 50 words, extracts text from the second page as well.

    Args:
        file_path (str): Path to the PDF file.

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
            # Extract text from the second page if the first page is insufficient
            second_page_text = pdf_document[1].get_text() if len(pdf_document) > 1 else ""
            return first_page_text + "\n\n" + second_page_text
    except Exception as e:
        return f"An error occurred: {e}"


def generate_title(extracted_text):
    session = boto3.Session()

    # Retrieve the current region
    region = session.region_name

    # Create an STS client
    sts_client = session.client('sts')

    # Retrieve the account ID
    account_id = sts_client.get_caller_identity()['Account']

    # Define the model name and version
    model_name = 'us.anthropic.claude-3-5-sonnet-20241022-v2:0'

    # Construct the model_id
    model_id = f'arn:aws:bedrock:{region}:{account_id}:inference-profile/{model_name}'
    print(model_id)
    
    client = boto3.client('bedrock-runtime', region_name=region)
    prompt = f'''
    Using the following content extracted from the first two pages of a PDF document, generate a clear, concise, and descriptive title for the file. 
    The title should accurately summarize the primary focus of the document, be free of unnecessary jargon, and comply with WCAG 2.1 AA accessibility guidelines by being understandable and distinguishable.
    Context for title generation: {extracted_text}
    Output only the title as the response and please please dont reply with anything else except the generated title.
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

    # Send the request to the Converse API
    response = client.converse(
        modelId=model_id,
        messages=request_payload['messages']
    )

    # Extract and return the generated title
    generated_title = response['output']['message']['content'][0]['text']
    return generated_title.strip()

def lambda_handler(event, context):
    import fitz

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
            title = generate_title(extracted_text)
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
                "details": f"{file_name} - {str(e)}"
            }
        }

