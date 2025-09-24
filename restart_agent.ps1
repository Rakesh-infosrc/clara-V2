# PowerShell script to restart Clara Agent with Wake Word Detection Fix
Write-Host "🔄 Restarting Clara Agent with Wake Word Detection Fix" -ForegroundColor Green
Write-Host "====================================================" -ForegroundColor Green

Write-Host "🛑 Stopping existing Python processes..." -ForegroundColor Yellow
Get-Process -Name "python" -ErrorAction SilentlyContinue | Stop-Process -Force

Write-Host "⏳ Waiting 3 seconds..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

Write-Host "🚀 Activating virtual environment and starting Clara Agent..." -ForegroundColor Green
$VenvDir = "D:\AI FIX\New Flow\Virtual_Receptionist\backend"
$PythonPath = "D:\AI FIX\New Flow\Virtual_Receptionist\backend\venv\Scripts\python.exe"
Start-Process -FilePath $PythonPath -ArgumentList "main.py", "dev" -WorkingDirectory $VenvDir -WindowStyle Normal

Write-Host ""
Write-Host "✅ Agent restarted with new configuration!" -ForegroundColor Green
Write-Host ""
Write-Host "🔧 Changes Applied:" -ForegroundColor Cyan
Write-Host "- Clara now starts in SLEEP mode" -ForegroundColor White
Write-Host "- Only responds to 'Hey Clara' wake word" -ForegroundColor White  
Write-Host "- Proper voice recognition and flow handling" -ForegroundColor White
Write-Host "- Debug logging enabled for troubleshooting" -ForegroundColor White
Write-Host ""
Write-Host "💬 Testing Instructions:" -ForegroundColor Yellow
Write-Host "1. Wait for agent to connect to LiveKit" -ForegroundColor White
Write-Host "2. Say 'Hey Clara' to wake her up" -ForegroundColor White
Write-Host "3. She should respond: 'I'm awake! Hello! Are you an Employee or a Visitor?'" -ForegroundColor White
Write-Host "4. Say 'I am an employee' to trigger face recognition" -ForegroundColor White
Write-Host ""
Write-Host "🎯 Look at the backend terminal for debug messages!" -ForegroundColor Magenta

# Check if process started successfully
Start-Sleep -Seconds 2
$pythonProcess = Get-Process -Name "python" -ErrorAction SilentlyContinue
if ($pythonProcess) {
    Write-Host "✅ Clara Agent is running!" -ForegroundColor Green
} else {
    Write-Host "❌ Agent failed to start. Check for errors." -ForegroundColor Red
}

Write-Host ""
Write-Host "Press any key to continue..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")