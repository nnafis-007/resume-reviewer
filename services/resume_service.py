import base64
import os
import logging
from io import BytesIO
from typing import Optional

from pdf2image import convert_from_path
from openai import OpenAI
from dotenv import load_dotenv

# Configure logger for this module
logger = logging.getLogger(__name__)

class ResumeReviewService:
    def __init__(self):
        load_dotenv()
        self.api_key = os.environ.get("OPENROUTER_API_KEY")
        self.model_name = "google/gemma-3-27b-it"
        
        if not self.api_key:
            logger.error("OPENROUTER_API_KEY not found in environment variables.")
            raise ValueError("API Key not configured")

        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key,
        )

    def _encode_image(self, image) -> str:
        """
        Encodes a PIL Image to a base64 string.
        """
        buffered = BytesIO()
        image.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')

    def review_resume(self, pdf_path: str) -> Optional[str]:
        """
        Converts PDF pages to images and sends them to a multimodal LLM for review.
        """
        logger.info(f"Starting resume review for file: {pdf_path}")
        
        try:
            # Convert PDF to images
            # poppler_path can be added to convert_from_path if needed on specific OS
            images = convert_from_path(pdf_path)
            logger.info(f"Successfully converted PDF to {len(images)} images")
        except Exception as e:
            logger.error(f"Error converting PDF to images: {str(e)}")
            raise e

        # Prepare user content with text + images
        content_payload = [
            {"type": "text", "text": "Please review the attached resume. Focus on visual layout, formatting, and content."}
        ]

        # Add images to payload (Cap at first 2 pages to save tokens/context window)
        pages_to_process = images[:2]
        for i, img in enumerate(pages_to_process): 
            base64_image = self._encode_image(img)
            content_payload.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}"
                }
            })
        
        system_prompt = """
        You are an expert Senior Technical Recruiter and Executive Career Coach. 
        You are reviewing the attached resume to provide a professional, critical assessment.

        **Tone & Style Guidelines:**
        *   Be direct, professional, and analytical.
        *   Avoid conversational fillers (e.g., "Okay," "I have reviewed," "Hope this helps," "Let me know").
        *   Do not self-reference as an AI model.
        *   Start directly with the analysis.

        **Review Objectives:**
        1.  **Visual Presentation**: Evaluate layout, hierarchy, and professional polish.
        2.  **Content Impact**: Evaluate if the candidate effectively sells their skills using metrics and results.

        Provide the review in the following structured Markdown format:

        ### 1. Executive Summary & Visual Audit
        **ATS/Visual Score**: [0-100]
        **Professional Perception**: [2-3 sentences analyzing the immediate visual impression, layout cleanliness, and readability.]

        ### 2. Content & Narrative critique
        *   **Impact Analysis**: [Evaluate use of metrics and result-oriented language.]
        *   **Keyword Strategy**: [Assess alignment with industry standard terminology.]

        ### 3. Critical Observations
        *   [Observation 1]
        *   [Observation 2]

        ### 4. Strategic Recommendations (Top 3)
        1.  **[Strategy 1]**: [Actionable advice]
        2.  **[Strategy 2]**: [Actionable advice]
        3.  **[Strategy 3]**: [Actionable advice]
        """

        logger.info("Sending payload to Multimodal LLM via OpenRouter...")
        try:
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content_payload}
                ]
            )
            review_content = completion.choices[0].message.content
            logger.info("Successfully received review from LLM")
            return review_content
            
        except Exception as e:
            logger.error(f"Error calling LLM API: {str(e)}")
            raise e
