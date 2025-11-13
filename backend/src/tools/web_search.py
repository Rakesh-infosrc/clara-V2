import asyncio
import html
import logging
import re
from typing import List, Tuple, Optional, Dict

import requests
from livekit.agents import RunContext, function_tool
from mem0_client import add_employee_memory

logger = logging.getLogger(__name__)


def _resolve_mem_identity() -> tuple[Optional[str], Optional[str], Optional[Dict[str, str]]]:
    """Resolve current verified employee identity for private Mem0 storage."""
    try:
        from flow_manager import flow_manager
        session = flow_manager.get_current_session()
    except Exception:
        session = None

    employee_id: Optional[str] = None
    employee_name: Optional[str] = None
    if session and session.is_verified:
        employee_id = (
            session.user_data.get("employee_id")
            or session.user_data.get("manual_employee_id")
        )
        employee_name = (
            session.user_data.get("employee_name")
            or session.user_data.get("manual_name")
        )

    if not (employee_id or employee_name):
        try:
            from agent_state import (
                load_state_from_file as _load_state,
                is_verified as _is_verified,
                verified_user_name as _v_name,
                verified_user_id as _v_id,
            )
            _load_state()
            if _is_verified:
                employee_id = employee_id or _v_id
                employee_name = employee_name or _v_name
        except Exception:
            pass

    if not (employee_id or employee_name):
        return None, None, None

    if employee_id and employee_name:
        mem_user_id = f"{employee_id}:{employee_name}"
    else:
        mem_user_id = employee_id or employee_name

    metadata = {
        "employee_id": employee_id or "",
        "employee_name": employee_name or "",
        "type": "web_search",
    }
    return mem_user_id, employee_name, metadata


@function_tool()
async def search_web(context: RunContext, query: str) -> str:
    """Search the web using DuckDuckGo."""
    normalized_query = query.strip()
    if not normalized_query:
        return "Please provide a search query."

    errors: list[str] = []

    try:
        results = await asyncio.wait_for(_duckduckgo_text_search(normalized_query), timeout=10)
        if results:
            # Auto-store for verified employees with topic-focused summary and categories
            try:
                mem_user_id, employee_name, metadata = _resolve_mem_identity()
                if mem_user_id:
                    preview = _format_text_results(results)[:500]
                    # Build a concise topic summary from top results
                    try:
                        titles = [t for (t, _b, _u) in results[:3]]
                        links = [u for (_t, _b, u) in results if u][:3]
                        title_join = "; ".join(titles)
                        link_join = ", ".join(links)
                        summary = f"Summary: {normalized_query} — Top results: {title_join}. Sources: {link_join}"
                    except Exception:
                        summary = f"Summary: {normalized_query} — Top results available."

                    # Topic slug for custom categories
                    try:
                        topic_slug = re.sub(r"[^a-z0-9]+", "_", normalized_query.lower()).strip("_") or "topic"
                    except Exception:
                        topic_slug = "topic"

                    payload = [
                        {"role": "user", "content": f"Search for: {normalized_query}"},
                        {"role": "assistant", "content": f"{summary}\n\n{preview}"},
                    ]

                    custom_categories = [
                        {"web_search": "Auto-stored web search results"},
                        {"technology": "Technology-related search and research"},
                        {topic_slug: f"Topic: {normalized_query}"},
                    ]

                    meta = dict(metadata or {})
                    meta["detail"] = summary
                    meta["categories"] = ",".join({"web_search", "technology", topic_slug})

                    add_employee_memory(
                        payload,
                        user_id=mem_user_id,
                        metadata=meta,
                        entities=[employee_name] if employee_name else None,
                        custom_categories=custom_categories,
                        output_format="v1.1",
                    )
            except Exception:
                logger.debug("Skipping Mem0 auto-store for web search", exc_info=True)
            return _format_text_results(results)
        errors.append("No results returned from text endpoint.")
    except Exception as err:
        message = f"Primary DuckDuckGo search failed: {err}"
        logger.warning(message, exc_info=True)
        errors.append(message)

    try:
        instant_answer = await asyncio.wait_for(_duckduckgo_instant_answer(normalized_query), timeout=6)
        if instant_answer:
            # Auto-store instant answers with categories
            try:
                mem_user_id, employee_name, metadata = _resolve_mem_identity()
                if mem_user_id:
                    preview = instant_answer[:500]
                    try:
                        topic_slug = re.sub(r"[^a-z0-9]+", "_", normalized_query.lower()).strip("_") or "topic"
                    except Exception:
                        topic_slug = "topic"
                    payload = [
                        {"role": "user", "content": f"Search for: {normalized_query}"},
                        {"role": "assistant", "content": f"Summary: {normalized_query} — Instant answer.\n\n{preview}"},
                    ]
                    custom_categories = [
                        {"web_search": "Auto-stored web search results"},
                        {"technology": "Technology-related search and research"},
                        {topic_slug: f"Topic: {normalized_query}"},
                    ]
                    meta = dict(metadata or {})
                    meta["detail"] = f"Summary: {normalized_query} — Instant answer."
                    meta["categories"] = ",".join({"web_search", "technology", topic_slug})
                    add_employee_memory(
                        payload,
                        user_id=mem_user_id,
                        metadata=meta,
                        entities=[employee_name] if employee_name else None,
                        custom_categories=custom_categories,
                        output_format="v1.1",
                    )
            except Exception:
                logger.debug("Skipping Mem0 auto-store for instant answer", exc_info=True)
            return instant_answer
        errors.append("Instant answer API returned empty response.")
    except Exception as err:
        message = f"DuckDuckGo instant answer fallback failed: {err}"
        logger.warning(message, exc_info=True)
        errors.append(message)

    try:
        html_results = await asyncio.wait_for(_duckduckgo_html_fallback(normalized_query), timeout=8)
        if html_results:
            # Auto-store HTML fallback results with categories
            try:
                mem_user_id, employee_name, metadata = _resolve_mem_identity()
                if mem_user_id:
                    preview = _format_text_results(html_results)[:500]
                    try:
                        topic_slug = re.sub(r"[^a-z0-9]+", "_", normalized_query.lower()).strip("_") or "topic"
                    except Exception:
                        topic_slug = "topic"
                    payload = [
                        {"role": "user", "content": f"Search for: {normalized_query}"},
                        {"role": "assistant", "content": f"Summary: {normalized_query} — Fallback results.\n\n{preview}"},
                    ]
                    custom_categories = [
                        {"web_search": "Auto-stored web search results"},
                        {"technology": "Technology-related search and research"},
                        {topic_slug: f"Topic: {normalized_query}"},
                    ]
                    meta = dict(metadata or {})
                    meta["detail"] = f"Summary: {normalized_query} — Fallback results."
                    meta["categories"] = ",".join({"web_search", "technology", topic_slug})
                    add_employee_memory(
                        payload,
                        user_id=mem_user_id,
                        metadata=meta,
                        entities=[employee_name] if employee_name else None,
                        custom_categories=custom_categories,
                        output_format="v1.1",
                    )
            except Exception:
                logger.debug("Skipping Mem0 auto-store for HTML fallback", exc_info=True)
            return _format_text_results(html_results)
        errors.append("HTML fallback produced no results.")
    except Exception as err:
        message = f"DuckDuckGo HTML fallback failed: {err}"
        logger.warning(message, exc_info=True)
        errors.append(message)

    if errors:
        combined = " \n".join(errors)
        logger.error("All DuckDuckGo strategies failed. Details: %s", combined)

    return (
        "I'm unable to retrieve search results right now because all search "
        "strategies failed. The support team has been notified."
    )


