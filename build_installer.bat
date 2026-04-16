@echo off
echo ============================================
echo   VoiceType - Build Installer
echo ============================================
echo.

cd /d "%~dp0"

:: Check Inno Setup
set "ISCC="
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"

if "%ISCC%"=="" (
    echo Inno Setup 6 not found!
    echo.
    echo Download and install from:
    echo   https://jrsoftware.org/isdl.php
    echo.
    echo Then run this script again.
    pause
    exit /b 1
)

:: Check that EXE build exists
if not exist "dist\VoiceType\VoiceType.exe" (
    echo VoiceType.exe not found in dist\VoiceType\
    echo Run setup.bat first to build the EXE.
    pause
    exit /b 1
)

:: Make sure config.yaml is in dist
if not exist "dist\VoiceType\config.yaml" copy /Y config.yaml dist\VoiceType\ >nul
if not exist "dist\VoiceType\voicetype.ico" copy /Y voicetype.ico dist\VoiceType\ >nul

echo Building installer...
"%ISCC%" installer.iss

if exist "installer_output\VoiceType-Setup.exe" (
    echo.
    echo ============================================
    echo   Installer created!
    echo   installer_output\VoiceType-Setup.exe
    echo ============================================
) else (
    echo.
    echo Installer build failed!
)

pause
