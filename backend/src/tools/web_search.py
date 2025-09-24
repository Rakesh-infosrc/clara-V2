from livekit.agents import function_tool, RunContext
from langchain_community.tools import DuckDuckGoSearchRun


@function_tool()
async def search_web(context: RunContext, query: str) -> str:
    """Search the web using DuckDuckGo."""
    try:
        return DuckDuckGoSearchRun().run(tool_input=query)
    except Exception as e:
        return f"❌ Error searching the web: {e}"