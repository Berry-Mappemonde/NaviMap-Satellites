"""Télécharge un zip L1C via OData CDSE. Refuse MSIL2A. Mac seulement."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import httpx

from navimap_satellites.acquire.auth import fetch_cdse_token
from navimap_satellites.acquire.l1c import product_name, require_l1c

CATALOGUE = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
DOWNLOAD = "https://download.dataspace.copernicus.eu/odata/v1/Products"


def default_pilot_dir() -> Path:
    return Path.home() / "Desktop" / "sentinel-pilot"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def lookup_product(token: str, scene_id: str, *, client: httpx.Client | None = None) -> dict[str, Any]:
    require_l1c(scene_id)
    name = product_name(scene_id)
    own = client is None
    http = client or httpx.Client(timeout=60.0)
    try:
        response = http.get(
            CATALOGUE,
            params={"$filter": f"Name eq '{name}'"},
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        )
        response.raise_for_status()
        items = (response.json() or {}).get("value") or []
    finally:
        if own:
            http.close()
    if not items:
        raise RuntimeError(f"produit introuvable dans le catalogue : {name}")
    item = items[0]
    pid = item.get("Id")
    if not pid:
        raise RuntimeError(f"produit sans Id : {name}")
    return {"id": pid, "name": item.get("Name") or name, "size": item.get("ContentLength")}


def download_product(token: str, product_id: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    url = f"{DOWNLOAD}({product_id})/$value"
    with httpx.stream(
        "GET",
        url,
        headers={"Authorization": f"Bearer {token}"},
        timeout=600.0,
        follow_redirects=True,
    ) as response:
        response.raise_for_status()
        with tmp.open("wb") as out:
            for chunk in response.iter_bytes(1024 * 1024):
                out.write(chunk)
    tmp.replace(dest)


def download_l1c_scene(
    scene_id: str,
    dest_dir: Path | None = None,
    *,
    dry_run: bool = False,
    token: str | None = None,
) -> dict[str, Any]:
    """Télécharge une scène. Si le zip est déjà là, ne le retélécharge pas."""
    require_l1c(scene_id)
    out_dir = dest_dir or default_pilot_dir()
    tok = token or fetch_cdse_token()
    meta = lookup_product(tok, scene_id)
    zip_name = str(meta["name"]).replace(".SAFE", ".zip")
    dest = Path(out_dir) / zip_name
    rec: dict[str, Any] = {
        "scene_id": scene_id,
        "product_id": meta["id"],
        "name": meta["name"],
        "bytes": meta["size"],
        "path": str(dest),
        "skipped_existing": False,
        "dry_run": dry_run,
    }
    if dry_run:
        return rec
    if dest.exists() and dest.stat().st_size > 0:
        rec["skipped_existing"] = True
    else:
        download_product(tok, meta["id"], dest)
    rec["sha256"] = sha256_file(dest)
    rec["bytes_on_disk"] = dest.stat().st_size
    receipt = Path(out_dir) / "download_receipt.json"
    receipt.write_text(json.dumps({"scenes": [rec]}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    rec["receipt"] = str(receipt)
    return rec
