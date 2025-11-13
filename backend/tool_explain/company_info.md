# Company Info Tool

> Source: `src/tools/company_info.py`

## Purpose

Fetches company information from a PDF stored in S3 and returns localized snippets that answer common questions (general overview, services, contact details, etc.). Provides graceful fallbacks when the PDF is missing or empty.

## Key Functions

- `company_info(..)`: LiveKit tool entry point that orchestrates PDF retrieval, text extraction, language filtering, and query matching.
- `_fetch_company_pdf_bytes()`: Downloads the PDF payload from the S3 bucket/key configured in `config.py`.
- `_filter_text_for_language(..)`: Keeps only lines containing characters for the currently selected language (Tamil, Telugu, Hindi) when possible.
- `_get_current_language()`: Reads the preferred language from `agent_state` so messaging stays consistent with the session.

## Inputs

- `query` (str, default `"general"`): Keyword indicating what part of the company information the caller wants. Examples: "about", "services", "contact".
- The tool implicitly depends on the agent's preferred language (no explicit argument) to localize responses.

## Outputs

- Returns a user-facing string summarizing the requested information, or diagnostic messages when source data is missing, blank, or unreadable.

## Dependencies

- **Environment variables** (via `config.py`): `COMPANY_INFO_S3_BUCKET`, `COMPANY_INFO_S3_KEY`.
- **AWS services**: S3 for storing the PDF.
- **Libraries**: `boto3`, `PyPDF2`, and the local `agent_state` module for language selection.

## Typical Usage

```text
1. Agent calls company_info(context, query="about") during a conversation.
2. Tool pulls the PDF from S3, extracts text, filters it by language, and returns a concise answer.
3. Agent relays the answer to the user or follows up if nothing relevant was found.
```

## Error Handling & Edge Cases

- Missing bucket/key → returns a friendly message prompting the user to involve a human teammate.
- Empty or unreadable PDF → returns a summary explaining the issue.
- No matching lines for the query → falls back to a general snippet plus a prompt for follow-up questions.
- Unexpected exceptions are caught and surfaced as a generic failure notice that can be escalated.

## Related Files

- `src/tools/config.py` for bucket/key configuration.
- `src/agent.py` (`get_company_information`) which prefers this tool before using web search fallbacks.
- `src/tools/web_search.py` provides the secondary path when the PDF does not contain answers.
