"""Lancer ACOLITE en CLI (pas la GUI) sur une fenêtre d'AOI."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from navimap_satellites.aoi import AOI

L2W_PARAMETERS = (
    "rhos_443,rhos_492,rhos_560,rhos_665,rhos_704,rhos_833,rhos_1610,rhos_1614,rhos_2202"
)


class AcoliteError(RuntimeError):
    """ACOLITE introuvable, ou traitement en échec."""


def acolite_command() -> list[str]:
    """Chemin d'exécution : ACOLITE_LAUNCH, ACOLITE_DIR ou ACOLITE_BIN."""
    launch = os.environ.get("ACOLITE_LAUNCH", "").strip()
    if launch:
        return [sys.executable, launch] if launch.endswith(".py") else [launch]
    directory = os.environ.get("ACOLITE_DIR", "").strip()
    if directory:
        script = Path(directory) / "launch_acolite.py"
        if script.is_file():
            return [sys.executable, str(script)]
        raise AcoliteError(f"launch_acolite.py introuvable dans ACOLITE_DIR={directory}")
    binary = os.environ.get("ACOLITE_BIN", "").strip()
    if binary:
        return [binary]
    raise AcoliteError(
        "ACOLITE introuvable. Clonez https://github.com/acolite/acolite "
        "puis définissez ACOLITE_DIR (dossier du clone) ou ACOLITE_LAUNCH."
    )


def write_settings(
    path: str | Path,
    *,
    inputfile: str | Path,
    output: str | Path,
    aoi: AOI,
    extra: dict[str, str] | None = None,
) -> Path:
    """Fichier settings minimal : ACOLITE complète le reste avec ses défauts."""
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"inputfile={Path(inputfile).resolve()}",
        f"output={Path(output).resolve()}",
        f"limit={aoi.acolite_limit()}",
        "s2_target_res=10",
        f"l2w_parameters={L2W_PARAMETERS}",
        "rgb_rhot=False",
        "rgb_rhos=False",
        "l2w_export_geotiff=False",
        "map=False",
    ]
    if extra:
        lines.extend(f"{key}={value}" for key, value in extra.items())
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return dest


def run_acolite(
    settings_path: str | Path,
    *,
    command: list[str] | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> subprocess.CompletedProcess[str]:
    """`acolite --cli --settings=...`. `runner` permet de tester sans binaire."""
    cmd = list(command or acolite_command())
    cmd.extend(["--cli", f"--settings={Path(settings_path).resolve()}"])
    execute = runner or subprocess.run
    result = execute(cmd, check=False, text=True, capture_output=True)
    if getattr(result, "returncode", 1) != 0:
        err = (getattr(result, "stderr", None) or getattr(result, "stdout", None) or "").strip()
        raise AcoliteError(f"ACOLITE a échoué : {err or result.returncode}")
    return result


def find_l2w(output_dir: str | Path) -> Path:
    """Premier NetCDF L2W dans le dossier de sortie ACOLITE."""
    root = Path(output_dir)
    candidates = sorted(root.glob("*L2W*.nc")) + sorted(root.glob("*l2w*.nc"))
    # glob est insensible selon le FS ; dédoublonner.
    unique: list[Path] = []
    seen: set[Path] = set()
    for path in candidates:
        resolved = path.resolve()
        if resolved not in seen and path.is_file():
            seen.add(resolved)
            unique.append(path)
    if not unique:
        raise AcoliteError(f"Aucun fichier L2W.nc dans {root}. ACOLITE a-t-il fini ?")
    return unique[0]
