"""Wrapper autour d'adb.exe : détection, liste des appareils, push.

Nomme volontairement autrement que 'adb.py' : sur Windows, shutil.which('adb')
verifie toujours le dossier courant en premier, et PATHEXT contient '.PY' (via
le lanceur Python) - un fichier local 'adb.py' serait donc trouve et execute
a la place du vrai adb.exe, provoquant un WinError 193.
"""

import os
import shutil
import subprocess
from pathlib import Path


def find_adb() -> str | None:
    found = shutil.which("adb")
    if found:
        return found
    fallback = Path(os.environ.get("LOCALAPPDATA", "")) / "Android/Sdk/platform-tools/adb.exe"
    return str(fallback) if fallback.exists() else None


def list_devices(adb_path: str) -> list[tuple[str, str]]:
    """Retourne [(serial, state), ...] à partir de `adb devices -l`."""
    result = subprocess.run(
        [adb_path, "devices", "-l"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    devices = []
    for line in result.stdout.splitlines()[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 2:
            devices.append((parts[0], parts[1]))
    return devices


def push(adb_path: str, serial: str, local_path: str, device_dest: str, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(
        [adb_path, "-s", serial, "push", local_path, device_dest],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
