"""Set up missing dependencies and run the Joblee API and frontend together."""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
VENV = BACKEND / ".venv"
VENV_PYTHON = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def run_setup(command: list[str], cwd: Path) -> None:
    """Run one setup command and stop if it fails."""
    print(f"\n$ {' '.join(command)}  (in {cwd.relative_to(ROOT)})", flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def npm_command(*args: str) -> list[str]:
    if os.name == "nt":
        return ["cmd", "/c", "npm", *args]
    return ["npm", *args]


def prepare() -> None:
    if not shutil.which("node") or not shutil.which("npm"):
        raise RuntimeError(
            "Node.js and npm are required for the frontend. Install Node.js, then run `python run.py` again."
        )

    if not VENV_PYTHON.exists():
        run_setup([sys.executable, "-m", "venv", str(VENV)], ROOT)

    backend_ready = subprocess.run(
        [str(VENV_PYTHON), "-c", "import fastapi, uvicorn, google.auth, google.oauth2.id_token"],
        cwd=BACKEND,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0
    if not backend_ready:
        run_setup([str(VENV_PYTHON), "-m", "pip", "install", "-r", "requirements.txt"], BACKEND)

    if not (FRONTEND / "node_modules" / ".bin" / "vite").exists():
        run_setup(npm_command("install"), FRONTEND)


def stop(processes: list[subprocess.Popen]) -> None:
    for process in processes:
        if process.poll() is None:
            process.terminate()
    for process in processes:
        if process.poll() is None:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


def service_is_ready(url: str, marker: bytes | None = None) -> bool:
    """Check whether an existing local server can be reused."""
    try:
        with urlopen(url, timeout=1) as response:
            body = response.read(4096)
            return response.status == 200 and (marker is None or marker in body)
    except (OSError, URLError):
        return False


def find_frontend() -> tuple[int, bool]:
    """Reuse Joblee or choose the first free Vite development port."""
    candidate_ports = range(5173, 5200)
    for port in candidate_ports:
        if service_is_ready(f"http://127.0.0.1:{port}/", b"<title>Joblee</title>"):
            return port, True
    for port in candidate_ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            try:
                listener.bind(("127.0.0.1", port))
                return port, False
            except OSError:
                continue
    raise RuntimeError("No available frontend port found between 5173 and 5199")


def main() -> int:
    try:
        prepare()
    except (RuntimeError, subprocess.CalledProcessError) as error:
        print(f"\nSetup failed: {error}", file=sys.stderr)
        return 1

    processes: list[subprocess.Popen] = []
    try:
        print("\nStarting Joblee…", flush=True)
        frontend_port, frontend_reused = find_frontend()
        if service_is_ready("http://127.0.0.1:8000/api/v1/health", b'"status":"ok"'):
            print("API already running; reusing it.", flush=True)
        else:
            processes.append(subprocess.Popen(
                [str(VENV_PYTHON), "-m", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"],
                cwd=BACKEND,
            ))
        if frontend_reused:
            print(f"Frontend already running on port {frontend_port}; reusing it.", flush=True)
        else:
            frontend_env = {**os.environ, "JOBLEE_FRONTEND_PORT": str(frontend_port)}
            processes.append(subprocess.Popen(
                npm_command("run", "dev", "--", "--host", "127.0.0.1", "--strictPort"),
                cwd=FRONTEND,
                env=frontend_env,
            ))
        print("\nAPI:      http://127.0.0.1:8000/docs", flush=True)
        print(f"Frontend: http://127.0.0.1:{frontend_port}", flush=True)
        if frontend_port != 5173:
            print(f"Google sign-in: add http://localhost:{frontend_port} and http://127.0.0.1:{frontend_port} as authorized JavaScript origins in Google Cloud.", flush=True)
        print("Press Ctrl+C to stop both servers.\n", flush=True)

        if not processes:
            return 0

        while True:
            for process in processes:
                code = process.poll()
                if code is not None:
                    return code or 0
            time.sleep(0.4)
    except KeyboardInterrupt:
        print("\nStopping Joblee…", flush=True)
        return 0
    except RuntimeError as error:
        print(f"\nStartup failed: {error}", file=sys.stderr)
        return 1
    finally:
        stop(processes)


if __name__ == "__main__":
    raise SystemExit(main())
