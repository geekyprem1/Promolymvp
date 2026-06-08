# ReelForge MVP - Setup Script (Windows PowerShell)
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ReelForge MVP - Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# --- Backend ---
Write-Host "`n[1/4] Setting up Python backend..." -ForegroundColor Yellow
Set-Location "$PSScriptRoot\backend"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Python not found. Install Python 3.10+ first." -ForegroundColor Red
    exit 1
}

python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
Write-Host "Backend ready." -ForegroundColor Green

# --- Frontend ---
Write-Host "`n[2/4] Setting up frontend..." -ForegroundColor Yellow
Set-Location "$PSScriptRoot\frontend"

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Node.js not found. Install Node.js 18+ first." -ForegroundColor Red
    exit 1
}

npm install
Write-Host "Frontend ready." -ForegroundColor Green

# --- FFmpeg check ---
Write-Host "`n[3/4] Checking FFmpeg..." -ForegroundColor Yellow
if (Get-Command ffmpeg -ErrorAction SilentlyContinue) {
    Write-Host "FFmpeg found." -ForegroundColor Green
} else {
    Write-Host "WARNING: FFmpeg not found in PATH." -ForegroundColor Red
    Write-Host "  Download from https://ffmpeg.org/download.html and add to PATH." -ForegroundColor Yellow
}

Write-Host "`n[4/4] Setup complete!" -ForegroundColor Green
Write-Host "`nTo start ReelForge, run:" -ForegroundColor Cyan
Write-Host "  Backend:  cd backend && .\venv\Scripts\Activate.ps1 && uvicorn main:app --reload --port 8000"
Write-Host "  Frontend: cd frontend && npm run dev"
Write-Host "`nOpen: http://localhost:5173" -ForegroundColor Cyan
