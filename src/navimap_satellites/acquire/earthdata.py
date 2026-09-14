"""Jeton NASA Earthdata Login.

Troisième compte, distinct de Copernicus Data Space et de Copernicus Marine.
La recherche CMR (ATL24) et les tuiles GIBS n'en ont pas besoin.
Le jeton sert au téléchargement des granules HDF5 (plus tard).
"""

from __future__ import annotations

import os

import httpx

from navimap_satellites.acquire.envfile import load_cdse_env

URS_TOKEN_URL = "https://urs.earthdata.nasa.gov/api/users/find_or_create_token"


class EarthdataAuthError(RuntimeError):
    """Identifiants Earthdata absents ou refusés."""


def fetch_earthdata_token(
    username: str | None = None,
    password: str | None = None,
    *,
    client: httpx.Client | None = None,
) -> str:
    """Priorité : EARTHDATA_TOKEN, sinon login / mot de passe URS."""
    load_cdse_env()
    existing = (
        os.environ.get("EARTHDATA_TOKEN", "").strip()
        or os.environ.get("EARTHDATA_ACCESS_TOKEN", "").strip()
    )
    if existing:
        return existing
    user = (username or os.environ.get("EARTHDATA_USERNAME") or "").strip()
    secret = (password or os.environ.get("EARTHDATA_PASSWORD") or "").strip()
    if not user or not secret:
        raise EarthdataAuthError(
            "Compte Earthdata manquant. Créez-en un sur https://urs.earthdata.nasa.gov "
            "puis renseignez EARTHDATA_USERNAME et EARTHDATA_PASSWORD dans .env "
            "(ce n'est ni CDSE, ni Copernicus Marine). "
            "La recherche ATL24 et le fond GIBS marchent sans ce compte."
        )
    own = client is None
    http = client or httpx.Client(timeout=30.0)
    try:
        response = http.post(URS_TOKEN_URL, auth=(user, secret), headers={"Accept": "application/json"})
        if response.status_code >= 400:
            raise EarthdataAuthError(
                f"Earthdata a refusé l'authentification (HTTP {response.status_code}). "
                "Vérifiez urs.earthdata.nasa.gov, pas Data Space."
            )
        payload = response.json() or {}
        token = payload.get("access_token") or payload.get("token")
        if not token:
            raise EarthdataAuthError("Réponse Earthdata sans access_token.")
        return str(token)
    finally:
        if own:
            http.close()
