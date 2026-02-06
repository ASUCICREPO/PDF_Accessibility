"""
This AWS Lambda function is triggered by an S3 event when a PDF file is uploaded to a specified S3 bucket. 
The function performs the following operations:

1. Downloads the PDF file from S3.
2. Splits the PDF into chunks of specified page size (for example, one page per chunk).
3. Uploads each PDF chunk to a temporary location in the same S3 bucket.
4. Logs the processing status of each chunk and its upload to S3.
5. Starts an AWS Step Functions execution with metadata about the uploaded chunks.

"""
import json
import boto3
import urllib.parse
import io
import os

# Initialize AWS clients
cloudwatch = boto3.client('cloudwatch')
s3_client = boto3.client('s3')
stepfunctions = boto3.client('stepfunctions')

state_machine_arn = os.environ['STATE_MACHINE_ARN']

def log_chunk_created(filename):
    """
    Logs the creation of a PDF chunk.
    
    This function logs the filename and processing status for each chunk and indicates 
    successful upload of the chunk to S3. It also returns an HTTP status code and a message 
    confirming the update of the processing metric.
    
    Parameters:
        filename (str): The name of the file chunk being processed.

    Returns:
        dict: HTTP response with a status code and a message indicating the metric update.
    """
    print(f"File: {filename}, Status: Processing")
    print(f'Filename - {filename} | Uploaded {filename} to S3')
   
    return {
        'statusCode': 200,
        'body': 'Metric status updated to failed.'
    }

def split_pdf_into_pages(source_content, original_key, s3_client, bucket_name, pages_per_chunk):
    """
    Splits a PDF file into chunks of specified page size and uploads each chunk to S3.
    
    This function takes a PDF file's content, splits it into chunks of the specified number 
    of pages, and uploads each chunk back to the S3 bucket. It also returns metadata about 
    the uploaded chunks for further processing.
    
    Parameters:
        source_content (bytes): The binary content of the PDF file.
        original_key (str): The original S3 key of the PDF file.
        s3_client (boto3.client): The Boto3 S3 client instance for interacting with S3.
        bucket_name (str): The name of the S3 bucket.
        pages_per_chunk (int): The number of pages per chunk.

    Returns:
        list: A list of dictionaries containing metadata for each uploaded chunk.
    """
    from pypdf import PdfReader, PdfWriter
    
    reader = PdfReader(io.BytesIO(source_content))
    num_pages = len(reader.pages)
    file_basename = original_key.split('/')[-1].rsplit('.', 1)[0]
    
    chunks = []

    # Iterate through the PDF pages in chunks
    for start in range(0, num_pages, pages_per_chunk):
        output = io.BytesIO()
        writer = PdfWriter()

        # Add pages to the current chunk
        for i in range(start, min(start + pages_per_chunk, num_pages)):
            writer.add_page(reader.pages[i])

        writer.write(output)
        output.seek(0)

        # Create the filename and S3 key for this chunk
        chunk_index = start // pages_per_chunk + 1
        page_filename = f"{file_basename}_chunk_{chunk_index}.pdf"
        s3_key = f"temp/{file_basename}/{page_filename}"

        # Upload the chunk to S3
        s3_client.upload_fileobj(
            Fileobj=output,
            Bucket=bucket_name,
            Key=s3_key
        )
        print(f'Filename - {page_filename} | Uploaded {page_filename} to S3 at {s3_key}')
        # Store metadata for the chunk
        chunks.append({
            "s3_bucket": bucket_name,
            "s3_key": s3_key,
            "chunk_key": s3_key  # Key for the chunk
        })

    return chunks


def lambda_handler(event, context):
    """
    AWS Lambda function to handle S3 events and split uploaded PDF files into chunks.

    This function is triggered when a PDF file is uploaded to an S3 bucket. It downloads the 
    file from S3, splits the PDF into chunks (based on a page size), uploads each chunk back 
    to S3, and starts an AWS Step Functions execution to process the chunks. The function 
    also logs the processing status of each chunk.

    Parameters:
        event (dict): The S3 event that triggered the Lambda function, containing the S3 bucket 
                      and object key information.

    Returns:
        dict: HTTP response indicating the success or failure of the Lambda function execution.
    """
    try:
        
        print("Received event: " + json.dumps(event, indent=2))

        # Access the S3 event structure
        if 'Records' in event and len(event['Records']) > 0:
            s3_record = event['Records'][0]
            bucket_name = s3_record['s3']['bucket']['name']
            pdf_file_key = urllib.parse.unquote_plus(s3_record['s3']['object']['key'])
        else:
            raise ValueError("Event does not contain 'Records'. Check the S3 event structure.")
        file_basename = pdf_file_key.split('/')[-1].rsplit('.', 1)[0]


        s3 = boto3.client('s3')
        stepfunctions = boto3.client('stepfunctions')

        # Get the PDF file from S3
        response = s3.get_object(Bucket=bucket_name, Key=pdf_file_key)
        print(f'Filename - {pdf_file_key} | The response is: {response}')
        pdf_file_content = response['Body'].read()
  
        # Split the PDF into pages and upload them to S3
        chunks = split_pdf_into_pages(pdf_file_content, pdf_file_key, s3, bucket_name, 200)
        
        log_chunk_created(file_basename)

        # Trigger Step Function with the list of chunks
        response = stepfunctions.start_execution(
            stateMachineArn=state_machine_arn,
            input=json.dumps({"chunks": chunks, "s3_bucket": bucket_name})
        )
        print(f"Filename - {pdf_file_key} | Step Function started: {response['executionArn']}")

    except KeyError as e:
 
        print(f"File: {file_basename}, Status: Failed in split lambda function")
        print(f"Filename - {pdf_file_key} | KeyError: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error: Missing key in event: {str(e)}")
        }
    except ValueError as e:
  
        print(f"File: {file_basename}, Status: Failed in split lambda function")
        print(f"Filename - {pdf_file_key} | ValueError: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error: {str(e)}")
        }
    except Exception as e:

        print(f"File: {file_basename}, Status: Failed in split lambda function")
        print(f"Filename - {pdf_file_key} | Error occurred: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error processing event: {str(e)}")
        }

    return {
        'statusCode': 200,
        'body': json.dumps('Event processed successfully!')
    }
