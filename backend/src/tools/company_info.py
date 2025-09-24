import os
from PyPDF2 import PdfReader
from livekit.agents import function_tool, RunContext
from .config import COMPANY_INFO_PDF


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
        if not os.path.exists(COMPANY_INFO_PDF):
            return "Company information file is missing."

        reader = PdfReader(COMPANY_INFO_PDF)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"

        if not text.strip():
            return "Company information could not be extracted."

        # If user asked general
        if query.lower() == "general":
            return text[:600] + "..."  # return first ~600 chars

        # Search for keyword inside text
        query_lower = query.lower()
        matches = [line for line in text.split("\n") if query_lower in line.lower()]

        if matches:
            return " | ".join(matches[:5])  # return top 5 matches
        else:
            return f"No specific details found for '{query}'."

    except Exception as e:
        return f"Error reading company information: {str(e)}"