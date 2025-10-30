@echo off
REM slap this on windows: install pyinstaller first (python -m pip install pyinstaller)
pyinstaller --noconfirm --onefile --windowed --add-data "assets;assets" --add-data "config.json;." main.py
