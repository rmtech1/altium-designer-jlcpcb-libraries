@echo off
rem Double-click to update the JLCPCB database now.
cd /d "%~dp0.."
python -m jlc_altium update %*
pause
