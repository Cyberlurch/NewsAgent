@echo off
REM  RunNewsAgent.bat  –  double-click to launch NewsAgent in a PowerShell window
powershell -NoExit -ExecutionPolicy Bypass -Command "Set-Location 'D:\Dropbox\Eigene Dateien\AI\NewsAgent_V2'; & 'C:\Users\lurch\AppData\Local\pypoetry\Cache\virtualenvs\newsagent-kXX81KeG-py3.12\Scripts\Activate.ps1'; python -m src.newsagent.main --channels data/channels.json --threads 1 --max-chunks 12"
