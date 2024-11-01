/**
 * This script is designed to automate the process of downloading a PDF document from an S3 bucket, 
 * extracting associated image files, generating WCAG 2.1-compliant alt text using AWS Bedrock model(Claude Sonnet 3.5), 
 * and updating the PDF document with the generated alt text. 
 * Finally, the modified PDF is re-uploaded to the S3 bucket.
 * 
 * Key steps involved in this process:
 * 
 * 1. **S3 File Retrieval**: 
 *    - Fetch the PDF and associated image files from an S3 bucket.
 *    - Read a text file containing references to image objects in the PDF.
 * 
 * 2. **Alt Text Generation**: 
 *    - For each image, the alt text is generated using a Bedrock AI model. 
 *    - The prompt follows WCAG 2.1 guidelines to ensure the alt text improves accessibility.
 * 
 * 3. **PDF Modification**: 
 *    - The extracted alt text is added to the corresponding images within the PDF.
 *    - Hyperlinks in the PDF are also processed and assigned alt text describing their purpose.
 * 
 * 4. **Re-upload to S3**: 
 *    - After modifying the PDF to include the alt text, the updated file is saved locally and uploaded back to S3.
 * 
 * **Error Handling**:
 *    - Logging is used throughout the code to capture and report errors, including issues with S3 file retrieval, 
 *      alt text generation, and PDF processing.
 * 
 * This process ensures that PDFs are WCAG 2.1-compliant by adding meaningful alt text to all relevant images and links.
 */

const { S3Client, GetObjectCommand, PutObjectCommand } = require('@aws-sdk/client-s3');
const { BedrockRuntimeClient, InvokeModelCommand } = require('@aws-sdk/client-bedrock-runtime');
const fs = require('fs').promises;
const fs_1 = require('fs');
const winston = require('winston');
const pdfLib = require('pdf-lib');
const stream = require('stream');
const { promisify } = require('util');
const path = require('path');
const { PDFDocument, PDFName, PDFDict, PDFString } = require('pdf-lib');

const pipeline = promisify(stream.pipeline);

// Configure logger
const logger = winston.createLogger({
    level: 'info',
    format: winston.format.simple(),
    transports: [
        new winston.transports.Console()
    ]
});

// Create an S3 client instance.
const s3Client = new S3Client({ region: "us-east-1" });

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}


/**
 * Invokes the Bedrock AI model to generate alt text for a given image.
 * The image is provided as a buffer, which is converted to a base64-encoded string and included in the request payload.
 * The function sends the request to the model and returns the generated alt text.
 * 
 * @param {string} [prompt="generate alt text for this image"] - The prompt to guide the model in generating the alt text.
 * @param {Buffer} [imageBuffer=null] - The buffer containing the image data.
 * @param {string} [modelId="anthropic.claude-3-5-sonnet-20241022-v2:0"] - The ID of the Bedrock model to be used.
 * @returns {Promise<Object>} - A promise that resolves with the model's response, including the generated alt text.
 * @throws {Error} - Throws an error if invoking the model fails.
 */
const invokeModel = async (
    prompt = "generate alt text for this image",
    imageBuffer = null,
    modelId = "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
) => {
    // Create a new Bedrock Runtime client instance.
    const client = new BedrockRuntimeClient({ region: "us-east-1" });
    const model_arn_image = process.env.model_arn_image;
    
    // Convert the image buffer to a base64-encoded string
    const inputImageBase64 = imageBuffer ? imageBuffer.toString('base64') : null;

    // Prepare the payload for the model.
    const body = {
        anthropic_version: "bedrock-2023-05-31",
        max_tokens: 2000,
        temperature: 0,
        messages: [
            {
                role: "user",
                content: [
                    ...(inputImageBase64
                        ? [
                            {
                                type: "image",
                                source: {
                                    type: "base64",
                                    media_type: "image/png", 
                                    data: inputImageBase64,
                                },
                            },
                        ]
                        : []),
                    {
                        type: "text",
                        text: prompt,
                    },
                ],
            },
        ],
    };

    // Invoke the model with the payload and wait for the response.
    const command = new InvokeModelCommand({
        contentType: "application/json",
        body: JSON.stringify(body),
        modelId,
    });
    const apiResponse = await client.send(command);

    // Decode and return the response(s)
    const decodedResponseBody = new TextDecoder().decode(apiResponse.body);
    const responseBody = JSON.parse(decodedResponseBody);
    return responseBody;
};

