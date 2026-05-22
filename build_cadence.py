import os
import sys
import subprocess
import shutil
import hashlib
import zipfile
from pathlib import Path

# Paths
PROJECT_ROOT = Path(os.path.abspath("."))
SRC_DIR = PROJECT_ROOT / "src"
ASSETS_DIR = SRC_DIR / "assets"
BIN_DIR = PROJECT_ROOT / "libraries bin"
DIST_DIR = PROJECT_ROOT / "dist"

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


def package():
    """Zip dist/Cadence → Cadence.zip and generate a matching SHA-256 checksum file.

    The resulting files are placed in dist/ alongside the Cadence folder:
        dist/Cadence.zip
        dist/Cadence.zip.sha256   ← upload both of these to your GitHub Release

    The updater will automatically fetch and verify the checksum on the user's
    machine before installing, so never skip this step.
    """
    cadence_dir = DIST_DIR / "Cadence"
    zip_path    = DIST_DIR / "Cadence.zip"
    sha_path    = DIST_DIR / "Cadence.zip.sha256"

    if not cadence_dir.exists():
        print("[ERROR] dist/Cadence folder not found — run build first.")
        return

    # ---- 1. Create the zip ---------------------------------------------------
    print(f"\nZipping {cadence_dir} -> {zip_path} ...")
    if zip_path.exists():
        zip_path.unlink()

    sha256 = hashlib.sha256()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for file in sorted(cadence_dir.rglob("*")):
            if file.is_file():
                arcname = "Cadence/" + file.relative_to(cadence_dir).as_posix()
                zf.write(file, arcname)

    print(f"[OK] Created {zip_path.name}  ({zip_path.stat().st_size / 1_048_576:.1f} MB)")

    # ---- 2. Generate SHA-256 checksum ----------------------------------------
    print("Computing SHA-256 checksum...")
    sha256 = hashlib.sha256()
    with open(zip_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    digest = sha256.hexdigest().lower()

    sha_path.write_text(f"{digest}  Cadence.zip\n", encoding="utf-8")
    print(f"[OK] Checksum file written: {sha_path.name}")
    print(f"     SHA-256: {digest}")

    # ---- 3. Summary ----------------------------------------------------------
    print("\n=== RELEASE PACKAGE READY ===")
    print(f"  Upload to GitHub Release:")
    print(f"    {zip_path}")
    print(f"    {sha_path}")
    print("\n  Both files must be attached to the release for checksum verification to work.")


def build():
    """Run PyInstaller with correct configurations, then package for release."""
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
        print("[WARNING] ffmpeg.exe not found in 'libraries bin'. Downloads will NOT work!")
        
    if (BIN_DIR / "ffprobe.exe").exists():
        cmd.append(f"--add-binary={BIN_DIR}/ffprobe.exe;bin")
        print("[OK] Included ffprobe.exe")
    else:
        print("[WARNING] ffprobe.exe not found in 'libraries bin'.")
        
    # Main script
    cmd.append(str(SRC_DIR / "main.py"))
    
    # 3. Execute PyInstaller
    print("\nRunning PyInstaller (This may take a minute or two)...")
    subprocess.run(cmd, check=True)
    
    print("\n=== BUILD COMPLETE ===")
    print(r"Executable: dist\Cadence\Cadence.exe")

    # 4. Package into a release-ready zip with checksum
    package()


if __name__ == "__main__":
    build()
