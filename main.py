import sys
import os
from utils import get_resume_text

def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <path_to_resume_pdf>")
        sys.exit(1)

    resume_path = sys.argv[1]
    
    if not os.path.exists(resume_path):
        print(f"Error: File not found at {resume_path}")
        sys.exit(1)

    print(f"Starting extraction for: {resume_path}...")
    extracted_text = get_resume_text(resume_path)

    if extracted_text:
        print("\n" + "="*50)
        print("FINAL EXTRACTED TEXT")
        print("="*50)
        print(extracted_text)
        print("="*50)
        print(f"\nTotal characters extracted: {len(extracted_text)}")
    else:
        print("Failed to extract any text from the provided PDF.")

if __name__ == "__main__":
    main()
