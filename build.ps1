# F1 2022 Pit Wall — Build Script (PowerShell)
# This script compiles the project into a standalone .EXE file.

echo "Cleaning up old build artifacts..."
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }

echo "Installing/Checking PyInstaller..."
pip install pyinstaller

echo "Starting compilation (this may take a few minutes)..."

# Note: We include assets, config.json, and the database.
# We use --collect-all for dash and related packages to ensure all JS/CSS components are included.
pyinstaller --name "F1_PitWall" `
            --onefile `
            --windowed `
            --add-data "assets;assets" `
            --add-data "config.json;." `
            --add-data "telemetry.db;." `
            --collect-all dash `
            --collect-all plotly `
            --icon "assets/favicon.ico" `
            app.py

echo "Build complete! Your executable is in the 'dist' folder."
echo "File: dist/F1_PitWall.exe"
