"""Jeton Copernicus Data Space Ecosystem (CDSE).

Ce n'est PAS le compte Copernicus Marine (CMEMS) utilisé pour le vent et
la houle. Deux services, deux inscriptions.
"""

from __future__ import annotations

import os

import httpx

TOKEN_URL = (
    "https://identity.dataspace.copernicus.eu/auth/realms/CDSE"
    "/protocol/openid-connect/token"
)
CLIENT_ID = "cdse-public"


class CdseAuthError(RuntimeError):
    """Identifiants CDSE absents ou refusés."""


def fetch_cdse_token(
    username: str | None = None,
    password: str | None = None,
    *,
    client: httpx.Client | None = None,
) -> str:
    """Obtient un jeton OpenID. Priorité : CDSE_ACCESS_TOKEN, sinon login/mot de passe."""
    existing = os.environ.get("CDSE_ACCESS_TOKEN", "").strip()
    if existing:
        return existing
    user = (username or os.environ.get("CDSE_USERNAME") or "").strip()
    secret = (password or os.environ.get("CDSE_PASSWORD") or "").strip()
    if not user or not secret:
        raise CdseAuthError(
            "Compte CDSE manquant. Créez-en un sur https://dataspace.copernicus.eu "
            "puis renseignez CDSE_USERNAME et CDSE_PASSWORD dans .env "
            "(ce n'est pas le compte Copernicus Marine)."
        )
    own = client is None
    http = client or httpx.Client(timeout=30.0)
    try:
        response = http.post(
            TOKEN_URL,
            data={
                "grant_type": "password",
                "username": user,
                "password": secret,
                "client_id": CLIENT_ID,
            },
        )
        if response.status_code >= 400:
            raise CdseAuthError(
                f"CDSE a refusé l'authentification (HTTP {response.status_code}). "
                "Vérifiez le compte Data Space, pas Marine."
            )
        token = (response.json() or {}).get("access_token")
        if not token:
            raise CdseAuthError("Réponse CDSE sans access_token.")
        return str(token)
    finally:
        if own:
            http.close()
