from openai import OpenAI
import os
from dotenv import load_dotenv
import timeit

from invalid_resume_detector import (
    INVALID_RESUME_SENTINEL,
    is_invalid_resume_response,
)


def review_resume(resume_text):
    """
    Sends the resume text to an LLM via OpenRouter for an ATS-style review.
    """
    load_dotenv()  # Load environment variables from .env file

    # Placeholder credentials
    API_KEY = os.environ.get("OPENROUTER_API_KEY")
    MODEL_NAME = "google/gemma-3-27b-it" 
    
    # the base_url is usually "https://openrouter.ai/api/v1"
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=API_KEY,
    )

    system_prompt = f"""
    You are an expert Senior Technical Recruiter and ATS (Applicant Tracking System) Optimization Specialist.
    You are reviewing the **raw text extracted from a resume PDF**. 

    HARD RULE (must follow exactly):
    If the provided text is NOT a resume (examples: documentation, command reference, technical manual, random notes, blank/garbled text), respond with EXACTLY this and nothing else:
    ```{INVALID_RESUME_SENTINEL}```

    If you output the invalid message, do NOT include headings, scores, bullet points, analysis, or any other text.
    
    **IMPORTANT**: Since you are processing raw text, do NOT comment on visual formatting like fonts, margins, colors, or columns. 
    Instead, focus entirely on the **content**, the **logical order of sections**, and the **narrative structure**.

    Your standard is extremely high. Assume the role of a strict gatekeeper.

    Analyze the resume based on these critical pillars:

    1.  **Structure & Section Arrangement**:
        *   Are the sections logically ordered?
        *   Is any critical standard section missing?
        *   Is the hierarchy clear based on the text flow?

    2.  **Impact & Metrics (The "So What?" Test)**: 
        *   Every bullet point must answer "So what?".
        *   Check for Action-Context-Result structure.
        *   Are there quantifiable metrics (%, $, time saved)? If not, mark it down heavily.

    3.  **Keyword Optimization**: 
        *   Identify missing core technical skills or industry-standard keywords based on the resume's content.

    4.  **Clarity & Brevity**: 
        *   Flag vague buzzwords (e.g., "Responsible for", "Hard worker") that need to be removed.
        *   Is the writing concise and professional?

    Provide your feedback in this strict Markdown format:

    ### 1. Structure & Flow Score (0-100)
    **Score**: [0-100]
    **Verdict**: [Pass/Fail/Borderline]
    **Analysis**: Evaluate the section ordering and content flow (ignoring visual formatting).

    ### 2. Critical Red Flags (Content & Structure)
    *   **[Issue Name]**: [Explanation].

    ### 3. Impact Analysis & Missing Metrics
    *   **Observation**: [E.g., "Projects lack measurable outcomes."]
    *   **Advice**: [Specific instruction on what metric to specific add.]

    ### 4. Direct Line-by-Line Rewrites (The most important section)
    Identify the 3 weakest bullet points in the resume. For EACH, provide:
    *   **Original**: "[The original text]"
    *   **Critique**: Why is this weak?
    *   **Suggested Rewrite**: "[A powerful, metric-driven alternative]"

    ### 5. Final Verdict & Next Steps
    Summarize the top 2 actions to improve the resume's content and structure.
    """

    user_message = f"Here is the resume text extracted from a PDF:\n\n{resume_text}"

    try:
        start_time = timeit.default_timer()
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
        )
        end_time = timeit.default_timer()
        print(f"{MODEL_NAME} LLM review completed in {end_time - start_time:.2f} seconds")
        response_text = completion.choices[0].message.content
        if is_invalid_resume_response(response_text):
            return f"```{INVALID_RESUME_SENTINEL}```"
        return response_text
    except Exception as e:
        return f"Error connecting to LLM: {str(e)}"
