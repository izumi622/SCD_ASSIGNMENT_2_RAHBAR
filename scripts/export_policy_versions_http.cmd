@echo off
setlocal
cd /d "%~dp0.."
if not exist "C:\msys64\ucrt64\bin\python.exe" (
  echo Python not found at the previously verified MSYS2 location.
  exit /b 1
)
"C:\msys64\ucrt64\bin\python.exe" scripts\export_policy_versions_http.py --base http://127.0.0.1:8001 --out-dir eval
exit /b %errorlevel%
