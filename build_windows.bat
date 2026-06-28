@echo off
title Bild-Pro EXE erstellen
echo Erstelle Windows-EXE...
echo.
pip install -r requirements.txt
pyinstaller --noconfirm --windowed --name "Bild-Pro" --add-data "config;config" main.py
echo.
echo Fertig. Die EXE liegt in dist\Bild-Pro\Bild-Pro.exe
pause
