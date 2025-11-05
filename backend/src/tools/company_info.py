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
    Fetch company information from company_info.pdf stored in S3.
    
    Args:
        query: Optional keyword to search inside the PDF. 
               If 'general', return comprehensive company overview.
               Common queries: 'about', 'services', 'contact', 'location', 'history'
    """
    try:
        pdf_bytes, error_msg = _fetch_company_pdf_bytes()
        if not pdf_bytes:
            return error_msg or "I apologize, but I'm unable to access the company information at the moment. Let me know if you'd like me to bring in a human teammate."

        reader = PdfReader(io.BytesIO(pdf_bytes))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"

        if not text.strip():
            return "I'm sorry, but I couldn't extract the company information from our database. Let me know if you'd like me to involve a team member."

        lang = _get_current_language()
        localized_text = _filter_text_for_language(text, lang)
        
        # Use localized text if available, otherwise fall back to full text
        search_text = localized_text if localized_text.strip() else text

        # Handle different types of queries
        query_lower = query.lower().strip()
        
        # General company information
        if query_lower in ["general", "about", "company", "info", "information", "overview"]:
            # Return first 1500 characters for a good overview, but break at sentence boundary
            max_length = 1500
            snippet = search_text[:max_length] if search_text else ""
            
            # Find the last complete sentence within the limit
            if len(search_text) > max_length:
                # Look for sentence endings (., !, ?)
                last_period = max(snippet.rfind('.'), snippet.rfind('!'), snippet.rfind('?'))
                if last_period > 500:  # Only break at sentence if we have at least 500 chars
                    snippet = snippet[:last_period + 1]
                snippet += "\n\n...Would you like to know more about any specific aspect?"
            
            return f"Here's information about our company:\n\n{snippet}"

        # Specific keyword search
        lines = search_text.split("\n")
        matches = []
        
        # Search for exact matches first
        for line in lines:
            if query_lower in line.lower() and line.strip():
                matches.append(line.strip())
                
        # If no exact matches, try broader search
        if not matches:
            for line in lines:
                if any(word in line.lower() for word in query_lower.split()) and line.strip():
                    matches.append(line.strip())

        if matches:
            # Return top 3 most relevant matches
            result = "\n".join(matches[:3])
            return f"Here's what I found about '{query}':\n\n{result}"
        else:
            # Fallback: provide general info and suggest alternatives
            snippet = search_text[:400] if search_text else ""
            return (
                f"I couldn't find specific information about '{query}', but here's some general company information:\n\n"
                f"{snippet}...\n\nLet me know if you'd like me to connect you with a human teammate for more details."
            )

    except Exception as e:
        return (
            "I'm experiencing technical difficulties accessing company information. "
            f"I've logged the issue and can loop in a human teammate if needed. Error: {str(e)}"
        )