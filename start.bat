@echo off
rem Konzeptheft ohne Konsolenfenster starten
rem Ohne eigene .venv gilt die Umgebung des CodeCockpits (gleiche PySide6-Version)
cd /d "%~dp0"
set "PY=.venv\Scripts\pythonw.exe"
if not exist "%PY%" set "PY=..\..\..\Codecockpit\Repository\main\.venv\Scripts\pythonw.exe"
start "" "%PY%" main.py %*
