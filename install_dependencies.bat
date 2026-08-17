@echo off
REM ===========================================================================
REM  Sinkhole Express - Dependency Installer
REM  Installs Python packages required by the app:
REM    - sinkhole_express.pyw   (CustomTkinter UI)  -> keyring, customtkinter
REM  Tkinter itself ships with the standard Windows Python installer.
REM ===========================================================================

title Sinkhole Express - Dependency Installer

echo.
echo ============================================
echo   Sinkhole Express - Dependency Installer
echo ============================================
echo.

REM --- Check that Python is available ---
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python was not found on your PATH.
    echo         Install Python 3 from https://www.python.org/downloads/
    echo         and make sure "Add python.exe to PATH" is checked.
    echo.
    pause
    exit /b 1
)

echo Using Python:
python --version
echo.

REM --- Upgrade pip first ---
echo Upgrading pip...
python -m pip install --upgrade pip
echo.

REM --- Install required packages ---
echo Installing required packages: keyring, customtkinter ...
python -m pip install --upgrade keyring customtkinter
if errorlevel 1 (
    echo.
    echo [ERROR] Package installation failed. See messages above.
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   All dependencies installed successfully.
echo ============================================
echo.
echo You can now launch the app:
echo   - sinkhole_express.pyw    (CustomTkinter UI)
echo.
pause
