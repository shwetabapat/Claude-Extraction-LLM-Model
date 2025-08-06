from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import anthropic
import os
from dotenv import load_dotenv
import base64
import io
from PIL import Image
from pdf2image import convert_from_bytes
import PyPDF2
import logging
import json
import asyncio

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

async def send_progress_update(message: str):
    return f"data: {json.dumps({'type': 'progress', 'message': message})}\n\n"

async def send_result_update(result: dict):
    return f"data: {json.dumps({'type': 'result', 'data': result})}\n\n"

@app.post("/api/combine-documents")
async def combine_documents(files: list[UploadFile] = File(...)):
    try:
        # Create a PDF merger
        merger = PyPDF2.PdfMerger()
        
        # Process each file
        for file in files:
            if not file.filename.lower().endswith('.pdf'):
                raise HTTPException(
                    status_code=400, 
                    detail=f"File {file.filename} is not a PDF. Only PDF files are supported for combining."
                )
            
            # Read the file content
            content = await file.read()
            
            # Create a BytesIO object with the content
            pdf_buffer = io.BytesIO(content)
            
            # Add to merger
            merger.append(pdf_buffer)
        
        # Create the final combined PDF
        output_pdf = io.BytesIO()
        merger.write(output_pdf)
        merger.close()
        
        # Get the PDF content
        combined_pdf_content = output_pdf.getvalue()
        
        # Convert to base64
        base64_content = base64.b64encode(combined_pdf_content).decode('utf-8')
        
        return {
            "message": "Documents combined successfully",
            "filename": "combined_document.pdf",
            "base64_content": base64_content
        }
        
    except Exception as e:
        logger.error(f"Error combining documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analyze-documents")
async def analyze_documents(files: list[UploadFile] = File(...)):
    try:
        # We expect only one file (the combined document)
        if len(files) != 1:
            raise HTTPException(status_code=400, detail="Expected exactly one combined document")
        
        file = files[0]
        logger.info(f"Processing combined document: {file.filename}")
        
        # Read the file content
        content = await file.read()
        
        # Convert PDF to images for all pages
        images = convert_from_bytes(content)
        if not images:
            raise HTTPException(status_code=400, detail="No pages found in the combined PDF")

        base64_images = []
        
        # Convert each page to JPEG and Base64
        for i, image in enumerate(images):
            img_buffer = io.BytesIO()
            image.save(img_buffer, format='JPEG', quality=95)
            image_content = img_buffer.getvalue()
            
            # Convert to Base64
            base64_content = base64.b64encode(image_content).decode('utf-8')
            base64_images.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": base64_content
                }
            })

        logger.info(f"Successfully converted {len(images)} pages to images")
        
        bl_prompt = """I am going to upload a {documentType}, and I need you to scan it for specific information. Please return the data in a JSON format using the following structure. If any of the information is unavailable, return the property with a `null` value. If there are multiple items for a specific property, return them as an array. Here are specific instructions and examples for each field:

- `billOfLadingNumber`: The unique identifier for the bill of lading, often a combination of letters and numbers. Expected format: a string, e.g., `BL12345678`, `BOL-2023-001`.
- `containerNumbers`: Shipping container/cntr identifier. 11 character string, with 4 alphabets + 7 characters. Always.
- `shipmentDate`: The shipmentDate is the date the goods were loaded onto the vessel, prioritising labels like 'Shipped on Board Date' or 'SOB Date'. If an 'on board' date is not available, use the date the carrier took possession of the goods, such as 'Cargo Receipt Date'. As a final fallback, use the 'Pickup Date' if neither of the other two dates can be found. Expected format: a date in `YYYY-MM-DD` format, e.g., `2023-08-10`.
- `dateIssued`: The date the document or bill of lading was issued. Expected format: a date in `YYYY-MM-DD` format, e.g., `2023-08-15`.
- `vesselName`: The name of the vessel carrying the goods. Expected format: a string, e.g., `Evergreen`, `Maersk Alabama`.
- `buyerName`: The name of the buyer or recipient of the shipment. Expected format: a string, e.g., `XYZ Corp.`, `Jane Doe Enterprises`.
- `sellerName`: The name of the seller or supplier of the goods. Expected format: a string, e.g., `ABC Corp.`, `John Doe Enterprises`.
- `sellerAddress`: The physical address of the seller, including street, city, postal code, and country. Expected format: a string, e.g., `123 Market St, San Francisco, CA, 94103, USA`.
- `buyerAddress`: The physical address of the buyer, including street, city, postal code, and country. Expected format: a string, e.g., `456 Main St, New York, NY, 10001, USA`.
- `billOfLadingIssuer`: The entity or company that issued the bill of lading. Expected format: a string, e.g., `Maersk Line`, `Hapag-Lloyd`.
- `loadingPort`: The port where the goods were loaded onto the vessel. Expected format: a string, e.g., `Port of Shanghai`, `Los Angeles Port`.
- `dischargePort`: The port where the goods are to be unloaded from the vessel. Expected format: a string, e.g., `Port of Rotterdam`, `Port of Long Beach`.
Please scan the document and fill in each of the fields accordingly. If no information is found for a field, return it as `null`. For fields with multiple items, such as `containerNumbers`, `invoiceItems`, and `invoiceItemsWeight`, return an array of values.

{
'billOfLadingNumber': null,
'containerNumbers': [],
'shipmentDate': null,
'dateIssued': null,
'vesselName': null,
'buyerName': null,
'sellerName': null,
'sellerAddress': null,
'buyerAddress': null,
'billOfLadingIssuer': null,
'loadingPort': null,
'dischargePort': null,
}"""
        # Prepare the request for Claude, including all the page images
        claude_request = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": bl_prompt
                    }
                ] + base64_images  # Append all images to the content
            }
        ]

        # Send the request to Claude
        response = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=4096,
            messages=claude_request
        )

        # Return the response as JSON
        return {
            "insights": response.content[0].text,
            "files_processed": [file.filename],
            "pages_sent": len(images)
        }
        
    except Exception as e:
        logger.error(f"Error analyzing document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 