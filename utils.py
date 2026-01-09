import fitz  # PyMuPDF
import pdf2image
import easyocr
import numpy as np
import cv2
import re
import os

def extract_text_standard(pdf_path):
    """
    Standard extraction using PyMuPDF.
    Returns extracted text if found, else None.
    """
    try:
        doc = fitz.open(pdf_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text("text") + "\n"
        doc.close()
        
        cleaned_text = clean_text(full_text)
        return cleaned_text if cleaned_text.strip() else None
    except Exception as e:
        print(f"Standard extraction failed: {e}")
        return None

def extract_text_ocr(pdf_path):
    """
    OCR extraction using EasyOCR as fallback.
    """
    try:
        # Full OCR Fallback
        images = pdf2image.convert_from_path(pdf_path)
        reader = easyocr.Reader(['en'], gpu=False)
        
        full_text = ""
        for image in images:
            open_cv_image = np.array(image)
            open_cv_image = cv2.cvtColor(open_cv_image, cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
            results = reader.readtext(gray, detail=0)
            full_text += " ".join(results) + "\n"
            
        return clean_text(full_text)
    except Exception as e:
        print(f"OCR extraction failed: {e}")
        return None

def clean_text(text):
    """
    Basic text cleaning and formatting.
    """
    if not text:
        return ""
    # Replace multiple spaces
    text = re.sub(r'[ \t]+', ' ', text)
    # Normalize newlines
    text = re.sub(r'\n\s*\n', '\n\n', text)
    return text.strip()

def get_resume_text(pdf_path):
    """
    Try standard extraction first, fallback to OCR if needed.
    """
    print(f"Attempting standard extraction for: {os.path.basename(pdf_path)}")
    text = extract_text_standard(pdf_path)
    
    # If text is too short or empty, it might be a scanned image
    if not text or len(text.strip()) < 50:
        print("Standard extraction yielded insufficient text. Falling back to OCR...")
        text = extract_text_ocr(pdf_path)
        
    return text
