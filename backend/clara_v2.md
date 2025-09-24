# Clara V2 - Virtual Receptionist System 🤖

## Overview
Clara V2 is an intelligent virtual receptionist powered by LiveKit and Google's Realtime AI. She features advanced wake/sleep functionality, face recognition, employee verification, and comprehensive visitor management capabilities.

## 🎯 Key Features

### Wake/Sleep Functionality
- **Sleep State**: Clara ignores all inputs except "Hey Clara"
- **Wake State**: Clara responds to all queries and commands
- **Auto-sleep**: Automatically sleeps after 3 minutes of inactivity
- **Voice Commands**:
  - 🔴 **"Go idle"** → Clara sleeps (😴 Going idle, say 'Hey Clara' to wake me again.)
  - 🟢 **"Hey Clara"** → Clara wakes up (🤖 I'm awake! How can I help?)

### Core Capabilities
- 👤 **Employee Verification** with OTP authentication
- 🎤 **Candidate Interview Management** 
- 👥 **Visitor Registration & Notification**
- 🏢 **Company Information Retrieval**
- 📧 **Email Notifications**
- 🌤️ **Weather Information**
- 🔍 **Web Search**
- 🔐 **Face Recognition** (if configured)

## 📁 Project Structure

```
backend/
├── main.py                 # Main entry point - Run this file
├── clara_v2.md            # This documentation
├── config/                # Configuration files
├── data/                  # Data storage
│   └── dummy-data/        # Sample CSV files and data
│       ├── employee_details.csv
│       ├── candidate_interview.csv
│       ├── company_info.pdf
│       ├── visitor_log.csv
│       └── manager_visit.csv
├── logs/                  # Application logs
└── src/                   # Source code
    ├── agent.py           # Main Clara agent logic
    ├── agent_state.py     # Wake/sleep state management
    ├── prompts.py         # AI prompts and instructions
    ├── face_tool.py       # Face recognition integration
    ├── face_verify.py     # Face verification utilities
    ├── encode_faces.py    # Face encoding utilities
    ├── server.py          # Web server components
    └── tools/             # Modular tool system
        ├── __init__.py
        ├── config.py      # Configuration and paths
        ├── company_info.py         # Company info retrieval
        ├── employee_verification.py # Employee OTP system
        ├── candidate_verification.py # Interview management
        ├── visitor_management.py   # Visitor logging
        ├── wake_sleep.py           # Voice wake/sleep
        ├── weather.py              # Weather information
        ├── web_search.py           # Web search capability
        ├── email_sender.py         # Email functionality
        └── face_recognition.py     # Face recognition tools
```

## 🚀 How to Run Clara V2

### Prerequisites
1. Python 3.8+ installed
2. Virtual environment activated
3. All dependencies installed (`pip install -r requirements.txt`)
4. Environment variables configured (Gmail credentials, API keys)

### Running the Application

```bash
# Navigate to the backend directory
cd "D:\AI FIX\Virtual_Receptionist\backend"

# Activate virtual environment (if not already active)
.\venv\Scripts\Activate.ps1

# Run Clara V2
python main.py
```

### Alternative Run Methods

```bash
# Direct agent run (legacy method)
python src/agent.py

# Development mode with specific arguments
python main.py dev
```

## 💬 User Interaction Flow

### Starting Clara
```
🤖 Starting Clara Virtual Receptionist...
📁 Project structure organized
🎯 Clara is ready with wake/sleep functionality
💬 Say 'Hey Clara' to wake up or 'Go idle' to sleep
--------------------------------------------------
```

### Wake/Sleep Examples

#### Putting Clara to Sleep
```
User: "Go idle"
Clara: "😴 Going idle, say 'Hey Clara' to wake me again."
→ Clara now ignores all inputs
```

#### Clara is Sleeping
```
User: "What's the weather?"
Clara: (no response - sleeping)

User: "Hello there"
Clara: (no response - sleeping)
```

#### Waking Clara Up
```
User: "Hey Clara"
Clara: "🤖 I'm awake! How can I help?"
→ Clara is now responsive to all inputs
```

## 🛠️ Tool System

### Employee Verification
- **Secure OTP System**: Email-based verification
- **Manager Visit Greeting**: Special welcome for visiting managers
- **Retry Protection**: Maximum 3 OTP attempts

### Candidate Management
- **Interview Code Verification**: Unique code-based system
- **Interviewer Notification**: Automatic email alerts
- **Schedule Integration**: Interview timing coordination

### Visitor Management
- **Registration System**: Name, phone, purpose tracking
- **Employee Notification**: Real-time email alerts
- **Visitor Logging**: Comprehensive visit records

### Utility Tools
- **Company Info**: PDF-based information retrieval
- **Weather Service**: Real-time weather updates
- **Web Search**: DuckDuckGo integration
- **Email System**: Gmail SMTP integration

## 🔧 Configuration

### Environment Variables Required
```env
GMAIL_USER=your-email@gmail.com
GMAIL_APP_PASSWORD=your-app-password
TAVUS_API_KEY=your-tavus-key
LIVEKIT_URL=your-livekit-url
LIVEKIT_API_KEY=your-livekit-key
LIVEKIT_API_SECRET=your-livekit-secret
```

### Data Files
- Place CSV files in `data/dummy-data/`
- Face encodings in `data/dummy-data/encoding.pkl`
- Company PDF in `data/dummy-data/company_info.pdf`

## 🎭 Clara's Personality

Clara is designed to be:
- **Professional yet Friendly**: Warm corporate reception experience
- **State-Aware**: Different behavior when awake vs sleeping
- **Contextual**: Responds appropriately based on user type (employee/visitor/candidate)
- **Efficient**: Quick verification and notification systems

## 🔒 Security Features

- **OTP Verification**: Secure employee authentication
- **Session Management**: Temporary session storage
- **Input Validation**: Sanitized user inputs
- **Access Control**: Role-based feature access

## 📊 Monitoring & Logs

- Application logs stored in `logs/` directory
- State changes tracked and logged
- Email delivery confirmations
- Error handling and reporting

## 🚨 Troubleshooting

### Common Issues
1. **Import Errors**: Ensure you're running from the correct directory
2. **File Not Found**: Check that data files are in `data/dummy-data/`
3. **Email Failures**: Verify Gmail credentials and app password
4. **Wake/Sleep Issues**: Check microphone permissions

### Debug Mode
```bash
python main.py --debug
```

## 🔄 Version History

### V2 Improvements
- ✅ Organized file structure
- ✅ Modular tool system
- ✅ Enhanced wake/sleep with emojis
- ✅ Better path management
- ✅ Improved error handling
- ✅ Comprehensive documentation

---

**Clara V2** - Your Intelligent Virtual Receptionist 🏢✨

*Ready to greet, verify, and assist with professional excellence!*