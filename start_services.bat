@echo off
echo 🤖 Starting Clara Virtual Receptionist Services
echo ====================================================

echo 🚀 Starting Backend Agent...
cd /d "D:\AI FIX\New Flow\Virtual_Receptionist\backend"
start "Clara Backend" cmd /k "python main.py"

echo Waiting 3 seconds for backend to initialize...
timeout /t 3 /nobreak

echo 🌐 Starting Frontend...
cd /d "D:\AI FIX\New Flow\Virtual_Receptionist\frontend"  
start "Clara Frontend" cmd /k "npm run dev"

echo ✅ Services started!
echo.
echo 🔧 Configuration:
echo - Agent Name: clara-receptionist
echo - LiveKit Server: wss://fridayjarvis-nxz35tbu.livekit.cloud
echo - API Key: API5pBVs37c2cTU
echo.
echo 💬 Usage:
echo 1. Open http://localhost:3000 in your browser
echo 2. Click 'START CALL' button  
echo 3. Say 'Hey Clara' to wake up the agent
echo 4. Clara will ask: 'Are you an Employee or a Visitor?'
echo 5. Respond accordingly to trigger the appropriate flow
echo.
echo 🎯 The agent should now connect properly!
pause