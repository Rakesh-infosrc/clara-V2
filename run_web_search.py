#!/usr/bin/env python3
"""Utility script to exercise the Clara web_search tool."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend" / "src"))

from tools.web_search import search_web  # noqa: E402


async def main() -> None:
    query = "do web search of frontech"
    result = await search_web(None, query)
    print(f"➡️ Query: {query}\n\n{result}")


if __name__ == "__main__":
    asyncio.run(main())
