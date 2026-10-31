"""
One-command launch script for Regenerative Supercapacitor Elevator Energy Manager.
Starts the FastAPI backend and serves the compiled React dashboard at http://localhost:8000.
"""

import sys
import subprocess
from pathlib import Path

def main():
    root = Path(__file__).parent.resolve()
    frontend_dir = root / "frontend"
    dist_dir = frontend_dir / "dist"

    print("=" * 70)
    print("  KONE ELEVATOR ENERGY MANAGER - PRODUCTION LAUNCHER")
    print("=" * 70)

    # Check if frontend bundle exists, build if missing
    if not dist_dir.exists():
        print("[*] Frontend distribution not found. Building Vite production bundle...")
        res = subprocess.run(["npm", "run", "build"], cwd=str(frontend_dir), shell=True)
        if res.returncode != 0:
            print("[!] Warning: npm build failed. Running API mode only.")
        else:
            print("[+] Frontend bundle compiled successfully!")
    else:
        print("[+] Frontend production bundle verified in frontend/dist/")

    print("\n[+] Starting FastAPI & Live Simulation Service...")
    print("    - Dashboard URL: http://localhost:8000")
    print("    - API Documentation: http://localhost:8000/docs")
    print("    - Live WebSocket Stream: ws://localhost:8000/ws/live")
    print("=" * 70)

    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=False)

if __name__ == "__main__":
    main()
