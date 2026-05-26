# One-shot setup. Run from anywhere - figures out abc folder location.
# Idempotent (safe to re-run).
# English-only output to avoid PowerShell 5.1 UTF-8 encoding issues.

$ErrorActionPreference = "Continue"

$ABC = (Resolve-Path "$PSScriptRoot\..").Path

Write-Host ""
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host " Assistant setup - $ABC"                            -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""

# ---------- [1/5] code ----------
Write-Host "[1/5] Pulling latest code..." -ForegroundColor Cyan
Set-Location $ABC
git pull 2>&1 | ForEach-Object { Write-Host "    $_" }
Write-Host ""

# ---------- [2/5] .env ----------
Write-Host "[2/5] Writing .env..." -ForegroundColor Cyan
$envPath = Join-Path $ABC ".env"
$envContent = @"
TELEGRAM_BOT_TOKEN=8859704218:AAEkldOl6nzu9ewDzkKLbvpppxhTsubcdpc
TELEGRAM_CHAT_ID=6714828228
TIMEZONE=Asia/Seoul
"@
Set-Content -Path $envPath -Value $envContent -Encoding UTF8
Write-Host "    Wrote: $envPath" -ForegroundColor Green
Write-Host ""

# ---------- [3/5] Python deps ----------
Write-Host "[3/5] Installing Python packages (1-2 min)..." -ForegroundColor Cyan
$pythonExe = (Get-Command python -ErrorAction SilentlyContinue).Path
if (-not $pythonExe) {
    Write-Host "    [FAIL] python not found." -ForegroundColor Red
    Write-Host "    Install from https://www.python.org/downloads/ then re-run." -ForegroundColor Red
} else {
    Write-Host "    using: $pythonExe" -ForegroundColor Gray
    & python -m pip install --upgrade pip --quiet 2>&1 | ForEach-Object { Write-Host "    $_" }
    & python -m pip install -r requirements.txt --quiet 2>&1 | ForEach-Object { Write-Host "    $_" }
    Write-Host "    Done." -ForegroundColor Green
}
Write-Host ""

# ---------- [4/5] ffmpeg ----------
Write-Host "[4/5] Checking ffmpeg (for voice messages)..." -ForegroundColor Cyan
$ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
if ($ffmpeg) {
    Write-Host "    Found: $($ffmpeg.Path)" -ForegroundColor Green
} else {
    Write-Host "    Not found. Trying winget install..." -ForegroundColor Yellow
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($winget) {
        winget install --id=Gyan.FFmpeg -e --silent --accept-source-agreements --accept-package-agreements 2>&1 | ForEach-Object { Write-Host "    $_" }
        Write-Host "    Installed. CLOSE this PowerShell and reopen so PATH picks up ffmpeg." -ForegroundColor Yellow
    } else {
        Write-Host "    winget not available. Manual install: https://www.gyan.dev/ffmpeg/builds/" -ForegroundColor Yellow
        Write-Host "    (Optional - assistant still works without ffmpeg; voice will fall back to mp3.)" -ForegroundColor Gray
    }
}
Write-Host ""

# ---------- [5/5] claude CLI ----------
Write-Host "[5/5] Checking claude CLI (for Max subscription calls)..." -ForegroundColor Cyan
$claude = Get-Command claude -ErrorAction SilentlyContinue
if ($claude) {
    Write-Host "    Found: $($claude.Path)" -ForegroundColor Green
    Write-Host "    If not logged in yet: claude /login" -ForegroundColor Gray
} else {
    Write-Host "    [FAIL] claude CLI not found." -ForegroundColor Red
    Write-Host "    Install from https://claude.ai/code then run: claude /login" -ForegroundColor Red
}
Write-Host ""

Write-Host "===================================================" -ForegroundColor Green
Write-Host " Setup complete. To start the assistant:"            -ForegroundColor Green
Write-Host ""                                                    -ForegroundColor Green
Write-Host "   cd `$HOME\Desktop\abc"                            -ForegroundColor Yellow
Write-Host "   python -m src.main"                               -ForegroundColor Yellow
Write-Host ""                                                    -ForegroundColor Green
Write-Host " Then in Telegram, send /brief to the bot"           -ForegroundColor Green
Write-Host " to get the first AI-generated morning brief."       -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Green
Write-Host ""

$startNow = Read-Host "Start the assistant now? (y/N)"
if ($startNow -eq "y" -or $startNow -eq "Y") {
    Write-Host ""
    Write-Host "Starting. Press Ctrl+C to stop." -ForegroundColor Cyan
    Write-Host ""
    & python -m src.main
}
