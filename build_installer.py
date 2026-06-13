import os
import subprocess
import sys

def main():
    print("Building SreeBase CLI Installer...")
    
    # We compile the SreeBase Interactive REPL Client into a single standalone binary.
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", "sreebase-cli",
        "sreebase/client/cli.py"
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print("\n✅ Build complete. Check the 'dist' folder for the executable.")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Build failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
