import requests
from livekit.agents import function_tool, RunContext


@function_tool()
async def get_weather(context: RunContext, city: str) -> str:
    """Get the current weather for a given city."""
    try:
        response = requests.get(f"https://wttr.in/{city}?format=3")
        return response.text.strip() if response.status_code == 200 else "❌ Could not retrieve weather."
    except Exception as e:
        return f"❌ Error retrieving weather: {e}"