/**
 * Generates WCAG 2.1-compliant alt text for an image based on its content and the provided prompt.
 * The function calls the Bedrock AI model to get a description formatted as JSON.
 * 
 * @param {Object} imageObject - Contains metadata about the image, such as its ID.
 * @param {Buffer} imageBuffer - The buffer containing the image data.
 * @returns {Promise<string>} - A promise that resolves with the generated alt text in JSON format.
 * @throws {Error} - Throws an error if generating the alt text fails.
 */
async function generateAltText(imageObject, imageBuffer) {
    const prompt = `Generate WCAG 2.1-compliant alt text for an image embedded in a PDF document. The output must be in strict JSON format as follows:
    {“${imageObject.id}“: “Alternative text”}
    Follow these guidelines to create appropriate and effective alt text:
    1. Image Description:
       - Describe the key elements of the image, including objects, people, scenes, and any visible text.
       - Consider the image’s role within the PDF. What information or function does it provide?
    2. WCAG 2.1 Compliance:
       a) Text in Image:
          - If duplicated nearby, use empty alt text: alt=“”
          - For functional text (e.g., icons), describe the function
          - Otherwise, include the exact text
       b) Functional Images:
          - For links/buttons, describe the action/destination
       c) Informative Images:
          - Provide a concise description of essential information
          - For complex images, summarize key data or direct to full information
       d) Decorative Images:
          - Use empty alt text: alt=“”
    3. Output Guidelines:
       - Keep alt text short, clear, and relevant
       - Ensure it enhances accessibility for assistive technology users
    Examples:
    1. “Sun Devil Stadium with a lone runner on the track during early morning training”
    2. “ASU’s Sun Devil head logo, symbolizing school spirit and athletic pride”
    3. “Print the course schedule for Fall 2024 semester”
    4. “Contact ASU support for assistance”
    Remember:
    - Provide only the JSON output with no additional explanation
    - Do not use unnecessary phrases like “Certainly!” or “Here’s the alt text:”
    - If you’re unsure about specific details, focus on describing what you can clearly determine from the context provided
    Now, based on the information given and these guidelines, generate the appropriate alt text in the required JSON format.`;

    try {
        const response = await invokeModel(prompt, imageBuffer);
        
        return response.content[0].text;
    } catch (error) {
      
        throw error;
    }
}


/**
 * Invokes the Bedrock AI model to generate alt text for a hyperlink based on its URL.
 * The function sends a prompt to the model and returns the generated alt text describing the link's destination or purpose.
 * 
 * @param {string} [prompt="Generate alt text for this link"] - The prompt to guide the model in generating the alt text for the link.
 * @param {string} [modelId="us.anthropic.claude-3-haiku-20240307-v1:0"] - The ID of the Bedrock model to be used.
 * @returns {Promise<string>} - A promise that resolves with the generated alt text for the link.
 * @throws {Error} - Throws an error if invoking the model fails.
 */
const invokeModel_alt_text_links = async (
    prompt = "Generate alt text for this link",
    modelId = "us.anthropic.claude-3-haiku-20240307-v1:0"
) => {
    const client = new BedrockRuntimeClient({ region: "us-east-1" });
    const model_arn_link = process.env.model_arn_link
    const body = {
        anthropic_version: "bedrock-2023-05-31",
        max_tokens: 2000,
        temperature: 0,
        messages: [
            {
                role: "user",
                content: [
                    {
                        type: "text",
                        text: prompt,
                    },
                ],
            },
        ],
    };

    const command = new InvokeModelCommand({
        contentType: "application/json",
        body: JSON.stringify(body),
        modelId,
    });

    try {
        const apiResponse = await client.send(command);
        const decodedResponseBody = new TextDecoder().decode(apiResponse.body);
        const responseBody = JSON.parse(decodedResponseBody);
        return responseBody.content[0].text;
    } catch (error) {
        console.error(`Error invoking model: ${error}`);
        throw error;
    }
};

/**
 * Invokes the Bedrock AI model to generate alt text for a hyperlink.
 * The model processes the link URL and prompt to provide a description.
 * @param {string} url - The URL of the hyperlink.
 * @returns {Promise<string>} - A promise that resolves with the generated alt text for the link.
 * @throws {Error} - Throws an error if the model invocation fails.
 */
async function generateAltTextForLink(url) {
    const prompt = `Generate WCAG 2.1-compliant alt text for a hyperlink. The alt text should describe the link's destination or purpose in a clear and concise manner. Example: "Link to YouTube video about PDF accessibility". The link URL is: ${url}`;
    try {
        return await invokeModel_alt_text_links(prompt, "us.anthropic.claude-3-haiku-20240307-v1:0");
    } catch (error) {
        console.error(`Error generating alt text for link: ${error}`);
        throw error;
    }
}

