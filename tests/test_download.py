import io
import zipfile
from pathlib import Path

import httpx

from navimap_satellites.acquire.auth import CdseToken
from navimap_satellites.acquire.download import download_product, extract_safe_zip
from navimap_satellites.acquire.odata import ODataProduct


def _safe_zip_bytes(name: str = "S2C_MSIL1C_x.SAFE") -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr(f"{name}/MTD_MSIL1C.xml", "<xml/>")
        zf.writestr(f"{name}/manifest.safe", "ok")
    return buffer.getvalue()


def test_extract_reuses_existing_safe(tmp_path: Path):
    name = "S2C_MSIL1C_x.SAFE"
    safe = tmp_path / name
    safe.mkdir()
    (safe / "MTD_MSIL1C.xml").write_text("<xml/>", encoding="utf-8")
    zip_path = tmp_path / f"{name}.zip"
    zip_path.write_bytes(_safe_zip_bytes(name))
    assert extract_safe_zip(zip_path, tmp_path, name) == safe


def test_download_product_streams_and_extracts(tmp_path: Path):
    name = "S2C_MSIL1C_x.SAFE"
    payload = _safe_zip_bytes(name)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer tok"
        return httpx.Response(200, content=payload)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    product = ODataProduct(id="abc", name=name)
    path = download_product(
        product,
        tmp_path,
        token=CdseToken(access_token="tok"),
        client=client,
        retries=1,
    )
    assert path.name == name
    assert (path / "MTD_MSIL1C.xml").is_file()


def test_download_skips_if_safe_present(tmp_path: Path):
    name = "S2C_MSIL1C_x.SAFE"
    safe = tmp_path / name
    safe.mkdir()
    (safe / "MTD_MSIL1C.xml").write_text("<xml/>", encoding="utf-8")
    product = ODataProduct(id="abc", name=name)
    path = download_product(product, tmp_path, token="unused")
    assert path == safe


def test_download_retries_then_succeeds(tmp_path: Path):
    name = "S2C_MSIL1C_x.SAFE"
    payload = _safe_zip_bytes(name)
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(503, text="busy")
        return httpx.Response(200, content=payload)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    product = ODataProduct(id="abc", name=name)
    path = download_product(
        product,
        tmp_path,
        token="tok",
        client=client,
        retries=3,
        sleep=lambda _s: None,
    )
    assert path.is_dir()
    assert calls["n"] == 2
