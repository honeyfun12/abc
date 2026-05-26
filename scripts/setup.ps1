# One-shot setup. Run from anywhere — figures out abc folder location.
# Idempotent (safe to re-run).

$ErrorActionPreference = "Continue"

# Resolve the abc folder relative to this script.
$ABC = (Resolve-Path "$PSScriptRoot\..").Path

Write-Host ""
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host " 비서 시스템 셋업 — $ABC" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""

# ---------- [1/5] code ----------
Write-Host "[1/5] 코드 최신화..." -ForegroundColor Cyan
Set-Location $ABC
git pull 2>&1 | ForEach-Object { Write-Host "    $_" }
Write-Host ""

# ---------- [2/5] .env ----------
Write-Host "[2/5] .env 파일 작성..." -ForegroundColor Cyan
$envPath = Join-Path $ABC ".env"
$envContent = @"
TELEGRAM_BOT_TOKEN=8859704218:AAEkldOl6nzu9ewDzkKLbvpppxhTsubcdpc
TELEGRAM_CHAT_ID=6714828228
TIMEZONE=Asia/Seoul
"@
Set-Content -Path $envPath -Value $envContent -Encoding UTF8
Write-Host "    OK: $envPath" -ForegroundColor Green
Write-Host ""

# ---------- [3/5] Python deps ----------
Write-Host "[3/5] Python 패키지 설치 (1~2분 걸릴 수 있음)..." -ForegroundColor Cyan
$pythonExe = (Get-Command python -ErrorAction SilentlyContinue).Path
if (-not $pythonExe) {
    Write-Host "    [실패] python 명령어 인식 안 됨." -ForegroundColor Red
    Write-Host "    https://www.python.org/downloads/ 에서 설치 후 다시 시도." -ForegroundColor Red
} else {
    Write-Host "    using: $pythonExe" -ForegroundColor Gray
    & python -m pip install --upgrade pip --quiet 2>&1 | ForEach-Object { Write-Host "    $_" }
    & python -m pip install -r requirements.txt --quiet 2>&1 | ForEach-Object { Write-Host "    $_" }
    Write-Host "    OK." -ForegroundColor Green
}
Write-Host ""

# ---------- [4/5] ffmpeg ----------
Write-Host "[4/5] ffmpeg 확인 (음성 변환용)..." -ForegroundColor Cyan
$ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
if ($ffmpeg) {
    Write-Host "    OK: $($ffmpeg.Path)" -ForegroundColor Green
} else {
    Write-Host "    ffmpeg 없음. winget 으로 설치 시도..." -ForegroundColor Yellow
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($winget) {
        winget install --id=Gyan.FFmpeg -e --silent --accept-source-agreements --accept-package-agreements 2>&1 | ForEach-Object { Write-Host "    $_" }
        Write-Host "    설치 완료. PowerShell을 닫고 새로 열어야 ffmpeg가 PATH에서 잡혀." -ForegroundColor Yellow
    } else {
        Write-Host "    winget도 없네. 수동 설치: https://www.gyan.dev/ffmpeg/builds/" -ForegroundColor Yellow
        Write-Host "    (없어도 비서는 동작함. 음성 메시지가 mp3로 갈 뿐.)" -ForegroundColor Gray
    }
}
Write-Host ""

# ---------- [5/5] claude CLI ----------
Write-Host "[5/5] claude CLI 확인 (Max 구독 호출용)..." -ForegroundColor Cyan
$claude = Get-Command claude -ErrorAction SilentlyContinue
if ($claude) {
    Write-Host "    OK: $($claude.Path)" -ForegroundColor Green
    Write-Host "    아직 Max 계정 로그인 안 했으면: claude /login" -ForegroundColor Gray
} else {
    Write-Host "    [실패] claude CLI 없음." -ForegroundColor Red
    Write-Host "    https://claude.ai/code 에서 Claude Code 설치 후 'claude /login'" -ForegroundColor Red
}
Write-Host ""

# ---------- done ----------
Write-Host "===================================================" -ForegroundColor Green
Write-Host " 셋업 끝. 비서 켜려면 다음 줄 실행:" -ForegroundColor Green
Write-Host "" -ForegroundColor Green
Write-Host "   cd `$HOME\Desktop\abc" -ForegroundColor Yellow
Write-Host "   python -m src.main" -ForegroundColor Yellow
Write-Host "" -ForegroundColor Green
Write-Host " 테스트: 텔레그램에서 봇한테 /brief 보내면 AI가 만든" -ForegroundColor Green
Write-Host " 첫 모닝 브리프가 돌아옴." -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Green
Write-Host ""

$startNow = Read-Host "지금 바로 비서 켤까? (y/N)"
if ($startNow -eq "y" -or $startNow -eq "Y") {
    Write-Host ""
    Write-Host "비서 시작. 끄려면 Ctrl+C." -ForegroundColor Cyan
    Write-Host ""
    & python -m src.main
}
