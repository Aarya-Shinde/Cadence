import os
import sys
import subprocess
import shutil
from pathlib import Path

# Paths
PROJECT_ROOT = Path(os.path.abspath("."))
SRC_DIR = PROJECT_ROOT / "src"
ASSETS_DIR = SRC_DIR / "assets"
BIN_DIR = PROJECT_ROOT / "libraries bin"

def convert_icon():
    """Convert PNG icon to ICO format if needed."""
    png_path = ASSETS_DIR / "desktop icon.png"
    ico_path = ASSETS_DIR / "icon.ico"
    
    if ico_path.exists():
        print("[OK] ICO file already exists.")
        return str(ico_path)
        
    if not png_path.exists():
        print("[WARNING] No desktop icon.png found. Using default icon.")
        return None
        
    print("Converting PNG to ICO...")
    try:
        from PIL import Image
        img = Image.open(png_path)
        img.save(ico_path, format="ICO", sizes=[(256, 256)])
        print("[OK] Successfully created icon.ico")
        return str(ico_path)
    except ImportError:
        print("[WARNING] Pillow library not found. Could not convert PNG to ICO.")
        print("Run: pip install Pillow")
        return None
    except Exception as e:
        print(f"[WARNING] Failed to convert icon: {e}")
        return None

def build():
    """Run PyInstaller with correct configurations."""
    print("=== Building Cadence Desktop App ===")
    
    # Check if PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # 1. Prepare Icon
    icon_file = convert_icon()
    
    # 2. Prepare PyInstaller Command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=Cadence",
        "--windowed", # Hides the console/terminal
        "--noconfirm", # Overwrite output directory
        "--clean",
    ]
    
    if icon_file:
        cmd.append(f"--icon={icon_file}")
        
    # Add Data (Assets, SVGs, etc.)
    # Windows uses ';' to separate source;destination
    cmd.append(f"--add-data={SRC_DIR}/assets;assets")
    
    # Add Binaries (FFmpeg)
    if (BIN_DIR / "ffmpeg.exe").exists():
        cmd.append(f"--add-binary={BIN_DIR}/ffmpeg.exe;bin")
        print("[OK] Included ffmpeg.exe")
    else:
        print("[WARNING] ffmpeg.exe not found in 'libraries bin'.")
        
    if (BIN_DIR / "ffprobe.exe").exists():
        cmd.append(f"--add-binary={BIN_DIR}/ffprobe.exe;bin")
        print("[OK] Included ffprobe.exe")
        
    # Main script
    cmd.append(str(SRC_DIR / "main.py"))
    
    # 3. Execute
    print("\nRunning PyInstaller (This may take a minute or two)...")
    subprocess.run(cmd, check=True)
    
    print("\n=== BUILD COMPLETE ===")
    print(r"Your executable is located in: \dist\Cadence\Cadence.exe")
    print("Note: To share it, ZIP the entire 'Cadence' folder inside 'dist'.")

if __name__ == "__main__":
    build()