/**
 * Modifies a PDF by adding alt text to images and links based on the provided data.
 * The PDF is downloaded from S3, processed to include alt text, and re-uploaded to S3.
 * @param {Object} zipped - An object mapping image IDs to their respective alt text descriptions.
 * @param {string} bucketName - The name of the S3 bucket.
 * @param {string} inputKey - The key (path) of the input PDF in the S3 bucket.
 * @param {string} outputKey - The key (path) of the output PDF in the S3 bucket.
 * @param {string} filebasename - The base name of the file being processed.
 * @returns {Promise<void>} - A promise that resolves when the PDF has been modified and uploaded.
 * @throws {Error} - Throws an error if any step in the PDF processing or S3 operations fails.
 */
async function modifyPDF(zipped, bucketName, inputKey, outputKey, filebasename) {
    const downloadPath = path.join('/tmp', path.basename(inputKey)); // Download to /tmp directory

    try {
        // Step 1: Download the PDF file from S3 to a local path
        const downloadParams = {
           Bucket: process.env.S3_BUCKET_NAME,
            Key: `temp/${filebasename}/output_autotag/COMPLIANT_${process.env.S3_FILE_KEY.split("/").pop()}`,
        };
        const pdfData = await s3Client.send(new GetObjectCommand(downloadParams));

        // Stream the data to a file
        const writeStream = fs_1.createWriteStream(downloadPath);
        pdfData.Body.pipe(writeStream);

        await new Promise((resolve, reject) => {
            writeStream.on('finish', resolve);
            writeStream.on('error', reject);
        });

        // Step 2: Read the downloaded PDF file
        const pdfBytes = fs_1.readFileSync(downloadPath);
        const pdfDoc = await PDFDocument.load(pdfBytes);

        const linkProcessingPromises = [];

        // Process the PDF
        pdfDoc.context.enumerateIndirectObjects().forEach(([pdfRef, pdfObject]) => {
            if (pdfObject instanceof PDFDict) {
                const structType = pdfObject.lookup(PDFName.of('S'))?.encodedName;

                if (structType === '/Figure') {
                    Object.entries(zipped).forEach(([key, value]) => {
                        if (key == pdfRef.objectNumber) {
                            if (value === 'artifact') {
                             
                                pdfObject.set(PDFName.of('S'), PDFName.of('Artifact'));
                            } else {
                                logger.info(`Filename: ${filebasename} | Adding the alt text`);
                        
                                const newAltText = value;
                                pdfObject.set(PDFName.of('Alt'), PDFString.of(newAltText));
                                pdfObject.set(PDFName.of('Contents'), PDFString.of(newAltText));
                                delete zipped[key];
                                logger.info(`Filename: ${filebasename} | Alt text added:${newAltText}`);
                            }
                        }
                    });
                }
                if (pdfObject.has(PDFName.of('Type')) && pdfObject.lookup(PDFName.of('Type')).encodedName === '/Annot') {
                    const subType = pdfObject.lookup(PDFName.of('Subtype'))?.encodedName;
                    if (subType === '/Link') {
                        const action = pdfObject.lookup(PDFName.of('A'));
                        const url = action?.lookup(PDFName.of('URI'))?.value;

                        if (url) {
                            console.log(`Processing URL: ${url}`);
                            const altTextPromise = generateAltTextForLink(url).then((altText) => {
                                pdfObject.set(PDFName.of('Alt'), PDFString.of(altText));
                                pdfObject.set(PDFName.of('Contents'), PDFString.of(altText));
                            });

                            linkProcessingPromises.push(altTextPromise);
                        }
                    }
                }
                
            }
        });
        await Promise.all(linkProcessingPromises);
        // Step 3: Save the modified PDF locally
        const modifiedPdfBytes = await pdfDoc.save();
        const modifiedPdfPath = path.join('/tmp', 'modified_' + path.basename(inputKey));
        fs_1.writeFileSync(modifiedPdfPath, modifiedPdfBytes);

        // Step 4: Upload the modified PDF back to S3
        const uploadParams = {
            Bucket: bucketName,
            Key: `temp/${filebasename}/FINAL_${outputKey}`,
            Body: fs_1.createReadStream(modifiedPdfPath),
            ContentType: 'application/pdf'
        };
        await s3Client.send(new PutObjectCommand(uploadParams));

        logger.info(`PDF modification complete. Output saved to s3://${bucketName}/FINAL_${outputKey}`);

        // Clean up: Remove the local files if needed
        fs_1.unlinkSync(downloadPath);
        fs_1.unlinkSync(modifiedPdfPath);

    } catch (err) {
        console.error(`Filename: ${filebasename} | Error processing PDF: ${err}`);
    }
}

