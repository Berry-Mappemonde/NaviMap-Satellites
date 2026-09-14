"""Campagne multi-baies : expédition, puis route, puis le reste (plus tard)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import yaml

from navimap_satellites.aoi import AOI, iter_aoi_files, load_aoi


@dataclass(frozen=True)
class Campaign:
    """Liste ordonnée de baies, une à la fois."""

    id: str
    name: str
    notes: str
    stages: tuple[AOI, ...]
    paths: tuple[Path, ...]

    def filter_phase(self, phase: str | None) -> Campaign:
        if not phase:
            return self
        pairs = [(a, p) for a, p in zip(self.stages, self.paths, strict=True) if a.phase == phase]
        stages = tuple(a for a, _ in pairs)
        paths = tuple(p for _, p in pairs)
        return replace(self, stages=stages, paths=paths)


def load_campaign(path: str | Path) -> Campaign:
    """Charge un manifeste YAML, ou tous les AOI d'un dossier."""
    target = Path(path)
    if target.is_file():
        return _from_manifest(target)
    if not target.is_dir():
        raise FileNotFoundError(f"Campagne introuvable : {path}")
    manifest = target / "manifest.yaml"
    if manifest.is_file():
        return _from_manifest(manifest)
    files = iter_aoi_files(target)
    if not files:
        raise ValueError(f"Aucun AOI YAML dans {target}")
    aois = tuple(load_aoi(p) for p in files)
    order = sorted(range(len(aois)), key=lambda i: (aois[i].order, aois[i].id))
    return Campaign(
        id=target.name,
        name=target.name,
        notes="",
        stages=tuple(aois[i] for i in order),
        paths=tuple(files[i] for i in order),
    )


def _from_manifest(path: Path) -> Campaign:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Manifeste invalide : {path}")
    root = path.parent
    campaign_id = str(raw.get("id") or path.parent.name)
    notes = str(raw.get("notes") or "").strip()
    rows = raw.get("stages")
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"Manifeste sans stages : {path}")
    stages: list[AOI] = []
    paths: list[Path] = []
    for i, row in enumerate(rows):
        aoi, aoi_path = _stage_from_row(row, root, campaign_id, i)
        stages.append(aoi)
        paths.append(aoi_path)
    order = sorted(range(len(stages)), key=lambda i: (stages[i].order, stages[i].id))
    return Campaign(
        id=campaign_id,
        name=str(raw.get("name") or campaign_id),
        notes=notes,
        stages=tuple(stages[i] for i in order),
        paths=tuple(paths[i] for i in order),
    )


def _stage_from_row(row: Any, root: Path, campaign_id: str, index: int) -> tuple[AOI, Path]:
    if isinstance(row, str):
        aoi_path = (root / row).resolve()
        aoi = load_aoi(aoi_path)
        if not aoi.campaign:
            aoi = replace(aoi, campaign=campaign_id)
        if aoi.order == 0:
            aoi = replace(aoi, order=(index + 1) * 10)
        return aoi, aoi_path
    if not isinstance(row, dict) or "path" not in row:
        raise ValueError("Chaque stage doit être un chemin ou {path, phase, order}")
    aoi_path = (root / str(row["path"])).resolve()
    aoi = load_aoi(aoi_path)
    aoi = replace(
        aoi,
        campaign=str(row.get("campaign") or aoi.campaign or campaign_id),
        phase=str(row.get("phase") or aoi.phase),
        order=int(row["order"]) if row.get("order") is not None else (aoi.order or (index + 1) * 10),
    )
    aoi.validate()
    return aoi, aoi_path
