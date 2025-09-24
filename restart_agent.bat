@echo off
echo 🔄 Restarting Clara Agent with Wake Word Detection Fix
echo ====================================================

echo 🛑 Stopping existing Python processes...
taskkill /F /IM python.exe >nul 2>&1

echo ⏳ Waiting 3 seconds...
timeout /t 3 /nobreak >nul

echo 🚀 Starting Clara Agent in SLEEP mode...
cd /d "D:\AI FIX\New Flow\Virtual_Receptionist\backend"
start "Clara Agent" cmd /k "python main.py dev"

echo.
echo ✅ Agent restarted with new configuration!
echo.
echo 🔧 Changes Applied:
echo - Clara now starts in SLEEP mode
echo - Only responds to "Hey Clara" wake word
echo - Proper voice recognition and flow handling
echo - Debug logging enabled for troubleshooting
echo.
echo 💬 Testing Instructions:
echo 1. Wait for agent to connect to LiveKit
echo 2. Say "Hey Clara" to wake her up
echo 3. She should respond: "I'm awake! Hello! Are you an Employee or a Visitor?"
echo 4. Say "I am an employee" to trigger face recognition
echo.
echo 🎯 Look at the backend terminal for debug messages!
pause