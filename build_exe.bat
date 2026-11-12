@echo off
echo ============================================================
echo   Building Avanture Automation Standalone EXE Setup
echo ============================================================
echo.

python -m PyInstaller --noconfirm --clean AvantureAutomation.spec

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Packaging clean folder into portable archive...
    powershell -Command "Compress-Archive -Path 'dist\AvantureAutomation\*' -DestinationPath 'AvantureAutomation_Setup.zip' -Force"

    echo.
    echo Compiling single-file AvantureSetup.exe...
    "C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe" /target:winexe /optimize+ /out:AvantureSetup.exe /resource:AvantureAutomation_Setup.zip,payload.zip /reference:System.dll,System.Windows.Forms.dll,System.Drawing.dll,System.IO.Compression.dll,System.IO.Compression.FileSystem.dll installer_src\Setup.cs >nul 2>&1

    echo.
    echo ============================================================
    echo   BUILD SUCCESSFUL!
    echo   1. Single Setup EXE:  AvantureSetup.exe (Send this 1 file!)
    echo   2. Portable Folder:   dist\AvantureAutomation\
    echo   3. Portable Zip:      AvantureAutomation_Setup.zip
    echo ============================================================
) else (
    echo.
    echo [ERROR] Build failed. Please check the logs above.
)
pause
