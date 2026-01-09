import fitz  # PyMuPDF
import sys
import re

def extract_text_from_pdf(pdf_path):
    """
    Extracts text from a PDF file and performs basic formatting.
    """
    try:
        # Open the PDF file
        doc = fitz.open(pdf_path)
        full_text = ""

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text("text")
            full_text += text + "\n"

        doc.close()

        # Basic formatting/cleaning
        # 1. Replace multiple spaces with a single space
        formatted_text = re.sub(r'[ \t]+', ' ', full_text)
        # 2. Normalize newlines (remove excessive blank lines)
        formatted_text = re.sub(r'\n\s*\n', '\n\n', formatted_text)
        # 3. Strip leading/trailing whitespace
        formatted_text = formatted_text.strip()

        return formatted_text

    except Exception as e:
        return f"Error extracting text: {e}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_text.py <path_to_resume_pdf>")
    else:
        resume_path = sys.argv[1]
        text = extract_text_from_pdf(resume_path)
        print("--- Extracted Text ---")
        print(text)
        print("----------------------")
