"""One command to run vigil in development: the Python API + the React frontend.

    python dev.py

Starts:
  • the FastAPI backend  via  `uv run vigil serve`   (http://127.0.0.1:8000)
  • the Vite dev server  via  `npm run dev`           (http://127.0.0.1:5173)

Open the frontend URL. Vite proxies /api to the backend, so there's no CORS to
configure. Ctrl+C stops both. First run installs the frontend deps automatically.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "frontend"
IS_WIN = os.name == "nt"
NPM = "npm.cmd" if IS_WIN else "npm"
NEW_GROUP = subprocess.CREATE_NEW_PROCESS_GROUP if IS_WIN else 0  # type: ignore[attr-defined]

procs: list[tuple[str, subprocess.Popen]] = []


def spawn(name: str, args: list[str], cwd: Path) -> subprocess.Popen:
    p = subprocess.Popen(
        args, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1, creationflags=NEW_GROUP,
    )
    procs.append((name, p))

    def pump() -> None:
        assert p.stdout is not None
        for line in p.stdout:
            sys.stdout.write(f"[{name}] {line}")
            sys.stdout.flush()

    threading.Thread(target=pump, daemon=True).start()
    return p


def kill(p: subprocess.Popen) -> None:
    """Kill a process and its children (vite/node spawn grandchildren)."""
    if p.poll() is not None:
        return
    if IS_WIN:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
    else:
        p.terminate()


def shutdown() -> None:
    print("\n[dev] shutting down…")
    for _, p in procs:
        kill(p)
    for _, p in procs:
        try:
            p.wait(timeout=5)
        except Exception:
            p.kill()


def main() -> None:
    if not (FRONTEND / "node_modules").is_dir():
        print("[dev] installing frontend dependencies (first run)…")
        subprocess.run([NPM, "install"], cwd=str(FRONTEND), check=True)

    spawn("api", ["uv", "run", "vigil", "serve"], ROOT)
    spawn("web", [NPM, "run", "dev"], FRONTEND)

    print(
        "\n  vigil dev\n"
        "  ─────────\n"
        "  API      → http://127.0.0.1:8000\n"
        "  Frontend → http://127.0.0.1:5173   ← open this\n"
        "  Ctrl+C to stop both.\n"
    )

    try:
        while True:
            for name, p in procs:
                if p.poll() is not None:
                    print(f"[dev] '{name}' exited with code {p.returncode}; stopping.")
                    return
            time.sleep(0.4)
    except KeyboardInterrupt:
        pass
    finally:
        shutdown()


if __name__ == "__main__":
    main()
