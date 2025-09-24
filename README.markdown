# Virtual Receptionist: AI-Powered Virtual Assistant

## Overview
Virtual Receptionist is an AI-powered virtual receptionist designed to handle intelligent tasks for an IT company. Built using **LiveKit**, it leverages real-time communication, natural language processing, and external APIs to assist employees, candidates, and visitors. The agent, named **Divya**, can greet users, fetch weather updates, send emails, perform web searches, and retrieve employee or candidate details from CSV files. Additionally, it supports **Tavus** for avatar-based interactions, providing a lifelike visual experience for users.

This project is inspired by the [LiveKit Tutorial on YouTube](https://youtu.be/An4NwL8QSQ4?si=1pLISaiUBGafE8XJ), which demonstrates building a JARVIS-like AI agent.

## Features
- **Greetings & Personalization**: Divya greets employees and candidates by name, offering a professional and warm interaction.
- **Weather Updates**: Retrieves current weather for a specified city using the `wttr.in` API.
- **Web Search**: Performs web searches via DuckDuckGo.
- **Email Sending**: Sends emails through Gmail using SMTP.
- **Employee/Candidate Lookup**: Fetches details from CSV files for employees or interview candidates.
- **Noise Cancellation**: Utilizes LiveKit's noise cancellation for clear audio interactions.
- **Real-Time Interaction**: Powered by LiveKit's real-time communication framework and Google’s RealtimeModel for natural language processing.
- **Tavu Avatar Integration**: Provides a realistic avatar for Divya using Tavus’s API, enhancing the user experience with visual and voice interactions.

## Prerequisites
- **Python 3.8+**
- **LiveKit Cloud Account**: Obtain API keys from [LiveKit Cloud](https://livekit.io/).
- **Google Cloud Account**: For Google’s RealtimeModel API key.
- **Gmail Account**: Configure an App Password for email functionality.
- **Tavus Account**: Required for avatar-based interactions. Sign up at [Tavus](https://www.tavus.io/) to obtain `PERSONA_ID`, `REPLICA_ID`, and `TAVUS_API_KEY`.
- CSV files (`employees.csv`, `candidates.csv`) with appropriate data in the project directory.

## Installation
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/yourusername/virtual-receptionist.git
   cd virtual-receptionist
   ```

2. **Install Dependencies**:
   Ensure you have `pip` installed, then run:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set Up Environment Variables**:
   Create a `.env` file in the project root and populate it with the following:
   ```plaintext
   LIVEKIT_URL=<your-livekit-url>
   LIVEKIT_API_KEY=<your-livekit-api-key>
   LIVEKIT_API_SECRET=<your-livekit-api-secret>
   GOOGLE_API_KEY=<your-google-api-key>
   GMAIL_APP_PASSWORD=<your-gmail-app-password>
   GMAIL_USER=<your-gmail-email>
   PERSONA_ID=<your-tavus-personapitfall
   REPLICA_ID=<your-tavus-replica-id>
   TAVUS_API_KEY=<your-tavus-api-key>
   ```

4. **Prepare CSV Files**:
   Place `employees.csv` and `candidates.csv` in the `dummy-data` directory. Expected formats:
   - **employees.csv**: Columns: `name`, `department`, `role`, `email`
   - **candidates.csv**: Columns: `name`, `position`, `interview_time`, `email`

## Usage
1. **Run the Agent**:
   Follow these steps to run the agent in different modes:
   - **Step 1**: Activate the virtual environment:
     ```bash
     .\venv\Scripts\activate
     ```
   - **Step 2**: Run in console mode (terminal-based interaction):
     ```bash
     python agent.py console
     ```
   - **Step 3**: Run with LiveKit for camera access (enables webcam and microphone):
     ```bash
     python agent.py dev
     ```
   - **Step 4**: Access the LiveKit Playground for a web-based interface:
     Open [LiveKit Playground](https://agents-playground.livekit.io/#cam=1&mic=1&screen=1&video=1&audio=1&chat=1&theme_color=amber) in your browser.

2. **Interact with Divya**:
   - Divya starts every conversation with: "Hello, my name is Divya, the company receptionist, how may I help you today?"
   - Example interactions:
     - **Employee**: "Hi Divya, can you book me a meeting room?"
       - Response: "Of course Rakesh, I’ll handle that right away. Meeting room booked successfully."
     - **Candidate**: "Hi, I’m here for an interview with Mr. Sharma."
       - Response: "Welcome, I see you’re scheduled with Mr. Sharma at 11 AM. Please wait in the lounge, someone will escort you shortly."
     - **New Visitor**: "Hello"
       - Response: "Hello, I don’t believe we’ve met before—may I know your name and purpose of visit?"

3. **Available Tools**:
   - **Weather**: `get_weather(city)` - Fetch weather for a city.
   - **Web Search**: `search_web(query)` - Search the web using DuckDuckGo.
   - **Email**: `send_email(to_email, subject, message, cc_email)` - Send an email via Gmail.
   - **Person Lookup**: `get_person_details(name, person_type)` - Retrieve employee or candidate details.

4. **Tavus Avatar**:
   - When enabled, Divya appears as a realistic avatar powered by Tavus, providing a more engaging visual and voice-based interaction.
   - Requires valid `PERSONA_ID`, `REPLICA_ID`, and `TAVUS_API_KEY` in the `.env` file.
   - To disable Tavus, comment out the avatar session code in `agent.py`.

## Project Structure
- `agent.py`: Main script to initialize and run the assistant, including Tavus avatar integration.
- `tools.py`: Contains tools for weather, email, web search, and person lookup.
- `prompts.py`: Defines Divya’s persona, instructions, and session behavior.
- `requirements.txt`: Lists Python dependencies, including `livekit-agents[tavus]`.
- `.env`: Stores environment variables (not tracked in git).
- `dummy-data/`: Directory for `employees.csv` and `candidates.csv`.

## Notes
- **Tavus Integration**: The Tavus avatar session is commented out in `agent.py` by default. Uncomment and configure with valid Tavus credentials to enable the avatar feature. Ensure `PERSONA_ID`, `REPLICA_ID`, and `TAVUS_API_KEY` are correctly set in `.env`. Visit [Tavus Documentation](https://docs.tavus.io/) for setup details.
- **Error Handling**: Tools include robust error handling with logging for debugging.
- **Security**: Ensure sensitive data like API keys and Gmail credentials are stored securely in the `.env` file and not exposed in version control.
- **Customization**: Modify `prompts.py` to adjust Divya’s tone, style, or capabilities.

## Troubleshooting
- **Missing CSV Files**: Ensure `employees.csv` and `candidates.csv` are in the correct directory.
- **API Key Issues**: Verify all API keys in `.env` are valid, including Tavus credentials.
- **Connection Errors**: Check `LIVEKIT_URL` and ensure your LiveKit server is running.
- **Email Issues**: Confirm Gmail App Password is correctly set up (not your regular Gmail password).
- **Tavus Errors**: Ensure Tavus API keys and IDs are correct. Check Tavus dashboard for valid `PERSONA_ID` and `REPLICA_ID`.

## Acknowledgments
- Built with [LiveKit](https://livekit.io/) for real-time communication.
- Powered by [Tavus](https://www.tavus.io/) for realistic avatar interactions.
- Inspired by the [LiveKit Tutorial on YouTube](https://youtu.be/An4NwL8QSQ4?si=1pLISaiUBGafE8XJ).
- Uses Google’s RealtimeModel for LLM capabilities and DuckDuckGo for web searches.

## License
This project is licensed under the MIT License.