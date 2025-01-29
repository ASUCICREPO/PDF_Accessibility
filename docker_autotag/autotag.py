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


import os
import boto3
import logging
import json
import sys
from botocore.exceptions import ClientError
import sqlite3


logging.basicConfig(level=logging.INFO)

def download_file_from_s3(bucket_name,file_base_name, file_key, local_path):
    """
    Download a file from an S3 bucket.
    
    Args:
        bucket_name (str): The S3 bucket name.
        file_base_name (str): The base name of the file.
        file_key (str): The key (path) of the file in the S3 bucket.
        local_path (str): The local path where the file will be saved.
    """
    s3 = boto3.client('s3')
    logging.info(f"File key in the function: {file_key}")
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

    s3 = boto3.client('s3')

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


def pdf_processing(pdf_path, file_base_name, file_key, bucket_name):
    """
    Processes the downloaded PDF file, adds TOC, custom metadata, and extracts text, tables, and images.
    
    Args:
        pdf_path (str): Path to the downloaded PDF file.
        file_base_name (str): The base name of the file.
        file_key (str): The key of the file in the S3 bucket.
        bucket_name (str): The S3 bucket name.
    """
    import pymupdf
    import logging
    import os
    from datetime import datetime
    import json
    import re
    import zipfile
    from pypdf import PdfReader, PdfWriter
    import boto3
    from adobe.pdfservices.operation.auth.service_principal_credentials import ServicePrincipalCredentials
    from adobe.pdfservices.operation.exception.exceptions import ServiceApiException, ServiceUsageException, SdkException
    from adobe.pdfservices.operation.pdf_services_media_type import PDFServicesMediaType
    from adobe.pdfservices.operation.io.cloud_asset import CloudAsset
    from adobe.pdfservices.operation.io.stream_asset import StreamAsset
    from adobe.pdfservices.operation.pdf_services import PDFServices, ClientConfig
    from adobe.pdfservices.operation.pdfjobs.jobs.extract_pdf_job import ExtractPDFJob
    from adobe.pdfservices.operation.pdfjobs.params.extract_pdf.extract_element_type import ExtractElementType
    from adobe.pdfservices.operation.pdfjobs.params.extract_pdf.extract_pdf_params import ExtractPDFParams
    from adobe.pdfservices.operation.pdfjobs.params.extract_pdf.extract_renditions_element_type import \
        ExtractRenditionsElementType
    from adobe.pdfservices.operation.pdfjobs.result.extract_pdf_result import ExtractPDFResult
    from adobe.pdfservices.operation.pdfjobs.jobs.autotag_pdf_job import AutotagPDFJob
    from adobe.pdfservices.operation.pdfjobs.params.autotag_pdf.autotag_pdf_params import AutotagPDFParams
    from adobe.pdfservices.operation.pdfjobs.result.autotag_pdf_result import AutotagPDFResult

    
    base_filename = os.path.basename(pdf_path)
    filename = "COMPLIANT_" + base_filename
    client_id, client_secret = get_secret(base_filename)

    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    logging.basicConfig(level=logging.INFO)

    # Add all pages to the writer
    for page in reader.pages:
        writer.add_page(page)

    writer.create_viewer_preferences()
    writer.viewer_preferences.display_doctitle = True

    # Write the updated PDF to a file
    with open(filename, "wb") as f:
        writer.write(f)

    # Initialize the logger
    logging.basicConfig(level=logging.INFO)

    class AutotagPDFWithOptions:
        def __init__(self):
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
                output_file_path = self.create_output_file_path()
                output_file_path_report = self.create_output_file_path_for_tagging_report()
                with open(output_file_path, "wb") as file:
                    file.write(stream_asset.get_input_stream())
                with open(output_file_path_report, "wb") as file:
                    file.write(stream_asset_report.get_input_stream())

            except (ServiceApiException, ServiceUsageException, SdkException) as e:
                logging.exception(f'Filename : {filename} | Exception encountered while executing operation: {e}')
        # Generates a string containing a directory structure and file name for the output file
        @staticmethod
        def create_output_file_path() -> str:
            now = datetime.now()
            time_stamp = now.strftime("%Y-%m-%dT%H-%M-%S")
            os.makedirs("output/AutotagPDF", exist_ok=True)
            return f"{filename}"

        # Generates a string containing a directory structure and file name for the tagging report output
        @staticmethod
        def create_output_file_path_for_tagging_report() -> str:
            now = datetime.now()
            time_stamp = now.strftime("%Y-%m-%dT%H-%M-%S")
            os.makedirs("output/AutotagPDF", exist_ok=True)
            return f"output/AutotagPDF/{filename}.xlsx"

    class ExtractTextTableInfoWithFiguresTablesRenditionsFromPDF:
        def __init__(self):
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
                output_file_path = self.create_output_file_path()
                with open(output_file_path, "wb") as file:
                    file.write(stream_asset.get_input_stream())

            except (ServiceApiException, ServiceUsageException, SdkException) as e:
                logging.exception(f'Exception encountered while executing operation: {e}')

        # Generates a string containing a directory structure and file name for the output file
        @staticmethod
        def create_output_file_path() -> str:
            now = datetime.now()
            time_stamp = now.strftime("%Y-%m-%dT%H-%M-%S")
            os.makedirs("output/ExtractTextInfoFromPDF", exist_ok=True)
            return f"output/ExtractTextInfoFromPDF/extract${filename}.zip"
        

    AutotagPDFWithOptions()
    ExtractTextTableInfoWithFiguresTablesRenditionsFromPDF()


    def unzip_file(zip_path, extract_to):
        """
        Unzips a zip file to a specified directory.
        
        Args:
            zip_path (str): The path of the zip file.
            extract_to (str): The directory where the contents will be extracted.
        """
        # Ensure the extraction directory exists
        os.makedirs(extract_to, exist_ok=True)

        # Open the ZIP file
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Extract all contents
            zip_ref.extractall(extract_to)
            logging.info(f'Filename : {filename} |Files extracted to {extract_to}')

    zip_path = f"output/ExtractTextInfoFromPDF/extract${filename}.zip"
    os.makedirs(f"output/zipfile/{filename}", exist_ok=True)
    extract_to = f"output/zipfile/{filename}"
    unzip_file(zip_path, extract_to)

    with open(f"output/zipfile/{filename}/structuredData.json") as file:
        data = json.load(file)

    # Extract bookmarks based on headings found in the structured data
    # bookmarks = [(element["Text"], element["Page"] + 1) for element in data["elements"] if re.search(r'H[1-6]', element["Path"])]
    
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
    def add_toc_to_pdf(pdf_document, toc_entries):
        # Create a list of toc entries in the format required by PyMuPDF
        toc_list = []
        for title, page_number in toc_entries:
            # Page numbers are 0-indexed in PyMuPDF
            toc_list.append([1, title, page_number])
        # Add TOC entries
        pdf_document.set_toc(toc_list)
        logging.info(f'Filename : {filename} |TOC entries added to the PDF')


    # Adobe API sets all the metadata that is why it is not required (But may be required in the future)
    def set_custom_metadata(pdf_document, base_filename):
        # Set XML metadata for the PDF
        xmp_metadata = f'''<?xml version="1.0" encoding="UTF-8"?>
        <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
                xmlns:dc="http://purl.org/dc/elements/1.1/"
                xmlns:xmp="http://ns.adobe.com/xap/1.0/">
            <rdf:Description rdf:about=""
                xmlns:dc="http://purl.org/dc/elements/1.1/">
                <dc:title>{base_filename}</dc:title>
            </rdf:Description>
        </rdf:RDF>
        '''
        pdf_document.set_xml_metadata(xmp_metadata)
        
        # Update PDF metadata
        current_metadata = pdf_document.metadata
        current_metadata['title'] = base_filename  # Update the title in the metadata
        pdf_document.set_metadata(current_metadata)
        logging.info(f'Filename : {filename} | Metadata updated for the PDF')

    # Currently done by Adobe API(May be required in the future)
    def set_language_comprehend(data,pdf_document):
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

    # Open the source PDF
    pdf_document = pymupdf.open(filename)

    # Add TOC entries
    add_toc_to_pdf(pdf_document, bookmarks)

    # Save the updated PDF and close the document
    pdf_document.saveIncr()
    pdf_document.close()



    save_to_s3(filename, bucket_name, "output_autotag",file_base_name, file_key)
    logging.info(f"PDF saved with updated metadata and TOC. File location: COMPLIANT_{file_key}")
    import os
    import pandas as pd
    import openpyxl
    from openpyxl.drawing.image import Image
    import logging

    import ast
    logging.basicConfig(level=logging.INFO)
    import zipfile
    import os

    def unzip_file(zip_file_path, extract_to):
        # Check if the zip file exists
        if not os.path.exists(zip_file_path):
            raise FileNotFoundError(f"The file {zip_file_path} does not exist.")
        
        # Open the zip file
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            # Extract all the contents into the specified directory
            zip_ref.extractall(extract_to)
            print(f"Extracted all files to '{extract_to}'.")
            
    import os
    import cv2
    import numpy as np

    def compare_image_to_folder(input_image_path, folder_path):
        # Read the input image
        input_image = cv2.imread(input_image_path)
        if input_image is None:
            raise FileNotFoundError(f"Input image '{input_image_path}' not found or not valid.")
        
        matched_images = []
        
        # Iterate through all files in the folder
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            
            # Skip if not a file
            if not os.path.isfile(file_path):
                continue
            
            # Read the current image
            folder_image = cv2.imread(file_path)
            if folder_image is None:
                continue
            
            # Check if the dimensions match
            if input_image.shape != folder_image.shape:
                continue  # Skip images with different dimensions
            
            # Compare the images pixel by pixel
            difference = cv2.subtract(input_image, folder_image)
            if not np.any(difference):  # If all values are zero, the images are identical
                matched_images.append(file_path)
        
        return matched_images
    def remove_prefix(text, prefix):
        if text.startswith(prefix):
            return text[len(prefix):]
        return text
    import os

    def print_folders_and_files(folder_path):
        try:
            items = os.listdir(folder_path)
            folders = []
            files = []

            for item in items:
                item_path = os.path.join(folder_path, item)
                if os.path.isdir(item_path):
                    folders.append(item)
                else:
                    files.append(item)

            print("Folders:")
            for folder in folders:
                print(folder)

            print("\nFiles:")
            for file in files:
                print(file)

        except Exception as e:
            print(f"An error occurred: {e}")

    # Example usage
    
    def extract_images_from_extract_api(filename, file_path, output_dir, s3_bucket, s3_folder):
        unzip_file(file_path, output_dir)
        
        print_folders_and_files("output/ExtractTextInfoFromPDF")
        with open(f"output/ExtractTextInfoFromPDF/{filename}/structuredData.json", "r") as file:
            data = json.load(file)
        by_page = {}

        for ele in data["elements"]:
            if "Page" in ele:
                if ele["Page"] not in by_page:
                    by_page[ele["Page"]] = []
                by_page[ele["Page"]].append(ele)

        
        return by_page
    
    def natural_sort_key(file_name):
        # Extract numbers from the file name using regex and convert to int for sorting
        return [int(num) if num.isdigit() else num for num in re.split(r'(\d+)', file_name)]
    def extract_images_from_excel(folder_path,file_path, output_dir, s3_bucket, s3_folder):
        """
        Extract images from an Excel file and save them to a directory and upload them to S3.

        Args:
        file_path (str): Path to the Excel file.
        output_dir (str): Directory to save the images.
        s3_bucket (str): The S3 bucket to upload the files to.
        s3_folder (str): The S3 folder to upload the files to.
        """
        logging.info(f'Filename : {filename} | Extracting the images from excel file...')
        pdf_document = pymupdf.open(pdf_path)
        
        
        # Load the workbook and the first sheet
        wb = openpyxl.load_workbook(file_path)
        wb.close()
        sheet = wb["Figures"]
        logging.info(f'Filename : {filename} | Sheet: {sheet.title}')
        logging.info(f'Filename : {filename} | Number of images: {len(sheet._images)}')

        # Check if the directory exists
        if not os.path.exists(output_dir):
            # Create the directory
            os.makedirs(output_dir)
        # Load the workbook
        df = pd.read_excel(file_path, sheet_name="Figures")
        logging.info(f'Filename : {filename} | DF loaded: {str(df)}')
        # Get the object IDs
        object_ids = df["Unnamed: 4"].dropna().values[1:]
    
        page_num_img = df["Figures and Alt Text (excludes artifacts and decorative images)"].dropna().values[2:].astype(int)
        page_num_img = [int(i)-1 for i in page_num_img]
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        by_page = extract_images_from_extract_api(filename,f"output/ExtractTextInfoFromPDF/extract${filename}.zip", f"output/ExtractTextInfoFromPDF/{filename}", bucket_name, f"temp/{file_base_name}/output_autotag")
        image_paths = []
        image_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.bmp')
        coordinates = df["Unnamed: 3"].dropna().values[1:]
        parsed_cordinates = [ast.literal_eval(item) for item in coordinates]
        logging.info(f'Filename : {filename} | Sheet: {sheet} , Sheet Images: {sheet._images}')
        # Loop through all images in the sheet
        for idx, img in enumerate(sheet._images):
            # Determine the image type and format
            img_type = img.path.split('.')[-1]
            img_path = os.path.join(output_dir, f'image_{idx + 1}.{img_type}')
            image_paths.append(img_path)
        
            # Save the image
            with open(img_path, 'wb') as f:
                f.write(img._data())
            logging.info(f'Filename : {filename} | Image {idx + 1} saved as {img_path}')
        image_paths = [
            os.path.join(output_dir, f)
            for f in sorted(os.listdir(output_dir), key=natural_sort_key)
        ]
        # Initialize the S3 client
        s3 = boto3.client('s3')
        logging.info(f'Filename : {filename} | Image Paths: {image_paths}')
        # Upload the images to S3
        for img_path in image_paths:
            s3.upload_file(img_path, s3_bucket, f'{s3_folder}/images/{file_key}_{os.path.basename(img_path)}')
            logging.info(f'Filename : {filename} | Uploaded image to S3')
        # Write the object IDs and image paths to a text file
        logging.info(f'Filename : {filename} | Object IDs: {object_ids} : Image Paths: {image_paths}')

        
        
        db_path = os.path.join(output_dir, "temp_images_data.db")
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
        import math
        
        for objid, img_path, pg_num, c in zip(object_ids, image_paths, page_num_img, parsed_cordinates):
            context = """"""
            
            for ele in by_page[pg_num]:
                if "Text" in ele: 
                    context += ele["Text"]
                if "filePaths" in ele:
                    if len(ele["filePaths"]) ==1:
                        if abs(math.ceil(ele["attributes"]["BBox"][2]) - math.ceil(ele["attributes"]["BBox"][0]) - c[2]) <= 7 and abs(math.ceil(ele["attributes"]["BBox"][3]) - math.ceil(ele["attributes"]["BBox"][1]) - c[3]) <= 7 and abs(round(ele["attributes"]["BBox"][0]) - c[0]) <= 7 and abs(round(ele["attributes"]["BBox"][3]) - c[1]) <= 7:
                            context +=  "<IMAGE INTERESTED> " + os.path.basename(img_path) + " </IMAGE INTERESTED> "
                        else:
                            context += "<OTHER IMAGE> " + ele["filePaths"][0].split("/")[-1] + " </OTHER IMAGE> "
            print(f"{True if '<IMAGE INTERESTED>' in context else False}")
            print("context:", context)  
            print(" ======================")
            cursor.execute("""
                INSERT INTO image_data (objid, img_path, context)
                VALUES (?, ?, ?)
            """, (
                objid,
                os.path.basename(img_path),
                context
            ))

        conn.commit()
        conn.close()
        # with open(os.path.join(output_dir, "temp_images_data.txt"), "w") as f:
        #     for objid, img_path, pg_num in zip(object_ids, image_paths, page_num_img):
        #         logging.info(f"here in this for loop:{objid}, {img_path, pg_num} ")
        #         pages_content = {"prev": "", "current": f"{pdf_document[pg_num].get_text()}", "next": ""}
        #         if pg_num > 0:
        #             pages_content["prev"] = pdf_document[pg_num - 1].get_text()
                
        #         if pg_num < len(pdf_document) - 1:
        #             pages_content["next"] = pdf_document[pg_num + 1].get_text()
                
        #         # Serialize the pages_content dictionary to JSON
        #         pages_content_json = json.dumps(pages_content)
        #         f.write(f"{objid} {os.path.basename(img_path)} {pages_content_json}\n")

        # Upload the text file to S3
        s3.upload_file(os.path.join(output_dir, "temp_images_data.db"), s3_bucket, f'{s3_folder}/{file_key}_temp_images_data.db')
    extract_images_from_excel(f"output/ExtractTextInfoFromPDF/{filename}/figures",f"output/AutotagPDF/{filename}.xlsx", "output/zipfile/images", bucket_name, f"temp/{file_base_name}/output_autotag")
def main():
    """
    Main function that coordinates the downloading, processing, and uploading of PDF files and associated content.
    """

    # Configure logging to display only the message
    logging.basicConfig(format='%(message)s', level=logging.INFO)

    # Create a logger
    logger = logging.getLogger(__name__)

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
        pdf_processing(local_file_path, file_base_name,file_key, bucket_name)
        logging.info(f'Filename : {file_key} | Processing completed for pdf file')
    except Exception as e:
        logger.info(f"File: {file_base_name}, Status: Failed in First ECS task")
        logger.info(f"Filename : {file_key} | Error: {e}")
        sys.exit(1)
        
if __name__ == "__main__":
    main()