@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

set "TARGET_DIR=%~dp0"

echo ========================================
echo 生成设备端凭据
echo 输出目录: %TARGET_DIR%
echo ========================================

for /f %%i in ('powershell -Command "Get-Random -Minimum 1 -Maximum 4294967296"') do set ID=%%i
echo !ID!>"%TARGET_DIR%id"
echo [OK] id = !ID!

powershell -Command "$bytes = New-Object byte[] 16; [System.Security.Cryptography.RandomNumberGenerator]::Fill($bytes); ($bytes | ForEach-Object { $_.ToString('X2') }) -join ''" > "%temp%\sm4_device_master_key.tmp"
set /p MASTER_KEY=<"%temp%\sm4_device_master_key.tmp"
del "%temp%\sm4_device_master_key.tmp"

echo !MASTER_KEY!>"%TARGET_DIR%master_key"
echo [OK] master_key = !MASTER_KEY!

echo ========================================
echo 已写入:
echo %TARGET_DIR%id
echo %TARGET_DIR%master_key
echo ========================================
endlocal
pause
