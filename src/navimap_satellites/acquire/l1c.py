"""Garde-fous L1C : ACOLITE refuse le L2A ESA (correction terre)."""

from __future__ import annotations

L1C_COLLECTION = "sentinel-2-l1c"
L2A_COLLECTION = "sentinel-2-l2a"

KNOWN_L1C_LA_ROCHELLE = "S2C_MSIL1C_20260912T110631_N0512_R137_T30TWR_20260912T130923"
KNOWN_L2A_REJECTED = "S2C_MSIL2A_20260912T110631_N0512_R137_T30TWR_20260912T145321"


class L2ARejected(ValueError):
    """Scène L2A : Sen2Cor (terre), pas une entrée ACOLITE."""


def is_l2a_scene(scene_id: str) -> bool:
    return "MSIL2A" in (scene_id or "").upper()


def is_l1c_scene(scene_id: str) -> bool:
    return "MSIL1C" in (scene_id or "").upper()


def product_name(scene_id: str) -> str:
    name = (scene_id or "").strip()
    if not name.endswith(".SAFE"):
        name = f"{name}.SAFE"
    return name


def require_l1c(scene_id: str) -> None:
    if is_l2a_scene(scene_id):
        raise L2ARejected(
            "ACOLITE refuse Sentinel-2 L2A (Level-2A data not supported). "
            "Le L2A ESA (Sen2Cor) est une correction terre, pas un raccourci "
            "littoral. Utilisez le jumeau L1C, par ex. "
            f"{KNOWN_L1C_LA_ROCHELLE}."
        )
