"""
This script automates a comprehensive PDF processing pipeline that integrates Amazon S3, Adobe PDF Services, and
several Python libraries to handle various tasks such as downloading files, PDF manipulation, extraction of structured
data, and re-uploading the processed files back to S3.

Key Functionalities:
1. **Download from S3**:
    - Downloads a PDF file from an S3 bucket using Boto3.
    - The file is downloaded to the local environment for processing.

2. **PDF Processing**:
    - **Auto-Tagging for Accessibility**: Using Adobe PDF Services, the script automatically tags the PDF for accessibility,
      generating a compliant version with an optional report on tagging.
    - **Text and Table Extraction**: Text, tables, figures, and renditions are extracted from the PDF using Adobe PDF Services
      and saved as structured data.
    - **Table of Contents (TOC)**: A Table of Contents (TOC) is generated based on the headings in the extracted content and 
      added to the PDF.
    - **Custom Metadata**: XML metadata (such as title and dominant language) is injected into the PDF, improving its 
      accessibility and organization.

3. **Data Extraction**:
    - The script extracts images and other data from Excel files related to the PDF and uploads them to the S3 bucket.
    - It also handles unzipping files and organizing extracted content.

4. **Re-Upload to S3**:
    - After processing, the updated PDF (with metadata, TOC, and accessibility tagging) is uploaded back to S3 with a 
      new filename.
    - Extracted images and structured data are uploaded in organized directories in S3.

5. **Logging**:
    - Extensive logging is implemented throughout the script for tracking file names, successful operations, errors, 
      and results.
    - Logs key actions such as file downloads, metadata updates, file extraction, and final uploads.

6. **Additional Features**:
    - The script utilizes AWS Comprehend to detect the dominant language from extracted text and incorporates this 
      information into the PDF’s metadata.
    - Unzipped files are managed and organized into respective directories, and structured data (such as tables) is 
      processed for additional metadata and TOC generation.

Libraries and Services:
- **Boto3**: AWS SDK for Python to interact with S3.
- **PyMuPDF**: For editing and updating PDF files, including adding TOC and custom metadata.
- **OpenPyXL**: For extracting images from Excel files.
- **Adobe PDF Services**: Handles advanced PDF operations like autotagging for accessibility, extracting structured data 
  (tables, text, and figures), and generating reports.
- **AWS Comprehend**: For detecting the dominant language in extracted text.

Environment Variables Required:
- `S3_BUCKET_NAME`: The name of the S3 bucket to download and upload the PDF file.
- `S3_FILE_KEY`: The key (path) of the PDF file in the S3 bucket.

This script is ideal for batch processing of PDFs that need to be made accessible, tagged, and analyzed for further use
in structured formats. It handles compliance with accessibility standards and ensures easy re-upload of enhanced PDFs 
and related content.
"""

import pandas as pd
import openpyxl
import ast
import os
import boto3
import logging
import json
import sys
from botocore.exceptions import ClientError
import sqlite3
import pymupdf
import json
import re
import zipfile
from pypdf import PdfReader, PdfWriter

from adobe.pdfservices.operation.auth.service_principal_credentials import ServicePrincipalCredentials
from adobe.pdfservices.operation.exception.exceptions import ServiceApiException, ServiceUsageException, SdkException
from adobe.pdfservices.operation.pdf_services_media_type import PDFServicesMediaType
from adobe.pdfservices.operation.io.cloud_asset import CloudAsset
from adobe.pdfservices.operation.io.stream_asset import StreamAsset
from adobe.pdfservices.operation.pdf_services import PDFServices, ClientConfig
from adobe.pdfservices.operation.pdfjobs.jobs.extract_pdf_job import ExtractPDFJob
from adobe.pdfservices.operation.pdfjobs.params.extract_pdf.extract_element_type import ExtractElementType
from adobe.pdfservices.operation.pdfjobs.params.extract_pdf.extract_pdf_params import ExtractPDFParams
from adobe.pdfservices.operation.pdfjobs.params.extract_pdf.extract_renditions_element_type import ExtractRenditionsElementType
from adobe.pdfservices.operation.pdfjobs.result.extract_pdf_result import ExtractPDFResult
from adobe.pdfservices.operation.pdfjobs.jobs.autotag_pdf_job import AutotagPDFJob
from adobe.pdfservices.operation.pdfjobs.params.autotag_pdf.autotag_pdf_params import AutotagPDFParams
from adobe.pdfservices.operation.pdfjobs.result.autotag_pdf_result import AutotagPDFResult

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

