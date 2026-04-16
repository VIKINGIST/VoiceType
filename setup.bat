@echo off
echo ============================================
echo   VoiceType - Setup
echo ============================================
echo.

cd /d "%~dp0"

if not exist "venv" (
    echo [1/8] Creating venv...
    python -m venv venv
) else (
    echo [1/8] venv already exists
)

call venv\Scripts\activate.bat

echo [2/8] Upgrading pip...
python -m pip install --upgrade pip --quiet

echo [3/8] Installing PyTorch with CUDA...
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121 --quiet

echo [4/8] Installing CUDA runtime + dependencies...
pip install nvidia-cublas-cu12 nvidia-cudnn-cu12 --quiet
pip install -r requirements.txt --quiet

echo [5/8] Installing PyInstaller...
pip install pyinstaller --quiet

echo [6/8] Verifying...
echo.
python -c "import torch; print('PyTorch: ' + torch.__version__ + ', CUDA: ' + str(torch.cuda.is_available()) + ', GPU: ' + (torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A'))"
python -c "from faster_whisper import WhisperModel; print('faster-whisper: OK')"
python -c "import sounddevice; print('sounddevice: OK')"
echo.

echo [7/8] Generating icon...
python scripts\build_icon.py

echo [8/8] Building VoiceType.exe...
if not exist "logs" mkdir logs
pyinstaller --noconfirm --onedir --windowed --name VoiceType --icon voicetype.ico --add-data "voicetype;voicetype" --hidden-import voicetype --hidden-import voicetype.main --hidden-import voicetype.config --hidden-import voicetype.recorder --hidden-import voicetype.vad --hidden-import voicetype.transcriber --hidden-import voicetype.input_handler --hidden-import voicetype.notifier --hidden-import voicetype.settings_window --hidden-import keyboard --hidden-import pystray --hidden-import sounddevice --hidden-import customtkinter --hidden-import win11toast --hidden-import pythoncom --hidden-import psutil --collect-all customtkinter --collect-all sounddevice scripts\run.py

if exist "dist\VoiceType\VoiceType.exe" (
    copy /Y config.yaml dist\VoiceType\ >nul
    copy /Y voicetype.ico dist\VoiceType\ >nul
    if not exist "dist\VoiceType\logs" mkdir dist\VoiceType\logs

    echo Creating shortcut...
    python scripts\create_shortcut.py

    echo.
    echo ============================================
    echo   Build OK!
    echo   VoiceType.lnk  - shortcut in project root
    echo   Double-click it to run
    echo ============================================
) else (
    echo.
    echo Build failed. Creating start.bat as fallback...
    (
    echo @echo off
    echo cd /d "%%~dp0"
    echo call venv\Scripts\activate.bat
    echo start "" venv\Scripts\pythonw.exe -m voicetype.main
    ) > start.bat
    echo start.bat created as fallback
)

pause
