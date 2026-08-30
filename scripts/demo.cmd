@echo off
REM Runs the demo from cmd.exe. Without this, typing `.\scripts\demo.ps1` at a cmd prompt
REM returns silently: cmd does not execute .ps1 files and says nothing about it, which reads
REM exactly like a script that ran and did nothing.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0demo.ps1" %*