s3 = boto3.client('s3')

def download_file_from_s3(bucket_name,file_base_name, file_key, local_path):
    """
    Download a file from an S3 bucket.
    
    Args:
        bucket_name (str): The S3 bucket name.
        file_base_name (str): The base name of the file.
        file_key (str): The key (path) of the file in the S3 bucket.
        local_path (str): The local path where the file will be saved.
    """
    logging.info(f"File key in the download_file_from_s3: {file_key}")
    s3.download_file(bucket_name, f"temp/{file_base_name}/{file_key}", local_path)
    logging.info(f"Downloaded {file_key} from {bucket_name} to {local_path}")

def save_to_s3(filename, bucket_name, folder_name,file_basename, file_key):
    """
    Uploads a file to an S3 bucket.
    
    Args:
        filename (str): The path of the file to upload.
        bucket_name (str): The S3 bucket name.
        folder_name (str): The folder where the file will be uploaded.
        file_basename (str): The base name of the file.
        file_key (str): The key (path) where the file will be uploaded.
    """

    with open(filename, "rb") as data:
        s3.upload_fileobj(data, bucket_name, f"temp/{file_basename}/{folder_name}/COMPLIANT_{file_key}")


def get_secret(basefilename):
    """
    Retrieves client credentials from AWS Secrets Manager.
    
    Returns:
        tuple: (client_id, client_secret)
    """
    secret_name = "/myapp/client_credentials"
    region_name = "us-east-1"


    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        logging.info(f'Filename : {basefilename} | Error: {e}')
        

    secret = get_secret_value_response['SecretString']
    secret_dict = json.loads(secret)
    
    client_id = secret_dict['client_credentials']['PDF_SERVICES_CLIENT_ID']
    client_secret = secret_dict['client_credentials']['PDF_SERVICES_CLIENT_SECRET']
    
    return client_id, client_secret

def add_viewer_preferences(pdf_path, filename):
    reader = PdfReader(pdf_path)
    writer = PdfWriter()

    # Add all pages to the writer
    for page in reader.pages:
        writer.add_page(page)

    writer.create_viewer_preferences()
    writer.viewer_preferences.display_doctitle = True

    # Write the updated PDF to a file
    with open(filename, "wb") as f:
        writer.write(f)
    logger.info(f'Filename : {filename} | Viewer preferences added to the PDF')

def autotag_pdf_with_options(filename, client_id, client_secret):
    try:
        with open(filename, 'rb') as file:
            input_stream = file.read()
        

        # Initial setup, create credentials instance
        credentials = ServicePrincipalCredentials(
            client_id=client_id,
            client_secret=client_secret
        )
        client_config = ClientConfig(
            connect_timeout=8000,
            read_timeout=40000
        )

        # Creates a PDF Services instance
        pdf_services = PDFServices(credentials=credentials, client_config=client_config)

        # Creates an asset(s) from source file(s) and upload
        input_asset = pdf_services.upload(input_stream=input_stream,
                                        mime_type=PDFServicesMediaType.PDF)

        # Create parameters for the job
        autotag_pdf_params = AutotagPDFParams(
            generate_report=True,
            shift_headings=True
        )

        # Creates a new job instance
        autotag_pdf_job = AutotagPDFJob(input_asset=input_asset,
                                        autotag_pdf_params=autotag_pdf_params)

        # Submit the job and gets the job result
        location = pdf_services.submit(autotag_pdf_job)
        pdf_services_response = pdf_services.get_job_result(location, AutotagPDFResult)

        # Get content from the resulting asset(s)
        result_asset: CloudAsset = pdf_services_response.get_result().get_tagged_pdf()
        result_asset_report: CloudAsset = pdf_services_response.get_result().get_report()
        stream_asset: StreamAsset = pdf_services.get_content(result_asset)
        stream_asset_report: StreamAsset = pdf_services.get_content(result_asset_report)

        # Creates an output stream and copy stream asset's content to it
        os.makedirs("output/AutotagPDF", exist_ok=True)
        output_file_path = filename
        output_file_path_report = f"output/AutotagPDF/{filename}.xlsx"

        with open(output_file_path, "wb") as file:
            file.write(stream_asset.get_input_stream())
        with open(output_file_path_report, "wb") as file:
            file.write(stream_asset_report.get_input_stream())

    except (ServiceApiException, ServiceUsageException, SdkException) as e:
        logging.exception(f'Filename : {filename} | Exception encountered while executing operation: {e}')