async def _duckduckgo_text_search(query: str) -> List[Tuple[str, str, str]]:
    def _run_search() -> List[Tuple[str, str, str]]:
        try:
            from ddgs import DDGS  # type: ignore
        except ImportError:
            from duckduckgo_search import DDGS  # type: ignore

        with DDGS() as ddgs:  # type: ignore[arg-type]
            results = ddgs.text(  # type: ignore[call-arg]
                query,
                max_results=5,
                safesearch="moderate",
                region="wt-wt",
            )
            formatted: List[Tuple[str, str, str]] = []
            for result in results:
                title = result.get("title") or "No title"
                body = result.get("body") or result.get("abstract") or "No description"
                url = result.get("href") or result.get("url") or ""
                formatted.append((title, body, url))
            return formatted

    return await asyncio.to_thread(_run_search)


async def _duckduckgo_instant_answer(query: str) -> str:
    def _call_instant_answer() -> str:
        params = {
            "q": query,
            "format": "json",
            "no_html": "1",
            "no_redirect": "1",
        }
        response = requests.get(
            "https://api.duckduckgo.com/",
            params=params,
            timeout=(4, 6),
            headers={"User-Agent": "Mozilla/5.0 (ClaraAgent/1.0)"},
        )
        response.raise_for_status()
        data = response.json()

        abstract = data.get("AbstractText")
        heading = data.get("Heading")
        if abstract and heading:
            return f"**{heading}**\n{abstract}"

        related_topics = data.get("RelatedTopics", [])
        summaries: List[str] = []
        for topic in related_topics:
            if isinstance(topic, dict):
                text = topic.get("Text")
                url = topic.get("FirstURL")
                if text and url:
                    summaries.append(f"• {text}\n  {url}")
            elif isinstance(topic, list):
                for item in topic:
                    text = item.get("Text")
                    url = item.get("FirstURL")
                    if text and url:
                        summaries.append(f"• {text}\n  {url}")

        if summaries:
            return "Here are some related findings:\n" + "\n".join(summaries[:5])

        return ""

    return await asyncio.to_thread(_call_instant_answer)


async def _duckduckgo_html_fallback(query: str) -> List[Tuple[str, str, str]]:
    def _call_html() -> List[Tuple[str, str, str]]:
        params = {"q": query, "ia": "web"}
        response = requests.get(
            "https://html.duckduckgo.com/html/",
            params=params,
            timeout=(4, 6),
            headers={
                "User-Agent": "Mozilla/5.0 (ClaraAgent/1.0)",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        response.raise_for_status()

        matches = re.findall(
            r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
            response.text,
            flags=re.IGNORECASE | re.DOTALL,
        )

        cleaned_results: List[Tuple[str, str, str]] = []
        for href, link_html in matches[:5]:
            text = re.sub(r"<[^>]+>", " ", link_html)
            text = html.unescape(" ".join(text.split()))
            url = html.unescape(href)
            cleaned_results.append((text, "", url))
        return cleaned_results

    return await asyncio.to_thread(_call_html)


def _format_text_results(results: List[Tuple[str, str, str]]) -> str:
    formatted_sections = []
    for title, body, url in results:
        section = f"**{title}**\n{body}"
        if url:
            section += f"\n{url}"
        formatted_sections.append(section)
    return "\n\n".join(formatted_sections)