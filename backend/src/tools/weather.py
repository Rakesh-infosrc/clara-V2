import requests
from livekit.agents import function_tool, RunContext

from agent_state import get_preferred_language
from language_utils import get_message


@function_tool()
async def get_weather(context: RunContext, city: str) -> str:
    """Get the current weather for a given city."""
    lang = get_preferred_language()
    try:
        response = requests.get(f"https://wttr.in/{city}?format=3")
        if response.status_code == 200:
            report = response.text.strip()
            return get_message("weather_report", lang, city=city, report=report)
        return get_message("weather_error", lang)
    except Exception:
        return get_message("weather_error", lang)