def extract_api(filename, client_id, client_secret):
    try:
        with open(filename, 'rb') as file:
            input_stream = file.read()

        # Initial setup, create credentials instance
        credentials = ServicePrincipalCredentials(
            client_id=client_id,
            client_secret=client_secret
        )
        client_config = ClientConfig(
            connect_timeout=4000,
            read_timeout=40000
            )
        # Creates a PDF Services instance
        pdf_services = PDFServices(credentials=credentials, client_config=client_config)

        # Creates an asset(s) from source file(s) and upload
        input_asset = pdf_services.upload(input_stream=input_stream, mime_type=PDFServicesMediaType.PDF)

        # Create parameters for the job
        extract_pdf_params = ExtractPDFParams(
            elements_to_extract=[ExtractElementType.TEXT, ExtractElementType.TABLES],
            elements_to_extract_renditions=[ExtractRenditionsElementType.TABLES, ExtractRenditionsElementType.FIGURES],
        )

        # Creates a new job instance
        extract_pdf_job = ExtractPDFJob(input_asset=input_asset, extract_pdf_params=extract_pdf_params)

        # Submit the job and gets the job result
        location = pdf_services.submit(extract_pdf_job)
        pdf_services_response = pdf_services.get_job_result(location, ExtractPDFResult)

        # Get content from the resulting asset(s)
        result_asset: CloudAsset = pdf_services_response.get_result().get_resource()
        stream_asset: StreamAsset = pdf_services.get_content(result_asset)

        # Creates an output stream and copy stream asset's content to it
        os.makedirs("output/ExtractTextInfoFromPDF", exist_ok=True)
        output_file_path = f"output/ExtractTextInfoFromPDF/extract${filename}.zip"
        with open(output_file_path, "wb") as file:
            file.write(stream_asset.get_input_stream())

    except (ServiceApiException, ServiceUsageException, SdkException) as e:
        logging.exception(f'Exception encountered while executing operation: {e}')

def unzip_file(filename,zip_path, extract_to):
    """
    Unzips a zip file to a specified directory.
    
    Args:
        zip_path (str): The path of the zip file.
        extract_to (str): The directory where the contents will be extracted.
    """
    if not os.path.exists(zip_path):
        raise FileNotFoundError(f"The file {zip_path} does not exist.")
    os.makedirs(extract_to, exist_ok=True)

    # Open the ZIP file
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        # Extract all contents
        zip_ref.extractall(extract_to)
        logging.info(f'Filename : {filename} |Files extracted to {extract_to}')

def add_toc_to_pdf(filename,pdf_document,data):
    """
    Adds a Table of Contents (TOC) to a PDF document based on the provided entries.
    """
    bookmarks = []
    for element in data.get("elements", []):
        path = element.get("Path", "")
        if re.search(r'H[1-4]', path) and "Text" in element:
            bookmarks.append((element["Text"], element["Page"] + 1))
        else:
            # Optional: Log elements without 'Text' or not matching headings
            if "Text" not in element:
                logging.debug(f"Element with ObjectID {element.get('ObjectID')} has no 'Text' key.")
            if not re.search(r'H[1-4]', path):
                logging.debug(f"Element with ObjectID {element.get('ObjectID')} does not match heading pattern.")

    # Create a list of toc entries in the format required by PyMuPDF
    toc_list = []
    for title, page_number in bookmarks:
        # Page numbers are 0-indexed in PyMuPDF
        toc_list.append([1, title, page_number])
    # Add TOC entries
    pdf_document.set_toc(toc_list)
    logging.info(f'Filename : {filename} |TOC entries added to the PDF')

# Currently done by Adobe API(May be required in the future)
def set_language_comprehend(filename,data,pdf_document):
    concatenated_text = ""
    for element in data['elements']:
        if 'Text' in element:
            concatenated_text += element['Text'] + " "

    # Remove trailing whitespace
    concatenated_text = concatenated_text.strip()
    
    comprehend = boto3.client('comprehend')
    response = comprehend.detect_dominant_language(Text=concatenated_text)
    languages = response['Languages']
    # Assuming the dominant language is the one with the highest score
    dominant_language = max(languages, key=lambda lang: lang['Score'])

    # Set the language in the PDF metadata
    pdf_document.set_language(dominant_language['LanguageCode'])
    logging.info(f'Filename : {filename} | Language set to {dominant_language["LanguageCode"]}')

