@echo off
setlocal
cd /d "%~dp0backend"

rem Find a REAL Python. The Windows "python" shortcut that opens the Microsoft Store does not count.
set "PY="
py -3 --version >nul 2>nul
if not errorlevel 1 set "PY=py -3"
if not defined PY (
  python --version >nul 2>nul
  if not errorlevel 1 set "PY=python"
)
if not defined PY goto nopython
%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if errorlevel 1 goto oldpython

if not exist ".venv\Scripts\python.exe" (
  echo Creating a private Python environment, one time only...
  %PY% -m venv .venv
  if errorlevel 1 goto venvfail
)
call ".venv\Scripts\activate.bat"
echo Installing dependencies. The first run takes a few minutes...
python -m pip install -r requirements.txt
if errorlevel 1 goto pipfail
echo.
echo Taxon is starting. Your browser will open http://localhost:8000
echo Keep this window open while you use Taxon. Press Ctrl+C to stop it.
start "" /b cmd /c "timeout /t 6 >nul & start http://localhost:8000"
python -m uvicorn app.main:app --port 8000
pause
exit /b 0

:nopython
echo.
echo Python is not installed. Windows only has a placeholder that opens the Microsoft Store.
echo   1. Download Python from https://www.python.org/downloads/ , version 3.12 or newer.
echo   2. Run the installer. On the FIRST screen tick "Add python.exe to PATH", then click Install Now.
echo   3. Close this window and double-click start-taxon.bat again.
pause
exit /b 1

:oldpython
echo Your Python is older than 3.10. Install Python 3.12 or newer from https://www.python.org/downloads/ and run this file again.
pause
exit /b 1

:venvfail
echo Could not create the Python environment.
pause
exit /b 1

:pipfail
echo Installing dependencies failed. Check your internet connection and try again.
pause
exit /b 1
