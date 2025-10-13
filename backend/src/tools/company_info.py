import io
from typing import List, Tuple

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from PyPDF2 import PdfReader
from livekit.agents import function_tool, RunContext

from .config import get_company_info_location


LANGUAGE_RANGES = {
    "ta": [(0x0B80, 0x0BFF)],  # Tamil
    "te": [(0x0C00, 0x0C7F)],  # Telugu
    "hi": [(0x0900, 0x097F)],  # Devanagari (Hindi)
}


def _line_has_language_chars(line: str, ranges: List[Tuple[int, int]]) -> bool:
    for ch in line:
        cp = ord(ch)
        for start, end in ranges:
            if start <= cp <= end:
                return True
    return False


def _filter_text_for_language(text: str, lang: str) -> str:
    ranges = LANGUAGE_RANGES.get(lang)
    if not ranges:
        return text

    filtered_lines = [line for line in text.splitlines() if _line_has_language_chars(line, ranges)]
    if filtered_lines:
        return "\n".join(filtered_lines)
    return text


def _get_current_language() -> str:
    try:
        from agent_state import get_preferred_language  # Local import to avoid circular dependency
        return get_preferred_language()
    except Exception:
        return "en"

def _fetch_company_pdf_bytes() -> tuple[bytes | None, str | None]:
    """Fetch the company info PDF bytes from S3."""

    bucket, key = get_company_info_location()
    if not bucket or not key:
        return None, "Company information file is missing and no S3 location is configured."

    try:
        s3 = boto3.client("s3")
        response = s3.get_object(Bucket=bucket, Key=key)
        data = response["Body"].read()
        if not data:
            return None, "Company information file appears to be empty."
        return data, None
    except (BotoCoreError, ClientError) as s3_err:
        return None, f"Could not fetch company info from S3 ({bucket}/{key}): {s3_err}"
    except Exception as err:
        return None, f"Unexpected error fetching company info: {err}"


@function_tool()
async def company_info(
    context: RunContext,  # type: ignore
    query: str = "general"
) -> str:
    """
    Fetch company information from company_info.pdf.
    
    Args:
        query: Optional keyword to search inside the PDF. 
               If 'general', return the first page summary.
    """
    try:
        pdf_bytes, error_msg = _fetch_company_pdf_bytes()
        if not pdf_bytes:
            return error_msg or "Company information file is missing."

        reader = PdfReader(io.BytesIO(pdf_bytes))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"

        if not text.strip():
            return "Company information could not be extracted."

        lang = _get_current_language()
        localized_text = _filter_text_for_language(text, lang)

        # If user asked general
        if query.lower() == "general":
            snippet = localized_text[:600] if localized_text else ""
            return (snippet or text[:600]) + "..."

        # Search for keyword inside text
        query_lower = query.lower()
        matches = [line for line in localized_text.split("\n") if query_lower in line.lower()]

        if matches:
            return " | ".join(matches[:5])  # return top 5 matches
        else:
            # Fallback: search entire document before giving up
            backup_matches = [line for line in text.split("\n") if query_lower in line.lower()]
            if backup_matches:
                return " | ".join(backup_matches[:5])
            return f"No specific details found for '{query}'."

    except Exception as e:
        return f"Error reading company information: {str(e)}"