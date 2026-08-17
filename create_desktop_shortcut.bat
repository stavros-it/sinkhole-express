@echo off
REM ===========================================================================
REM  Sinkhole Express - Desktop Shortcut Installer
REM  Creates a desktop shortcut using pythonw.exe (no console)
REM  and the bundled sinkhole_express.ico icon.
REM
REM  Resolves the REAL Desktop path via Windows (handles OneDrive-redirected
REM  Desktops, where C:\Users\<name>\Desktop does not exist).
REM  Run from the folder that contains the .pyw files and the .ico.
REM ===========================================================================

title Sinkhole Express - Shortcut Installer
setlocal EnableDelayedExpansion

echo.
echo ============================================
echo   Sinkhole Express - Desktop Shortcut Setup
echo ============================================
echo.

REM --- Folder where this .bat lives ---
set "APPDIR=%~dp0"
if "%APPDIR:~-1%"=="\" set "APPDIR=%APPDIR:~0,-1%"

set "ICON=%APPDIR%\sinkhole_express.ico"
set "APP=%APPDIR%\sinkhole_express.pyw"

REM --- Locate pythonw.exe ---
set "PYW="
for /f "delims=" %%i in ('where pythonw.exe 2^>nul') do (
    if not defined PYW set "PYW=%%i"
)
if not defined PYW (
    echo [ERROR] pythonw.exe was not found on your PATH.
    echo         Install Python 3 and ensure it was added to PATH.
    echo.
    pause
    exit /b 1
)
echo Using launcher: %PYW%

REM --- Ask Windows for the real Desktop path (works with OneDrive redirect) ---
for /f "usebackq delims=" %%D in (`powershell -NoProfile -Command "[Environment]::GetFolderPath('Desktop')"`) do set "DESKTOP=%%D"

if not defined DESKTOP (
    echo [ERROR] Could not resolve your Desktop folder.
    echo.
    pause
    exit /b 1
)
echo Desktop folder: %DESKTOP%
echo.

REM --- Build shortcuts. All PowerShell is written to a temp .ps1 to avoid
REM     the caret line-continuation quoting problems. ---
set "PS1=%TEMP%\sinkhole_mkshortcut.ps1"

if exist "%APP%" (
    call :make_shortcut "Sinkhole Express" "%APP%"
) else (
    echo [skip] %APP% not found.
)

if exist "%PS1%" del "%PS1%" >nul 2>&1

echo.
echo ============================================
echo   Done. Check your Desktop for the shortcut(s).
echo ============================================
echo.
pause
exit /b 0

REM ---------------------------------------------------------------------------
REM  :make_shortcut  <ShortcutName>  <TargetPywPath>
REM ---------------------------------------------------------------------------
:make_shortcut
set "LNKNAME=%~1"
set "TARGET=%~2"
set "LNKPATH=%DESKTOP%\%LNKNAME%.lnk"
echo Creating shortcut: %LNKNAME%.lnk

REM Write a small PowerShell script (variables passed via environment).
> "%PS1%" echo $ErrorActionPreference = 'Stop'
>> "%PS1%" echo try {
>> "%PS1%" echo   $ws = New-Object -ComObject WScript.Shell
>> "%PS1%" echo   $sc = $ws.CreateShortcut($env:LNKPATH)
>> "%PS1%" echo   $sc.TargetPath = $env:PYW
>> "%PS1%" echo   $sc.Arguments = '"' + $env:TARGET + '"'
>> "%PS1%" echo   $sc.WorkingDirectory = $env:APPDIR
>> "%PS1%" echo   if (Test-Path $env:ICON) { $sc.IconLocation = $env:ICON }
>> "%PS1%" echo   $sc.Description = 'Toggle sinkhole blocking on/off'
>> "%PS1%" echo   $sc.Save()
>> "%PS1%" echo   exit 0
>> "%PS1%" echo } catch { Write-Host $_.Exception.Message; exit 1 }

set "LNKPATH=%LNKPATH%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%"

if errorlevel 1 (
    echo   [ERROR] Failed to create %LNKNAME%.lnk
) else (
    echo   [OK] %LNKNAME%.lnk created.
)
goto :eof
