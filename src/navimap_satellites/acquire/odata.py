"""Catalogue OData CDSE : UUID et nom de produit SAFE."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

ODATA_PRODUCTS_URL = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
DOWNLOAD_URL = "https://download.dataspace.copernicus.eu/odata/v1/Products({id})/$value"


class ODataError(RuntimeError):
    """Produit introuvable ou catalogue injoignable."""


@dataclass(frozen=True)
class ODataProduct:
    id: str
    name: str
    s3_path: str | None = None
    content_length: int | None = None

    def download_url(self) -> str:
        return DOWNLOAD_URL.format(id=self.id)


def as_l1c_product_name(scene_id: str) -> str:
    """Nom SAFE L1C. ACOLITE / DSF part du TOA, pas du L2A Sen2Cor."""
    name = scene_id.strip()
    name = name.replace("MSIL2A", "MSIL1C")
    if not name.endswith(".SAFE"):
        name += ".SAFE"
    return name


def as_product_name(scene_id: str) -> str:
    name = scene_id.strip()
    if not name.endswith(".SAFE"):
        name += ".SAFE"
    return name


def lookup_product(
    name: str,
    *,
    client: httpx.Client | None = None,
    url: str = ODATA_PRODUCTS_URL,
) -> ODataProduct:
    """Cherche un produit par Name (ex. S2C_MSIL1C_….SAFE)."""
    safe = name.replace("'", "''")
    query = f"{url}?$filter=Name eq '{safe}'&$select=Id,Name,S3Path,ContentLength"
    own = client is None
    http = client or httpx.Client(timeout=45.0)
    try:
        response = http.get(query)
        response.raise_for_status()
        rows = (response.json() or {}).get("value") or []
    finally:
        if own:
            http.close()
    if not rows:
        raise ODataError(f"Aucun produit OData nommé {name}.")
    row = rows[0]
    length = row.get("ContentLength")
    return ODataProduct(
        id=str(row["Id"]),
        name=str(row.get("Name") or name),
        s3_path=row.get("S3Path"),
        content_length=int(length) if length is not None else None,
    )


def resolve_l1c_product(
    scene_id: str,
    *,
    odata_id: str | None = None,
    client: httpx.Client | None = None,
    url: str = ODATA_PRODUCTS_URL,
) -> ODataProduct:
    """Préfère un UUID déjà connu, sinon le nom L1C, sinon le nom tel quel."""
    if odata_id:
        name = as_l1c_product_name(scene_id)
        return ODataProduct(id=odata_id, name=name)
    l1c = as_l1c_product_name(scene_id)
    try:
        return lookup_product(l1c, client=client, url=url)
    except ODataError:
        original = as_product_name(scene_id)
        if original == l1c:
            raise
        return lookup_product(original, client=client, url=url)
