@echo off
title Bild-Pro Installation
echo Installiere benoetigte Python-Pakete...
echo.
python -m pip install --upgrade pip
pip install -r requirements.txt
echo.
echo Fertig. Jetzt start_windows.bat doppelklicken.
pause
