@echo off
setlocal
set "APP_DIR=%~dp0"
set "SCRIPT=%APP_DIR%baixatudo.pyw"

if exist "%LOCALAPPDATA%\Programs\Python\Launcher\pyw.exe" (
    start "" "%LOCALAPPDATA%\Programs\Python\Launcher\pyw.exe" -3 "%SCRIPT%"
    exit /b
)

where pyw.exe >nul 2>nul
if not errorlevel 1 (
    start "" pyw.exe -3 "%SCRIPT%"
    exit /b
)

where pythonw.exe >nul 2>nul
if not errorlevel 1 (
    start "" pythonw.exe "%SCRIPT%"
    exit /b
)

where py.exe >nul 2>nul
if not errorlevel 1 (
    start "" py.exe -3 "%SCRIPT%"
    exit /b
)

where python.exe >nul 2>nul
if not errorlevel 1 (
    start "" python.exe "%SCRIPT%"
    exit /b
)

for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python*") do (
    if exist "%%~fD\pythonw.exe" (
        start "" "%%~fD\pythonw.exe" "%SCRIPT%"
        exit /b
    )
)

for /d %%D in ("%ProgramFiles%\Python*") do (
    if exist "%%~fD\pythonw.exe" (
        start "" "%%~fD\pythonw.exe" "%SCRIPT%"
        exit /b
    )
)

start "" "%SCRIPT%"
