import sys
import os
import base64
from io import BytesIO
from pdf2image import convert_from_path
from openai import OpenAI
from dotenv import load_dotenv
import timeit

def encode_image(image):
    """
    Encodes a PIL Image to a base64 string.
    """
    buffered = BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def review_resume_multimodal(pdf_path):
    """
    Converts PDF pages to images and sends them to a multimodal LLM for review.
    """
    load_dotenv()
    
    API_KEY = os.environ.get("OPENROUTER_API_KEY")
    # Using the specific model requested. 
    # Note: Ensure "google/gemma-3-27b-it" is the correct slug on OpenRouter.
    # Often multimodal models on OpenRouter might be "google/gemini-pro-1.5" or similar.
    # I am using the placeholder as requested by the user prompt logic ("Specifically gemma 3 27B")
    MODEL_NAME = "google/gemma-3-27b-it" 

    if not API_KEY:
        print("Error: OPENROUTER_API_KEY not found in environment variables.")
        return

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=API_KEY,
    )

    print(f"Converting PDF to images for analysis: {pdf_path}...")
    try:
        # Convert PDF to images
        start_time = timeit.default_timer()
        images = convert_from_path(pdf_path)
        end_time = timeit.default_timer()
        print(f"Converted PDF to {len(images)} images in {end_time - start_time:.2f} seconds")
    except Exception as e:
        print(f"Error converting PDF: {e}")
        return

    # Prepare user content with text + images
    content_payload = [
        {"type": "text", "text": "Please review the attached resume. Focus on visual layout, formatting, and content."}
    ]

    # Add images to payload
    for i, img in enumerate(images[:]): 
        base64_image = encode_image(img)
        content_payload.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image}"
            }
        })

    system_prompt = """
    You are an expert Senior Technical Recruiter and Career Coach accessing this resume through a Multimodal AI vision model.
    Unlike text-only parsers, you can see the **actual visual layout** of the document.

    Your goal is to critique the resume on two fronts: 
    1. **Visual Presentation & Structure** (Formatting, White Space, Font choice, Consistency).
    2. **Content & Narrative** (Impact, Metrics, Keywords).

    Provide your feedback in the following Markdown structure:

    ### 1. Visual First Impressions (The 6-Second Scan)
    **Score**: [0-100]
    **Analysis**: 
    *   **Layout**: Is it clean and easy to scan? Are margins consistent? 
    *   **Whitespace**: Is the resume too crowded or too sparse?
    *   **Font hierarchy**: Are headers clearly distinguishable from body text?

    ### 2. Content & Impact Review
    *   **Quantifiable Results**: Do bullet points include numbers (%, $, time)?
    *   **Action Verbs**: Are strong verbs used?

    ### 3. Critical formatting Issues
    (Only mention if applicable)
    *   [e.g., "Inconsistent indentation on the second job entry"]
    *   [e.g., "Font size for dates is too small to read easily"]

    ### 4. Top 3 Improvements
    1. [Visual/Structural Change]
    2. [Content Rewriting Suggestion]
    3. [General Optimization]
    """

    print("Sending data to Multimodal LLM...")
    try:
        start_time = timeit.default_timer()
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content_payload}
            ]
        )
        end_time = timeit.default_timer()
        print(f"Multimodal LLM review completed in {end_time - start_time:.2f} seconds")
        print("\n" + "="*50)
        print("MULTIMODAL RESUME REVIEW")
        print("="*50)
        print(completion.choices[0].message.content)
    except Exception as e:
        print(f"Error calling LLM: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <path_to_resume_pdf>")
    else:
        path = sys.argv[1]
        if os.path.exists(path):
            review_resume_multimodal(path)
        else:
            print("File not found.")
