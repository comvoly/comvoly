param(
    [string]$PublicApiUrl = "https://clever-miracle-v2-development.up.railway.app"
)

$ErrorActionPreference = "Stop"
$python = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
$admin = Join-Path $PSScriptRoot "..\src\telegram_bot_admin.py"

if (-not (Test-Path -LiteralPath $python)) {
    throw "The Comvoly backend virtual environment was not found at $python."
}

$tokenSecure = Read-Host "Paste the BotFather token (input is hidden)" -AsSecureString
$masterSecure = Read-Host "Paste the Railway COMVOLY_TELEGRAM_WEBHOOK_MASTER_KEY (input is hidden)" -AsSecureString

try {
    $env:COMVOLY_TELEGRAM_BOT_TOKEN = [System.Net.NetworkCredential]::new("", $tokenSecure).Password
    $env:COMVOLY_TELEGRAM_WEBHOOK_MASTER_KEY = [System.Net.NetworkCredential]::new("", $masterSecure).Password
    $env:COMVOLY_PUBLIC_API_URL = $PublicApiUrl
    & $python $admin register
    if ($LASTEXITCODE -ne 0) { throw "Telegram webhook registration failed." }
}
finally {
    Remove-Item Env:COMVOLY_TELEGRAM_BOT_TOKEN -ErrorAction SilentlyContinue
    Remove-Item Env:COMVOLY_TELEGRAM_WEBHOOK_MASTER_KEY -ErrorAction SilentlyContinue
    Remove-Item Env:COMVOLY_PUBLIC_API_URL -ErrorAction SilentlyContinue
    $tokenSecure = $null
    $masterSecure = $null
}
