"""Start the whole app with one command (API on :8000, web on :5173). Ctrl+C stops both.

uv run python scripts/dev.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    npm = shutil.which("npm")
    if npm is None:
        sys.exit("npm not found - install Node.js 20+")
    if not (ROOT / "web" / "node_modules").exists():
        subprocess.run([npm, "install"], cwd=ROOT / "web", check=True)

    # Without this, a GEMINI_API_KEY in .env is ignored and explanations silently use the mock.
    env_file = ["--env-file", ".env"] if (ROOT / ".env").exists() else []
    api = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "dnb.server.app:app",
            "--reload",
            "--reload-dir",
            "dnb",
            "--port",
            "8000",
            *env_file,
        ],
        cwd=ROOT,
    )
    web = subprocess.Popen([npm, "run", "dev"], cwd=ROOT / "web")
    print("\n  App:  http://localhost:5173\n  API:  http://localhost:8000/docs\n")
    try:
        api.wait()
        web.wait()
    except KeyboardInterrupt:
        pass
    finally:
        for p in (api, web):
            p.terminate()


if __name__ == "__main__":
    main()