def extract_images_from_extract_api(filename):
    # unzip_file(file_path, output_dir)
    
    with open(f"output/zipfile/{filename}/structuredData.json", "r") as file:
        data = json.load(file)
    by_page = {}

    for ele in data["elements"]:
        if "Page" in ele:
            if ele["Page"] not in by_page:
                by_page[ele["Page"]] = []
            by_page[ele["Page"]].append(ele)

    
    return by_page

def natural_sort_key(filename):
        # Extract numbers from the file name using regex and convert to int for sorting
        return [int(num) if num.isdigit() else num for num in re.split(r'(\d+)', filename)]

def is_bbox_match(api_bbox, excel_bbox,tol=7):
    """
    Returns True if the differences between the API bbox and the converted Excel bbox 
    are all within the specified tolerance.
    """
    api_left = round(api_bbox[0])
    api_bottom = round(api_bbox[1])
    api_right = round(api_bbox[2])
    api_top = round(api_bbox[3])
    
    api_width  = api_right - api_left
    api_height = api_top - api_bottom
    
    diff_width = abs(api_width - excel_bbox[2])
    diff_height = abs(api_height - excel_bbox[3])
    
    diff_x = abs(api_left-excel_bbox[0])
    diff_y = abs(api_top-excel_bbox[1])
    return (diff_width <= tol and diff_height <= tol and
            diff_x <= tol and diff_y <= tol)

