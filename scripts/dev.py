"""Start the whole app with one command. Ctrl+C stops everything.

uv run python scripts/dev.py          # development: API on :8000 (auto-reload), web on :5173
uv run python scripts/dev.py --demo   # presentation: builds the web app, serves all on :8000
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"


def wait_until_up(url: str, timeout: float = 30.0) -> bool:
    """Poll `url` until it answers, so the browser doesn't open on a "can't connect" page."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except OSError:
            time.sleep(0.3)
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--demo",
        action="store_true",
        help="build the web app once and serve it from the API on one port, no auto-reload",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="port for --demo (dev mode always uses 8000, the Vite proxy expects it)",
    )
    parser.add_argument("--no-browser", action="store_true", help="don't open a browser tab")
    args = parser.parse_args()

    npm = shutil.which("npm")
    if npm is None:
        sys.exit("npm not found - install Node.js 20+")
    if not (WEB / "node_modules").exists():
        subprocess.run([npm, "install"], cwd=WEB, check=True)

    # Without this, a GEMINI_API_KEY in .env is ignored and explanations silently use the mock.
    env_file = ["--env-file", ".env"] if (ROOT / ".env").exists() else []
    port = args.port if args.demo else 8000
    uvicorn = [sys.executable, "-m", "uvicorn", "dnb.server.app:app", "--port", str(port)]

    if args.demo:
        subprocess.run([npm, "run", "build"], cwd=WEB, check=True)
        env = os.environ | {"DNB_SERVE_WEB": "1"}
        procs = [subprocess.Popen([*uvicorn, *env_file], cwd=ROOT, env=env)]
        url = f"http://localhost:{port}"
        print(f"\n  Demo: {url}\n  API:  {url}/docs\n")
    else:
        procs = [
            subprocess.Popen([*uvicorn, "--reload", "--reload-dir", "dnb", *env_file], cwd=ROOT),
            subprocess.Popen([npm, "run", "dev"], cwd=WEB),
        ]
        url = "http://localhost:5173"
        print(f"\n  App:  {url}\n  API:  http://localhost:{port}/docs\n")

    if not args.no_browser and wait_until_up(url):
        webbrowser.open(url)
    try:
        for p in procs:
            p.wait()
    except KeyboardInterrupt:
        pass
    finally:
        for p in procs:
            p.terminate()


if __name__ == "__main__":
    main()
