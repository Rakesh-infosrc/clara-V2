# PowerShell script to restart Clara Virtual Receptionist services
Write-Host "🤖 Restarting Clara Virtual Receptionist Services" -ForegroundColor Green
Write-Host "=" * 50

# Kill existing processes
Write-Host "🔄 Stopping existing services..." -ForegroundColor Yellow
Get-Process -Name "python" -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object {$_.ProcessName -eq "node"} | Stop-Process -Force

# Wait a moment for processes to stop
Start-Sleep -Seconds 2

# Get the project directory
$ProjectDir = "D:\AI FIX\New Flow\Virtual_Receptionist"

Write-Host "📁 Project Directory: $ProjectDir" -ForegroundColor Cyan

# Start Backend (Agent)
Write-Host "🚀 Starting Backend Agent..." -ForegroundColor Green
$BackendDir = Join-Path $ProjectDir "backend"
Start-Process -FilePath "python" -ArgumentList "main.py" -WorkingDirectory $BackendDir -WindowStyle Normal

# Wait for backend to initialize
Start-Sleep -Seconds 3

# Start Frontend
Write-Host "🌐 Starting Frontend..." -ForegroundColor Green
$FrontendDir = Join-Path $ProjectDir "frontend"
Start-Process -FilePath "npm" -ArgumentList "run", "dev" -WorkingDirectory $FrontendDir -WindowStyle Normal

Write-Host "✅ Services started!" -ForegroundColor Green
Write-Host "Backend: Clara agent running with name 'clara-receptionist'" -ForegroundColor White
Write-Host "Frontend: Web interface at http://localhost:3000" -ForegroundColor White
Write-Host "LiveKit: Connected to wss://fridayjarvis-nxz35tbu.livekit.cloud" -ForegroundColor White

Write-Host "`n🔧 Configuration Summary:" -ForegroundColor Yellow
Write-Host "- Agent Name: clara-receptionist" -ForegroundColor White
Write-Host "- LiveKit Server: wss://fridayjarvis-nxz35tbu.livekit.cloud" -ForegroundColor White
Write-Host "- API Key: API5pBVs37c2cTU" -ForegroundColor White
Write-Host "- Flow: Employee/Visitor classification → Face recognition" -ForegroundColor White

Write-Host "`n💬 Usage:" -ForegroundColor Yellow
Write-Host "1. Open http://localhost:3000 in your browser" -ForegroundColor White
Write-Host "2. Click 'START CALL' button" -ForegroundColor White
Write-Host "3. Say 'Hey Clara' to wake up the agent" -ForegroundColor White
Write-Host "4. Clara will ask: 'Are you an Employee or a Visitor?'" -ForegroundColor White
Write-Host "5. Respond accordingly to trigger the appropriate flow" -ForegroundColor White

Write-Host "`n🎯 The agent should now connect properly!" -ForegroundColor Green