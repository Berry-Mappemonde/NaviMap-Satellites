"""Charge CDSE_* depuis des .env gitignorés. N'imprime jamais le mot de passe."""

from __future__ import annotations

import os
from pathlib import Path


def _candidate_env_files() -> list[Path]:
    extra = os.environ.get("NAVIMAP_CDSE_ENV", "").strip()
    home = Path.home()
    paths = [
        Path.cwd() / ".env",
        Path(extra) if extra else None,
        home / "NaviMap-Satellites" / ".env",
        home / "navimap-satellites" / ".env",
        Path("/Users/clement/Blue-Intelligence-Map/scripts/satellite/.env"),
        home / "Blue-Intelligence-Map" / "scripts" / "satellite" / ".env",
    ]
    out: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        if path is None:
            continue
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        out.append(path)
    return out


def _parse_env_line(line: str) -> tuple[str, str] | None:
    raw = line.strip()
    if not raw or raw.startswith("#") or "=" not in raw:
        return None
    key, value = raw.split("=", 1)
    key = key.strip()
    value = value.strip()
    if (value.startswith("'") and value.endswith("'")) or (
        value.startswith('"') and value.endswith('"')
    ):
        value = value[1:-1]
    return key, value


def load_cdse_env() -> list[str]:
    """Remplit os.environ sans écraser une variable déjà définie.

    Retourne les chemins lus (pour un message « fichier trouvé », jamais le secret).
    """
    loaded: list[str] = []
    for path in _candidate_env_files():
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for line in text.splitlines():
            parsed = _parse_env_line(line)
            if not parsed:
                continue
            key, value = parsed
            if key.startswith(("CDSE_", "COPERNICUS_", "EARTHDATA_")):
                os.environ.setdefault(key, value)
        loaded.append(str(path))
    return loaded
