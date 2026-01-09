import pdf2image
import easyocr
import numpy as np
import cv2
import pdfplumber
import sys
import re

def ocr_extract_from_pdf(pdf_path):
    """
    Extracts text from a PDF file using OCR (EasyOCR) and pdf2image.
    Designed for scanned resumes or resumes that are images.
    """
    try:
        # 1. First, check if pdfplumber can extract text (useful for hybrid PDFs)
        print(f"Checking for existing text metadata with pdfplumber: {pdf_path}")
        with pdfplumber.open(pdf_path) as pdf:
            plumber_text = ""
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    plumber_text += text + "\n"
        
        # If we found significant text, we might not strictly need OCR, 
        # but the user specifically asked for OCR-based handling here.
        
        # 2. Convert PDF pages to images
        # Note: poppler-utils must be installed on the system (apt install poppler-utils)
        print(f"Converting PDF to images for OCR: {pdf_path}")
        images = pdf2image.convert_from_path(pdf_path)
        
        # 2. Initialize EasyOCR Reader (CPU mode)
        print("Initializing EasyOCR (CPU)...")
        reader = easyocr.Reader(['en'], gpu=False)
        
        full_text = ""
        
        for i, image in enumerate(images):
            print(f"Processing page {i+1}/{len(images)}...")
            
            # Convert PIL image to OpenCV format (numpy array)
            open_cv_image = np.array(image)
            # Convert RGB to BGR (OpenCV uses BGR)
            open_cv_image = cv2.cvtColor(open_cv_image, cv2.COLOR_RGB2BGR)
            
            # Optional: Image preprocessing with OpenCV (e.g., Grayscale)
            gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
            
            # Perform OCR
            # detail=0 returns only the text strings
            results = reader.readtext(gray, detail=0)
            page_text = " ".join(results)
            full_text += page_text + "\n\n"

        # Basic cleaning
        formatted_text = re.sub(r'[ \t]+', ' ', full_text)
        formatted_text = re.sub(r'\n\s*\n', '\n\n', formatted_text)
        formatted_text = formatted_text.strip()

        return formatted_text

    except Exception as e:
        return f"Error during OCR extraction: {e}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ocr_extract.py <path_to_resume_pdf>")
    else:
        resume_path = sys.argv[1]
        text = ocr_extract_from_pdf(resume_path)
        print("\n--- Extracted OCR Text ---")
        print(text)
        print("--------------------------")