/**
 * Main process function that orchestrates the retrieval of image data, 
 * generates alt text for images and links, and modifies the PDF accordingly.
 * This function fetches necessary data from S3, processes images to generate alt text,
 * updates the PDF with the generated alt text, and uploads the final PDF back to S3.
 * @returns {Promise<void>} - A promise that resolves when the entire process is complete.
 * @throws {Error} - Throws an error if any part of the process encounters issues.
 */
async function startProcess() {
    
    const bucketName = process.env.S3_BUCKET_NAME;
    const textFileKey = `${process.env.S3_FILE_KEY.split("/")[1]}/output_autotag/${process.env.S3_FILE_KEY.split("/").pop()}_temp_images_data.txt`;
    const filebasename = process.env.S3_FILE_KEY.split("/")[1];
   
    logger.info(`Filename: ${filebasename} | Text File Key: ${textFileKey}, Bucket Name: ${bucketName}`);
    try {
   
        const getObjectParams = {
            Bucket: bucketName,
            Key: `temp/${textFileKey}`,
        };
        const command = new GetObjectCommand(getObjectParams);
        const { Body } = await s3Client.send(command);

        // Stream the body contents to a buffer
        const chunks = [];
        await pipeline(Body, async function* (source) {
            for await (const chunk of source) {
                chunks.push(chunk);
            }
        });
        logger.info(`Filename: ${filebasename} | Chunks:${chunks}`);
        const fileBuffer = Buffer.concat(chunks);
        const localFilePath = path.join(__dirname, `temp_images_data.txt`);
        fs_1.writeFileSync(localFilePath, fileBuffer);
        const data = await fs.readFile('temp_images_data.txt', 'utf8');
        const lines = data.split('\n');
        const splitLines = lines.map(line => line.split(' '));
        splitLines.pop();
        logger.info(`Filename: ${filebasename} | Split Lines: ${splitLines}`);
        let imageObjects = splitLines.map(split => ({
            id: split[0],
            path: `temp/${process.env.S3_FILE_KEY.split("/")[1]}/output_autotag/images/${process.env.S3_FILE_KEY.split("/").pop()}_${split[1]}` // Path to images in S3
        }));

        let combinedResults = {};

        for (const imageObject of imageObjects) {
            try {
                const getObjectParams = {
                    Bucket: bucketName,
                    Key: imageObject.path,
                };
                const command = new GetObjectCommand(getObjectParams);
                const { Body } = await s3Client.send(command);
        
                // Stream the body contents to a buffer
                const chunks = [];
                await pipeline(Body, async function* (source) {
                    for await (const chunk of source) {
                        chunks.push(chunk);
                    }
                });
                const fileBuffer = Buffer.concat(chunks);
                const localFilePath = path.join(__dirname, `${imageObject.path.split('/').pop()}`);
                fs_1.writeFileSync(localFilePath, fileBuffer);
                const image_Buffer = await fs.readFile(localFilePath);
                const response = await generateAltText(imageObject, image_Buffer);
                logger.info(`Filename: ${filebasename} | Response:${response}`);
                Object.assign(combinedResults, JSON.parse(response));
            } catch (error) {
                logger.info(`Filename: ${filebasename} | Error: ${error}`);
            }
            await sleep(1000);
        }

        let defaultText = "No text available"; 

        for (const imageObject of imageObjects) {
            if (!combinedResults.hasOwnProperty(imageObject.id)) {
                combinedResults[imageObject.id] = defaultText;
            }
        }

        logger.info(`Filename: ${filebasename} | Combined Results:${combinedResults}`);

        // Process the combined results for modifying the PDF
        let descriptions = Object.values(combinedResults);
        let zipped = imageObjects.map((element, index) => [element.id, descriptions[index]]);
        logger.info(`Filename: ${filebasename} | zipped: ${zipped}`);

        await modifyPDF(combinedResults, bucketName, "output_autotag/COMPLIANT.pdf", path.basename(process.env.S3_FILE_KEY), filebasename);
        logger.info(`Filename: ${filebasename} | PDF modification complete`);

    } catch (error) {
        logger.info(`File: ${filebasename}, Status: Error in second ECS task`);
        logger.error(`Filename: ${filebasename} | Error processing images: ${error}`);
        process.exit(1);
    }
}



startProcess();
