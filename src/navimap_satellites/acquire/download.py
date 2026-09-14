"""Téléchargement d'un granule Sentinel via OData ($value), avec cache et retries."""

from __future__ import annotations

import time
import zipfile
from collections.abc import Callable
from pathlib import Path

import httpx

from navimap_satellites.acquire.auth import CdseAuthError, CdseToken, fetch_cdse_session, refresh_cdse_token
from navimap_satellites.aoi import AOI
from navimap_satellites.acquire.odata import ODataProduct, resolve_l1c_product
from navimap_satellites.acquire.stac import Scene, pick_best_scene

DEFAULT_RETRIES = 4
DEFAULT_TIMEOUT_S = 120.0


class DownloadError(RuntimeError):
    """Échec de téléchargement après retries."""


def download_product(
    product: ODataProduct,
    dest_dir: str | Path,
    *,
    token: CdseToken | str | None = None,
    client: httpx.Client | None = None,
    retries: int = DEFAULT_RETRIES,
    sleep: Callable[[float], None] = time.sleep,
) -> Path:
    """Télécharge le ZIP, l'extrait, renvoie le dossier .SAFE (ou le recrée s'il est déjà là)."""
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    safe_dir = dest / product.name
    if _looks_like_safe(safe_dir):
        return safe_dir
    zip_path = dest / f"{product.name}.zip"
    if zip_path.is_file() and zip_path.stat().st_size > 0:
        return extract_safe_zip(zip_path, dest, product.name)
    session = _as_token(token)
    own = client is None
    http = client or httpx.Client(timeout=DEFAULT_TIMEOUT_S, follow_redirects=True)
    try:
        _download_zip(product, zip_path, session, http, retries=retries, sleep=sleep)
    finally:
        if own:
            http.close()
    return extract_safe_zip(zip_path, dest, product.name)


def download_scene(
    scene: Scene,
    dest_dir: str | Path,
    *,
    token: CdseToken | str | None = None,
    client: httpx.Client | None = None,
    retries: int = DEFAULT_RETRIES,
    sleep: Callable[[float], None] = time.sleep,
) -> Path:
    """Résout le produit L1C puis télécharge."""
    product = resolve_l1c_product(
        scene.id,
        odata_id=(scene.extra or {}).get("odata_id"),
        client=client,
    )
    return download_product(
        product,
        dest_dir,
        token=token,
        client=client,
        retries=retries,
        sleep=sleep,
    )


def download_best_l1c(
    aoi: AOI,
    dest_dir: str | Path,
    *,
    scene_id: str | None = None,
    limit: int = 12,
    token: CdseToken | str | None = None,
    client: httpx.Client | None = None,
    retries: int = DEFAULT_RETRIES,
    sleep: Callable[[float], None] = time.sleep,
) -> Path:
    """Télécharge la scène L1C la moins nuageuse, ou `--scene` s'il est donné."""
    if scene_id:
        product = resolve_l1c_product(scene_id, client=client)
    else:
        scene = pick_best_scene(aoi, limit=limit, client=client)
        product = resolve_l1c_product(
            scene.id,
            odata_id=(scene.extra or {}).get("odata_id"),
            client=client,
        )
    return download_product(
        product,
        dest_dir,
        token=token,
        client=client,
        retries=retries,
        sleep=sleep,
    )


def extract_safe_zip(zip_path: str | Path, dest_dir: str | Path, product_name: str) -> Path:
    """Dézippe un SAFE en refusant les chemins qui sortent du dossier."""
    dest = Path(dest_dir)
    target = dest / product_name
    if _looks_like_safe(target):
        return target
    archive = Path(zip_path)
    if not zipfile.is_zipfile(archive):
        raise DownloadError(f"Fichier ZIP illisible : {archive}")
    with zipfile.ZipFile(archive) as zf:
        _safe_extract(zf, dest)
    if _looks_like_safe(target):
        return target
    found = [p for p in dest.glob("*.SAFE") if p.is_dir()]
    if len(found) == 1:
        return found[0]
    raise DownloadError(f"ZIP téléchargé mais dossier {product_name} introuvable.")


def _download_zip(
    product: ODataProduct,
    zip_path: Path,
    session: CdseToken,
    http: httpx.Client,
    *,
    retries: int,
    sleep: Callable[[float], None],
) -> None:
    url = product.download_url()
    partial = zip_path.with_suffix(zip_path.suffix + ".partial")
    last_error: Exception | None = None
    for attempt in range(max(1, retries)):
        try:
            session = _ensure_token(session, http)
            headers = {"Authorization": f"Bearer {session.access_token}"}
            with http.stream("GET", url, headers=headers) as response:
                if response.status_code == 401 and session.refresh_token:
                    session = refresh_cdse_token(session.refresh_token, client=http)
                    raise DownloadError("jeton expiré, nouvel essai")
                _write_stream(response, partial)
            partial.replace(zip_path)
            return
        except (httpx.HTTPError, DownloadError, CdseAuthError) as exc:
            last_error = exc
            if partial.exists():
                partial.unlink(missing_ok=True)
            if attempt + 1 >= retries:
                break
            sleep(2**attempt)
    raise DownloadError(f"Téléchargement impossible pour {product.name} : {last_error}") from last_error


def _write_stream(response: httpx.Response, dest: Path) -> None:
    if response.status_code >= 400:
        raise DownloadError(f"CDSE a refusé le téléchargement (HTTP {response.status_code}).")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as handle:
        for chunk in response.iter_bytes():
            if chunk:
                handle.write(chunk)
    if dest.stat().st_size <= 0:
        raise DownloadError("Fichier téléchargé vide.")


def _safe_extract(zf: zipfile.ZipFile, dest: Path) -> None:
    dest = dest.resolve()
    for info in zf.infolist():
        name = info.filename
        if name.startswith("/") or ".." in Path(name).parts:
            raise DownloadError(f"ZIP suspect (chemin {name}).")
    zf.extractall(dest)


def _looks_like_safe(path: Path) -> bool:
    if not path.is_dir():
        return False
    return any(path.glob("MTD_MSI*.xml")) or (path / "manifest.safe").is_file()


def _as_token(token: CdseToken | str | None) -> CdseToken:
    if isinstance(token, CdseToken):
        return token
    if isinstance(token, str) and token.strip():
        return CdseToken(access_token=token.strip())
    return fetch_cdse_session()


def _ensure_token(session: CdseToken, http: httpx.Client) -> CdseToken:
    if session.access_token:
        return session
    if session.refresh_token:
        return refresh_cdse_token(session.refresh_token, client=http)
    return fetch_cdse_session(client=http)
