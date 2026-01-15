import re
from typing import Optional

INVALID_RESUME_SENTINEL = "The provided resume is INVALID. Please provide a valid resume for review."


def _strip_code_fences(text: str) -> str:
    stripped = text.strip()

    # ```...``` (optionally with language tag)
    if stripped.startswith("```") and stripped.endswith("```"):
        # Remove first fence line (``` or ```lang)
        lines = stripped.splitlines()
        if len(lines) >= 2 and lines[0].startswith("```"):
            inner = "\n".join(lines[1:-1])
            return inner.strip()

        # Fallback: trim backticks
        return stripped.strip("`").strip()

    return stripped


def normalize_llm_text(text: Optional[str]) -> str:
    if not text:
        return ""
    return _strip_code_fences(text).strip()


def is_invalid_resume_response(text: Optional[str]) -> bool:
    """Flexible detector for the 'invalid resume' sentinel (and common non-compliance variants)."""
    normalized = normalize_llm_text(text)
    if not normalized:
        return False

    # Strict match (preferred)
    if normalized == INVALID_RESUME_SENTINEL:
        return True

    # Slight variations: extra whitespace, case differences, or sentence embedded in longer output.
    if INVALID_RESUME_SENTINEL.lower() in normalized.lower():
        return True

    # Heuristics for models that ignore the strict instruction.
    # Keep this conservative but useful for benchmarking.
    patterns = [
        r"\bnot\s+a\s+resume\b",
        r"\bisn['’]?t\s+a\s+resume\b",
        r"\bthis\s+is\s+not\s+a\s+resume\b",
        r"\bnot\s+actually\s+a\s+resume\b",
        r"\bcommand\s+reference\b",
        r"\btechnical\s+manual\b",
        r"\bdocumentation\b",
    ]
    lowered = normalized.lower()
    return any(re.search(p, lowered) for p in patterns)
