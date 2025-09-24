# Agent Connection Fix - Virtual Receptionist

## Problem
The error "Agent did not join the room" indicates that the Clara agent is not connecting to the LiveKit room that the frontend creates.

## Root Cause
The backend agent and frontend were configured to use different LiveKit server instances:
- **Backend**: `wss://fridayjarvis-nxz35tbu.livekit.cloud` (cloud server)
- **Frontend**: `ws://127.0.0.1:7880` (local server)

## Solution Applied

### 1. Fixed Environment Configuration
**Updated `frontend/.env.local`:**
```env
# LiveKit server URL (cloud server - matching backend)
LIVEKIT_URL=wss://fridayjarvis-nxz35tbu.livekit.cloud

# API key & secret (matching backend configuration)
LIVEKIT_API_KEY=API5pBVs37c2cTU
LIVEKIT_API_SECRET=A2oW6SeOeUI6nOOmCEDruAN4KYZSjhKpKfZZyKeT6OgB

# The default room name to join
LIVEKIT_ROOM=reception-room
```

### 2. Added Agent Name Configuration
**Updated `frontend/app-config.ts`:**
```typescript
agentName: 'clara-receptionist',
```

**Updated `backend/src/agent.py` and `backend/main.py`:**
```python
cli.run_app(
    WorkerOptions(
        entrypoint_fnc=entrypoint,
        agent_name="clara-receptionist"
    )
)
```

### 3. Verification Steps
1. Both backend and frontend now use the same LiveKit cloud server
2. Agent has a specific name that the frontend can request
3. API keys and secrets match between backend and frontend

## How to Restart Services

### Option 1: Using PowerShell Script
Run the provided PowerShell script:
```powershell
.\restart_services.ps1
```

### Option 2: Manual Restart
1. **Stop existing processes:**
   ```powershell
   Get-Process -Name "python" | Stop-Process -Force
   Get-Process -Name "node" | Stop-Process -Force
   ```

2. **Start Backend:**
   ```powershell
   cd "D:\AI FIX\New Flow\Virtual_Receptionist\backend"
   python main.py
   ```

3. **Start Frontend (in new terminal):**
   ```powershell
   cd "D:\AI FIX\New Flow\Virtual_Receptionist\frontend"
   npm run dev
   ```

## Expected Behavior
1. Open http://localhost:3000
2. Click "START CALL" button
3. You should see the Clara agent join the room
4. Say "Hey Clara" to activate the agent
5. Clara should respond: Hello, my name is clara, the receptionist at an Info Services, How may I help you today?
5. Clara should respond: " Are you an Employee or a Visitor?"

## Configuration Summary
- **Agent Name**: `clara-receptionist`
- **LiveKit Server**: `wss://fridayjarvis-nxz35tbu.livekit.cloud`
- **API Key**: `API5pBVs37c2cTU`
- **Room**: Random room created by frontend with agent request

## Troubleshooting
If the agent still doesn't connect:

1. **Check Console Logs:**
   - Backend terminal should show LiveKit connection messages
   - Frontend browser console should show room connection details

2. **Verify Network:**
   - Ensure internet connection to reach cloud LiveKit server
   - Check firewall settings for WSS connections

3. **Validate API Keys:**
   - Ensure the LiveKit project is active on the cloud
   - Verify API keys have not expired

4. **Check Agent Registration:**
   - Backend should log "Agent registered" or similar message
   - Frontend should show agent in participant list

The agent connection issue should now be resolved with matching configurations between frontend and backend.