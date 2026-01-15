import base64
import os
import logging
import asyncio
import re
from io import BytesIO
from typing import Optional

from pdf2image import convert_from_path
from openai import AsyncOpenAI
from dotenv import load_dotenv
from prometheus_client import Histogram

try:
    import fitz  # PyMuPDF
except Exception:  # pragma: no cover
    fitz = None

# Configure logger for this module
logger = logging.getLogger(__name__)


INVALID_RESUME_SENTINEL = "The provided resume is INVALID. Please provide a valid resume for review."


class InvalidResumeError(ValueError):
    """Raised when the LLM indicates the uploaded PDF is not a valid/legible resume."""

# Metrics
RESUME_PROCESSING_TIME = Histogram(
    "resume_processing_seconds", 
    "Time spent extracting content and querying LLM",
    buckets=[1, 5, 10, 20, 30, 60, 90, 120]
)

class ResumeReviewService:
    MIN_EXTRACTED_TEXT_CHARS = 50
    MAX_TEXT_CHARS_FOR_LLM = 15000

    def __init__(self):
        load_dotenv()
        self.api_key = os.environ.get("OPENROUTER_API_KEY")
        self.model_name = "google/gemma-3-27b-it"
        
        if not self.api_key:
            logger.error("OPENROUTER_API_KEY not found in environment variables.")
            raise ValueError("API Key not configured")

        self.client = AsyncOpenAI(
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

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n", "\n\n", text)
        return text.strip()

    def _extract_text_standard(self, pdf_path: str) -> Optional[str]:
        """Fast text extraction via PyMuPDF (no OCR)."""
        if fitz is None:
            logger.info("PyMuPDF not available; skipping text-first extraction")
            return None

        try:
            doc = fitz.open(pdf_path)
            full_text_parts: list[str] = []
            for page in doc:
                blocks = page.get_text("blocks")
                blocks.sort(key=lambda b: (b[1], b[0]))
                for block in blocks:
                    full_text_parts.append(block[4])
            doc.close()

            cleaned_text = self._clean_text("\n".join(full_text_parts))
            return cleaned_text if cleaned_text.strip() else None
        except Exception as e:
            logger.warning(f"Standard text extraction failed; falling back to images: {str(e)}")
            return None

    async def _get_resume_text(self, pdf_path: str) -> Optional[str]:
        return await asyncio.to_thread(self._extract_text_standard, pdf_path)

    def _truncate_for_llm(self, text: str) -> str:
        if len(text) <= self.MAX_TEXT_CHARS_FOR_LLM:
            return text
        truncated = text[: self.MAX_TEXT_CHARS_FOR_LLM]
        return truncated + "\n\n[TRUNCATED: resume text exceeded max length]"

    def _strip_code_fences(self, text: str) -> str:
        stripped = text.strip()

        # ```...``` (optionally with language tag)
        if stripped.startswith("```") and stripped.endswith("```"):
            lines = stripped.splitlines()
            if len(lines) >= 2 and lines[0].startswith("```"):
                inner = "\n".join(lines[1:-1])
                return inner.strip()
            return stripped.strip("`").strip()

        return stripped

    def _normalize_llm_text(self, text: Optional[str]) -> str:
        if not text:
            return ""
        return self._strip_code_fences(text).strip()

    def _is_invalid_resume_response(self, response_text: Optional[str]) -> bool:
        """Flexible detector for the invalid-resume sentinel and common non-compliance variants."""
        normalized = self._normalize_llm_text(response_text)
        if not normalized:
            return False

        if normalized == INVALID_RESUME_SENTINEL:
            return True

        if INVALID_RESUME_SENTINEL.lower() in normalized.lower():
            return True

        lowered = normalized.lower()
        condensed = re.sub(r"\s+", " ", lowered).strip()
        if "not a resume" in condensed or "not a resumé" in condensed or "not a résumé" in condensed:
            return True
        if "not suitable as a job application" in condensed:
            return True

        patterns = [
            # Direct non-resume statements
            r"\bnot\s+a\s+resum[eé]\b",
            r"\bisn['’]?t\s+a\s+resum[eé]\b",
            r"\bthis\s+(document\s+)?is\s+not\s+a\s+resum[eé]\b",
            r"\bnot\s+actually\s+a\s+resum[eé]\b",
            r"\bdemonstrably\s+not\s+a\s+resum[eé]\b",

            # Common document types that are not resumes
            r"\bcommand\s+reference\b",
            r"\btechnical\s+manual\b",
            r"\btechnical\s+guide\b",
            r"\btable\s+of\s+contents\b",
            r"\bdocumentation\b",

            # Disqualification phrasing
            r"\bnot\s+suitable\s+as\s+(a\s+)?job\s+application\b",
            r"\bimmediately\s+disqualifying\b",
        ]

        return any(re.search(p, lowered) for p in patterns)

    async def review_resume(self, pdf_path: str) -> Optional[str]:
        """
        Two-stage review to reduce latency:
        1) Try fast PDF text extraction and run a text-only review.
        2) If text extraction is insufficient, fall back to PDF->images multimodal review.
        """
        with RESUME_PROCESSING_TIME.time():
            logger.info(f"Starting resume review for file: {pdf_path}")

            # Stage 1: Fast text-only path
            extracted_text = await self._get_resume_text(pdf_path)
            if extracted_text and len(extracted_text.strip()) >= self.MIN_EXTRACTED_TEXT_CHARS:
                logger.info("Using text-first review path")

                resume_text_for_llm = self._truncate_for_llm(extracted_text)
                content_payload = [
                    {
                        "type": "text",
                        "text": (
                            "Please review this resume based on the extracted text below. "
                            "Focus on content impact, clarity, and ATS keyword strategy."
                        ),
                    },
                    {"type": "text", "text": f"RESUME TEXT\n\n{resume_text_for_llm}"},
                ]

                system_prompt = f"""
                You are an expert Senior Technical Recruiter and Executive Career Coach.
                You are reviewing a resume from extracted PDF text.

                HARD RULE (must follow exactly):
                If the provided text is NOT a resume (examples: documentation, command reference, technical manual, random notes, blank/garbled text), respond with EXACTLY this and nothing else:
                ```{INVALID_RESUME_SENTINEL}```

                If you output the invalid message, do NOT include headings, scores, bullet points, analysis, or any other text.

                **Tone & Style Guidelines:**
                *   Be direct, professional, and analytical.
                *   Avoid conversational fillers (e.g., "Okay," "I have reviewed," "Hope this helps," "Let me know").
                *   Do not self-reference as an AI model.
                *   Start directly with the analysis.

                **Review Objectives (Text-Only):**
                1.  **Content Impact**: Evaluate accomplishment bullets, metrics, and results.
                2.  **Clarity & Structure**: Evaluate readability and role progression from the text.
                3.  **Keyword Strategy**: Evaluate alignment with industry standard terminology.

                Provide the review in the following structured Markdown format:

                ### 1. Executive Summary & Visual Audit
                **ATS/Visual Score**: [0-100]
                **Professional Perception**: [2-3 sentences. Note: this is text-only; infer structure where possible.]

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

                logger.info("Sending text payload to LLM via OpenRouter...")
                try:
                    completion = await self.client.chat.completions.create(
                        model=self.model_name,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": content_payload},
                        ],
                    )
                    review_content = completion.choices[0].message.content
                    if self._is_invalid_resume_response(review_content):
                        raise InvalidResumeError("LLM reported invalid resume")
                    logger.info("Successfully received text-based review from LLM")
                    return review_content
                except InvalidResumeError:
                    logger.warning("LLM indicated the resume is invalid (text path)")
                    raise
                except Exception as e:
                    logger.error(f"Error calling LLM API (text path): {str(e)}")
                    raise e

            # Stage 2: Existing multimodal image fallback
            logger.info("Text extraction insufficient; using image-based review path")

            try:
                images = await asyncio.to_thread(convert_from_path, pdf_path)
                logger.info(f"Successfully converted PDF to {len(images)} images")
            except Exception as e:
                logger.error(f"Error converting PDF to images: {str(e)}")
                raise e

            content_payload = [
                {"type": "text", "text": "Please review the attached resume. Focus on visual layout, formatting, and content."}
            ]

            pages_to_process = images[:5]
            for img in pages_to_process:
                base64_image = self._encode_image(img)
                content_payload.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                    }
                )

            system_prompt = f"""
            You are an expert Senior Technical Recruiter and Executive Career Coach.
            You are reviewing the attached document via images.

            HARD RULE (must follow exactly):
            If the document is NOT a resume (examples: documentation, command reference, technical manual, invoice, certificate, blank page, garbled/illegible scan, slide deck), respond with EXACTLY this and nothing else:
            ```{INVALID_RESUME_SENTINEL}```

            If you output the invalid message, do NOT include headings, scores, bullet points, analysis, or any other text.

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

            logger.info("Sending multimodal payload to LLM via OpenRouter...")
            try:
                completion = await self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": content_payload},
                    ],
                )
                review_content = completion.choices[0].message.content
                if self._is_invalid_resume_response(review_content):
                    raise InvalidResumeError("LLM reported invalid resume")
                logger.info("Successfully received multimodal review from LLM")
                return review_content
            except InvalidResumeError:
                logger.warning("LLM indicated the resume is invalid (image path)")
                raise
            except Exception as e:
                logger.error(f"Error calling LLM API (image path): {str(e)}")
                raise e
