import fitz  # PyMuPDF
import pdf2image
import easyocr
import numpy as np
import cv2
import re
import os
import timeit

def extract_text_standard(pdf_path):
    """
    Standard extraction using PyMuPDF.
    Returns extracted text if found, else None.
    """
    try:
        start_time = timeit.default_timer()
        doc = fitz.open(pdf_path)
        full_text = ""
        for page in doc:
            # "blocks" output preserves structure text better (x0, y0, x1, y1, "text", block_no, block_type)
            blocks = page.get_text("blocks")
            # Sort blocks by vertical position, then horizontal
            blocks.sort(key=lambda b: (b[1], b[0]))
            
            for block in blocks:
                # blocks[4] is the text content
                full_text += block[4] + "\n"\
        
        end_time = timeit.default_timer()
        print(f"Standard extraction completed in {end_time - start_time:.2f} seconds")
                
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
        # Report Time taken for OCR
        start_time = timeit.default_timer()

        # Full OCR Fallback
        images = pdf2image.convert_from_path(pdf_path)
        reader = easyocr.Reader(['en'], gpu=False)
        
        full_text = ""
        for image in images:
            open_cv_image = np.array(image)
            open_cv_image = cv2.cvtColor(open_cv_image, cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
            
            # paragraph=True combines spatially close text into paragraphs
            results = reader.readtext(gray, detail=0, paragraph=True)
            # Join with double newlines to separate distinct text blocks/paragraphs
            full_text += "\n\n".join(results) + "\n\n"
        
        end_time = timeit.default_timer()
        print(f"OCR extraction completed in {end_time - start_time:.2f} seconds")
            
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