def create_sqlite_db(by_page, filename, images_output_dir, object_ids, image_paths,
                     page_num_img, parsed_cordinates, bucket_name, s3_folder_autotag, file_key, object_ids_cords):
    # Build the SQLite database file path and create a new database.
    db_path = os.path.join(images_output_dir, "temp_images_data.db")
    if os.path.exists(db_path):
        os.remove(db_path)
        logging.info(f'Filename : {filename} | Removed existing SQLite DB')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS image_data (
            objid TEXT,
            img_path TEXT,
            prev TEXT,
            current TEXT,
            next TEXT,
            context TEXT
        )
    """)
    
    # This set ensures that a candidate from the API is only assigned once.
    assigned_candidates = set()

    # Process each Excel row (each image from Excel)
    for objid, pg_num, excel_bbox in zip(object_ids, page_num_img, object_ids_cords):
        if pg_num not in by_page:
            logging.warning(f"Page {pg_num} not found in API data for file {filename}.")
            context = "No API data for this page."
        else:
            # --------------------------------------------------------------------
            # 1. Identify the current candidate using bounding box matching.
            # --------------------------------------------------------------------
            candidates = []

            for page, val in by_page.items():
                for ele in val:
                    # Enforce one-to-one mapping: skip already assigned elements.
                    if id(ele) in assigned_candidates:
                        logging.debug(f"Candidate {ele.get('ObjectID')} already assigned. Skipping.")
                        continue
                    if "filePaths" not in ele:
                        logging.debug(f"Candidate {ele.get('ObjectID')} has no filePaths. Skipping.")
                        continue

                    # Consider only file paths with image extensions.
                    paths = ele["filePaths"]
                    image_paths_list = [p for p in paths if p.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))]
                    if not image_paths_list:
                        logging.debug(f"Candidate {ele.get('ObjectID')} has no valid image file paths. Skipping.")
                        continue

                    candidate_image_path = image_paths_list[0]
                    if "tables" in candidate_image_path.lower():
                        logging.debug(f"Candidate {ele.get('ObjectID')} is from a tables directory. Skipping.")
                        continue

                    # Make sure the candidate has bounding box data.
                    if "attributes" not in ele or "BBox" not in ele["attributes"]:
                        logging.debug(f"Candidate {ele.get('ObjectID')} has no bounding box data. Skipping.")
                        continue

                    # Check if the candidate's bounding box matches the Excel bounding box.
                    if is_bbox_match(ele["Bounds"], excel_bbox[1], tol=7):
                        ele["objid"] = excel_bbox[0]
                        candidates.append(ele)

            if len(candidates) == 1:
                current_candidate = candidates[0]
            elif len(candidates) > 1:
                current_candidate = candidates[0]
            else:
                current_candidate = None

            if not current_candidate:
                continue
            if current_candidate:
                assigned_candidates.add(id(current_candidate))
            # --------------------------------------------------------------------
            # 2. Build the whole page context string.
            # --------------------------------------------------------------------
            # The context string is built by iterating over all API elements for the page,
            # preserving their original order.
            context_parts = []
            for ele in by_page[pg_num]:
                # Append any text from the element.
                if "Text" in ele and ele["Text"]:
                    context_parts.append(ele["Text"])
                # If the element has image file paths (and valid image extensions), append an image marker.
                if "filePaths" in ele:
                    valid_paths = [p for p in ele["filePaths"]
                                   if p.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))
                                   and "tables" not in p.lower()]
                    if valid_paths:
                        image_name = os.path.basename(valid_paths[0])
                        if current_candidate is not None and id(ele) == id(current_candidate):
                            # This is the current image (the one matching the Excel row).
                            marker = f"<IMAGE INTERESTED>{image_name}</IMAGE INTERESTED>"
                        else:
                            # Other images on the page.
                            marker = f"<OTHER IMAGE>{image_name}</OTHER IMAGE>"
                        context_parts.append(marker)
            
            # Join all parts with a space.
            context = " ".join(context_parts)
        # Debug prints.
        print(f"{'<IMAGE INTERESTED>' in context}")
        print("context:", context)
        print(" ======================")
        # Insert the data into the SQLite database.
        cursor.execute("""
            INSERT INTO image_data (objid, img_path, context)
            VALUES (?, ?, ?)
        """, (
            current_candidate["objid"],
            current_candidate["filePaths"][0].split("/")[-1],
            context
        ))
        print("Added in the database: ", current_candidate["objid"],
            current_candidate["filePaths"][0].split("/")[-1])
    conn.commit()
    conn.close()
    logging.info(f'Filename : {filename} | SQLite DB created with image data')
    
    # Upload the SQLite DB to S3.
    s3.upload_file(os.path.join(images_output_dir, "temp_images_data.db"),
                     bucket_name,
                     f'{s3_folder_autotag}/{file_key}_temp_images_data.db')
    logging.info(f'Filename : {filename} | Uploaded SQLite DB to S3')


def extract_images_from_excel(filename, figure_path, autotag_report_path, images_output_dir, bucket_name, s3_folder_autotag, file_key):
    """
    Extract images from an Excel file and save them to a directory and upload them to S3.

    Args:
        filename (str): The filename (used for logging).
        figure_path (str): Path to figures (unused in this snippet).
        autotag_report_path (str): Path to the Excel file.
        images_output_dir (str): Directory to save the images.
        bucket_name (str): The S3 bucket.
        s3_folder_autotag (str): The S3 folder for autotag output.
        file_key (str): File key for S3 naming.
    """
    try:
        logging.info(f'Filename : {filename} | Extracting the images from excel file...')
        
        # Load the workbook and get the sheet (Images are in the "Figures" sheet)
        wb = openpyxl.load_workbook(autotag_report_path)
        wb.close()
        sheet = wb["Figures"]
        logging.info(f'Filename : {filename} | Sheet: {sheet.title}')
        logging.info(f'Filename : {filename} | Number of images: {len(sheet._images)}')
        
        # Load the workbook into a DataFrame for additional details.
        df = pd.read_excel(autotag_report_path, sheet_name="Figures")
        logging.info(f'Filename : {filename} | DF loaded: {str(df)}')
        # Get the object IDs
        object_ids = df["Unnamed: 4"].dropna().values[1:]
        # Get page numbers for images (adjusting for 0-indexing)
        page_num_img = df["Figures and Alt Text (excludes artifacts and decorative images)"].dropna().values[2:].astype(int)
        page_num_img = [int(i)-1 for i in page_num_img]
        
        os.makedirs(images_output_dir, exist_ok=True)

        by_page = extract_images_from_extract_api(filename)
        image_paths = []
        coordinates = df["Unnamed: 3"].dropna().values[1:]
        parsed_cordinates = [ast.literal_eval(item) for item in coordinates]
        object_ids_cords = [(objid, cords) for objid, cords in zip(object_ids, parsed_cordinates)]
        print("Object IDs and Coordinates:", object_ids_cords)
        logging.info(f'Filename : {filename} | Sheet: {sheet} , Sheet Images: {sheet._images}')

        # Loop through all images in the sheet and save them locally.
        for idx, img in enumerate(sheet._images):
            img_type = img.path.split('.')[-1]
            img_path = os.path.join(images_output_dir, f'image_{idx + 1}.{img_type}')
            image_paths.append(img_path)
            with open(img_path, 'wb') as f:
                f.write(img._data())
            logging.info(f'Filename : {filename} | Image {idx + 1} saved as {img_path}')
        
        image_paths = [
            os.path.join(figure_path, f)
            for f in sorted(os.listdir(figure_path), key=natural_sort_key)
        ]
        
        for img_path in image_paths:
            s3.upload_file(img_path, bucket_name, f'{s3_folder_autotag}/images/{file_key}_{os.path.basename(img_path)}')
            logging.info(f'Filename : {filename} | Uploaded image to S3')
        logging.info(f'Filename : {filename} | Object IDs: {object_ids} : Image Paths: {image_paths}')

        create_sqlite_db(by_page, filename, images_output_dir, object_ids, image_paths, page_num_img, parsed_cordinates, bucket_name, s3_folder_autotag, file_key, object_ids_cords)
    except Exception as e:
        db_path = os.path.join(images_output_dir, "temp_images_data.db")
        if os.path.exists(db_path):
            os.remove(db_path)
            logging.info(f'Filename : {filename} | Removed existing SQLite DB')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS image_data (
                objid TEXT,
                img_path TEXT,
                prev TEXT,
                current TEXT,
                next TEXT,
                context TEXT
            )
        """)
        
        conn.commit()
        conn.close()
        logging.info(f'Filename : {filename} | SQLite DB created with image data')
        
        # Upload the SQLite DB to S3.
        s3.upload_file(os.path.join(images_output_dir, "temp_images_data.db"),
                        bucket_name,
                        f'{s3_folder_autotag}/{file_key}_temp_images_data.db')
        logging.info(f'Filename : {filename} | Uploaded SQLite DB to S3 With No Images')

