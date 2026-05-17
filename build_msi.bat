@echo off
echo === Building Cadence MSI Installer ===
echo This script compiles your code into an MSI using WiX Toolset v3.14

:: Temporarily add WiX to the PATH so we can find heat, candle, and light
set "PATH=%PATH%;C:\Program Files (x86)\WiX Toolset v3.14\bin"

:: Ensure the dist/Cadence folder exists
if not exist "dist\Cadence" (
    echo ERROR: You need to run build_cadence.py first!
    pause
    exit /b 1
)

:: 1. Harvest the files in the dist\Cadence directory
echo Harvesting files...
heat dir "dist\Cadence" -cg HarvestedComponents -dr INSTALLFOLDER -scom -sreg -srd -var var.SourceDir -gg -out components.wxs
if %errorlevel% neq 0 (
    echo ERROR: Heat failed to harvest files. Is WiX installed?
    pause
    exit /b %errorlevel%
)

:: 2. Compile the WiX source files
echo Compiling...
candle -dSourceDir="dist\Cadence" cadence.wxs components.wxs -ext WixUIExtension
if %errorlevel% neq 0 (
    echo ERROR: Candle compilation failed.
    pause
    exit /b %errorlevel%
)

:: 3. Link the compiled files into an MSI
echo Linking...
light -b "dist\Cadence" -out dist\Cadence-Installer.msi cadence.wixobj components.wixobj -ext WixUIExtension -sval
if %errorlevel% neq 0 (
    echo ERROR: Light linking failed.
    pause
    exit /b %errorlevel%
)

:: Cleanup temp objects
del components.wxs
del cadence.wixobj
del components.wixobj

echo === MSI BUILD COMPLETE ===
echo Your installer is located at: dist\Cadence-Installer.msi
pause
