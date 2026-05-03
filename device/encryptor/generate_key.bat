@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

set "TARGET_DIR=%~dp0"
if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%" 2>nul

echo ========================================
echo output_dir: %TARGET_DIR%
echo ========================================

for /f %%i in ('powershell -Command "Get-Random -Minimum 1 -Maximum 4294967296"') do set ID=%%i
echo !ID!>"%TARGET_DIR%id"
echo id = !ID!

powershell -Command "$bytes = New-Object byte[] 16; (New-Object System.Security.Cryptography.RNGCryptoServiceProvider).GetBytes($bytes); $hex = -join ($bytes | ForEach-Object { $_.ToString('X2') }); Write-Output $hex" > "%temp%\sm4_device_master_key.tmp"
set /p MASTER_KEY=<"%temp%\sm4_device_master_key.tmp"
del "%temp%\sm4_device_master_key.tmp"

echo !MASTER_KEY!>"%TARGET_DIR%master_key"
echo master_key = !MASTER_KEY!

echo ========================================
echo %TARGET_DIR%id
echo %TARGET_DIR%master_key
echo ========================================
endlocal
pause