def main():
    """
    Main function that coordinates the downloading, processing, and uploading of PDF files and associated content.
    """

    try:    
        bucket_name = os.getenv('S3_BUCKET_NAME')
        file_key = os.getenv('S3_FILE_KEY').split('/')[2]
        file_base_name = os.getenv('S3_FILE_KEY').split('/')[1]
        logging.info(f'Filename : {file_key} | Bucket Name: {bucket_name}')
        if not bucket_name or not file_key:
            logging.info("Error: S3_BUCKET_NAME and S3_FILE_KEY environment variables are required.")
            return

        # Define the local file path where the file will be saved
        local_file_path = os.path.basename(file_key)  # Save the file with its original name
        
        # Download the file from S3
        download_file_from_s3(bucket_name,file_base_name, file_key, local_file_path)

        base_filename = os.path.basename(local_file_path)
        filename = "COMPLIANT_" + base_filename

        client_id, client_secret = get_secret(base_filename)

        add_viewer_preferences(local_file_path, filename)

        autotag_pdf_with_options(filename, client_id, client_secret)

        extract_api(filename, client_id, client_secret)

        extract_api_zip_path = f"output/ExtractTextInfoFromPDF/extract${filename}.zip"
        extract_to = f"output/zipfile/{filename}"
        unzip_file(filename,extract_api_zip_path,extract_to)

        with open(f"output/zipfile/{filename}/structuredData.json") as file:
            data = json.load(file)

        pdf_document = pymupdf.open(filename)

        # Add TOC entries
        add_toc_to_pdf(filename,pdf_document,data)

        pdf_document.saveIncr()
        pdf_document.close()
        save_to_s3(filename, bucket_name, "output_autotag",file_base_name, file_key)

        logging.info(f"PDF saved with updated metadata and TOC. File location: COMPLIANT_{file_key}")

        figure_path = f"{extract_to}/figures"
        autotag_report_path = f"output/AutotagPDF/{filename}.xlsx"
        images_output_dir = "output/zipfile/images"

        s3_folder_autotag = f"temp/{file_base_name}/output_autotag"
        extract_images_from_excel(filename,figure_path,autotag_report_path,images_output_dir,bucket_name,s3_folder_autotag,file_key)
        
        logging.info(f'Filename : {file_key} | Processing completed for pdf file')
    except Exception as e:
        logger.info(f"File: {file_base_name}, Status: Failed in First ECS task")
        logger.info(f"Filename : {file_key} | Error: {e}")
        sys.exit(1)
        
if __name__ == "__main__":
    main()