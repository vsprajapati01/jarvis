@echo off
REM Build Jarvis.exe on Windows. Run this in the jarvis folder.
REM Needs Python 3.11 and pip. First run: pip install -r requirements.txt
pip install pyinstaller
pyinstaller --onefile --windowed --name Jarvis --icon logo.ico --add-data "logo.png;." --add-data "config.json;." jarvis_gui.py
echo.
echo Done. Your exe is at: dist\Jarvis.exe
echo Double-click dist\Jarvis.exe to run it.
pause
