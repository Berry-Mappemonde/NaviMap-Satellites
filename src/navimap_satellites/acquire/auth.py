"""Jeton Copernicus Data Space Ecosystem (CDSE).

Ce n'est PAS le compte Copernicus Marine (CMEMS) utilisé pour le vent et
la houle. Deux services, deux inscriptions.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

TOKEN_URL = (
    "https://identity.dataspace.copernicus.eu/auth/realms/CDSE"
    "/protocol/openid-connect/token"
)
CLIENT_ID = "cdse-public"


class CdseAuthError(RuntimeError):
    """Identifiants CDSE absents ou refusés."""


@dataclass
class CdseToken:
    """Jeton d'accès + refresh (le access expire en ~10 minutes)."""

    access_token: str
    refresh_token: str | None = None
    expires_in: int | None = None


def fetch_cdse_token(
    username: str | None = None,
    password: str | None = None,
    *,
    client: httpx.Client | None = None,
) -> str:
    """Obtient un jeton OpenID. Priorité : CDSE_ACCESS_TOKEN, sinon login/mot de passe."""
    return fetch_cdse_session(username, password, client=client).access_token


def fetch_cdse_session(
    username: str | None = None,
    password: str | None = None,
    *,
    client: httpx.Client | None = None,
) -> CdseToken:
    """Comme fetch_cdse_token, mais conserve le refresh_token pour les gros téléchargements."""
    existing = os.environ.get("CDSE_ACCESS_TOKEN", "").strip()
    if existing:
        return CdseToken(access_token=existing)
    user = (username or os.environ.get("CDSE_USERNAME") or "").strip()
    secret = (password or os.environ.get("CDSE_PASSWORD") or "").strip()
    if not user or not secret:
        raise CdseAuthError(
            "Compte CDSE manquant. Créez-en un sur https://dataspace.copernicus.eu "
            "puis renseignez CDSE_USERNAME et CDSE_PASSWORD dans .env "
            "(ce n'est pas le compte Copernicus Marine)."
        )
    return _token_request(
        {
            "grant_type": "password",
            "username": user,
            "password": secret,
            "client_id": CLIENT_ID,
        },
        client=client,
    )


def refresh_cdse_token(
    refresh_token: str,
    *,
    client: httpx.Client | None = None,
) -> CdseToken:
    """Renouvelle l'access_token sans renvoyer le mot de passe."""
    return _token_request(
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": CLIENT_ID,
        },
        client=client,
    )


def _token_request(
    data: dict[str, str],
    *,
    client: httpx.Client | None = None,
) -> CdseToken:
    own = client is None
    http = client or httpx.Client(timeout=30.0)
    try:
        response = http.post(TOKEN_URL, data=data)
        if response.status_code >= 400:
            raise CdseAuthError(
                f"CDSE a refusé l'authentification (HTTP {response.status_code}). "
                "Vérifiez le compte Data Space, pas Marine."
            )
        payload = response.json() or {}
        token = payload.get("access_token")
        if not token:
            raise CdseAuthError("Réponse CDSE sans access_token.")
        expires = payload.get("expires_in")
        return CdseToken(
            access_token=str(token),
            refresh_token=(str(payload["refresh_token"]) if payload.get("refresh_token") else None),
            expires_in=int(expires) if expires is not None else None,
        )
    finally:
        if own:
            http.close()
