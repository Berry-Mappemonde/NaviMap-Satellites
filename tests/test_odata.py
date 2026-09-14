from navimap_satellites.acquire.odata import (
    ODataError,
    as_l1c_product_name,
    as_product_name,
    lookup_product,
    resolve_l1c_product,
)
from navimap_satellites.acquire.stac import Scene, _odata_id_from_href

import httpx
import pytest


def test_l1c_name_from_l2a():
    assert as_l1c_product_name("S2C_MSIL2A_20260912T110631_T30TWR") == (
        "S2C_MSIL1C_20260912T110631_T30TWR.SAFE"
    )
    assert as_product_name("S2C_MSIL1C_x.SAFE") == "S2C_MSIL1C_x.SAFE"


def test_odata_id_from_href():
    href = "https://zipper.dataspace.copernicus.eu/odata/v1/Products(060882f4-0a34-5f14-8e25-6876e4470b0d)/$value"
    assert _odata_id_from_href(href) == "060882f4-0a34-5f14-8e25-6876e4470b0d"
    assert _odata_id_from_href(None) is None


def test_lookup_product(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert "S2C_MSIL1C_x.SAFE" in str(request.url)
        return httpx.Response(
            200,
            json={
                "value": [
                    {
                        "Id": "abc-123",
                        "Name": "S2C_MSIL1C_x.SAFE",
                        "S3Path": "/eodata/S2",
                        "ContentLength": 10,
                    }
                ]
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    product = lookup_product("S2C_MSIL1C_x.SAFE", client=client, url="https://odata.test/Products")
    assert product.id == "abc-123"
    assert product.download_url().endswith("Products(abc-123)/$value")


def test_resolve_uses_known_uuid():
    product = resolve_l1c_product("S2C_MSIL2A_x", odata_id="already-known")
    assert product.id == "already-known"
    assert "MSIL1C" in product.name


def test_lookup_empty():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"value": []})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(ODataError, match="Aucun produit"):
        lookup_product("missing.SAFE", client=client, url="https://odata.test/Products")


def test_scene_as_dict_includes_odata():
    scene = Scene(
        id="S2",
        collection="sentinel-2-l1c",
        datetime="2026-01-01T00:00:00Z",
        cloud_cover=1.0,
        platform="sentinel-2c",
        bbox=(0, 0, 1, 1),
        tile="T30TWR",
        product_href="https://x/Products(aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee)/$value",
        thumbnail_href=None,
        extra={"odata_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"},
    )
    assert scene.as_dict()["odata_id"] == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
