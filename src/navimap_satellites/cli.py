"""Interface en ligne de commande : navimap-sat."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from navimap_satellites import __version__
from navimap_satellites.aoi import load_aoi
from navimap_satellites.quality.disclaimer import NOT_FOR_NAVIGATION


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="navimap-sat",
        description=(
            "NaviMap Satellites — atelier d'hydrographie par satellite. "
            f"{NOT_FOR_NAVIGATION}"
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_search = sub.add_parser("search", help="Chercher des scènes Sentinel-2 (STAC CDSE)")
    p_search.add_argument("aoi", type=Path, help="Fichier YAML de zone (voir aois/)")
    p_search.add_argument("--limit", type=int, default=12, help="Nombre max de scènes")
    p_search.add_argument("--json", action="store_true", dest="as_json", help="Sortie JSON")

    p_coast = sub.add_parser(
        "coastline",
        help="Trait de côte depuis un L2R ACOLITE (rhos_561 / rhos_1612, seuil 0)",
    )
    p_coast.add_argument(
        "--l2r",
        type=Path,
        default=Path.home() / "Desktop" / "sentinel-pilot" / "acolite",
        help="Fichier *L2R*.nc ou dossier qui le contient",
    )
    p_coast.add_argument(
        "--aoi",
        type=Path,
        default=None,
        help="YAML de zone (défaut : aois/la-rochelle.yaml à côté du paquet)",
    )
    p_coast.add_argument(
        "--out",
        type=Path,
        default=Path.home() / "Desktop" / "sentinel-pilot" / "coastline.geojson",
    )

    p_dl = sub.add_parser("download", help="Télécharger un zip L1C (refuse MSIL2A). Inutile si déjà sur le Bureau.")
    p_dl.add_argument("scene_id", help="Identifiant MSIL1C")
    p_dl.add_argument("--out", type=Path, default=None, help="Dossier (défaut : ~/Desktop/sentinel-pilot)")
    p_dl.add_argument("--dry-run", action="store_true")

    p_ice = sub.add_parser(
        "icesat-check",
        help="Dit si ICESat-2 croise la zone. N'écrit aucune profondeur.",
    )
    p_ice.add_argument("--aoi", type=Path, default=None)

    p_demo = sub.add_parser("demo", help="Pipeline complet sur une île synthétique (sans satellite)")
    p_demo.add_argument("--out", type=Path, default=Path("work/demo"), help="Dossier de sortie")

    sub.add_parser("schema", help="Afficher le tableau OpenSeaMap / S-57 / S-101")

    p_auth = sub.add_parser("auth-check", help="Vérifier un compte CDSE (pas CMEMS)")
    p_auth.add_argument("--username", default=None)
    p_auth.add_argument("--password", default=None)

    args = parser.parse_args(argv)
    if args.cmd == "search":
        return _cmd_search(args)
    if args.cmd == "coastline":
        return _cmd_coastline(args)
    if args.cmd == "download":
        return _cmd_download(args)
    if args.cmd == "icesat-check":
        return _cmd_icesat(args)
    if args.cmd == "demo":
        return _cmd_demo(args)
    if args.cmd == "schema":
        return _cmd_schema()
    if args.cmd == "auth-check":
        return _cmd_auth(args)
    parser.error(f"commande inconnue : {args.cmd}")
    return 2


def _cmd_search(args: argparse.Namespace) -> int:
    from navimap_satellites.acquire.stac import search_scenes

    try:
        aoi = load_aoi(args.aoi)
    except (OSError, ValueError, KeyError) as exc:
        print(f"Fichier AOI illisible : {exc}", file=sys.stderr)
        return 1
    print(f"# {aoi.name}  [{aoi.id}]", file=sys.stderr)
    print(f"# {NOT_FOR_NAVIGATION}", file=sys.stderr)
    try:
        scenes = search_scenes(aoi, limit=args.limit)
    except Exception as exc:  # noqa: BLE001 — message clair pour un débutant
        print(f"Recherche STAC impossible : {exc}", file=sys.stderr)
        return 1
    if args.as_json:
        print(json.dumps([s.as_dict() for s in scenes], indent=2, ensure_ascii=False))
        return 0
    if not scenes:
        print("Aucune scène sous le seuil de nuages. Élargissez les dates ou max_cloud_cover.")
        return 0
    print(
        f"{'date':<22} {'nuages%':>8} {'eau%':>7} {'tuile':<14} {'plateforme':<14} id"
    )
    for scene in scenes:
        cloud = "—" if scene.cloud_cover is None else f"{scene.cloud_cover:7.2f}"
        water = "—" if scene.water_percent is None else f"{scene.water_percent:6.1f}"
        print(
            f"{scene.datetime:<22} {cloud:>8} {water:>7} {scene.tile:<14} "
            f"{scene.platform:<14} {scene.id}"
        )
    print(
        f"\n{len(scenes)} scène(s). ACOLITE veut du MSIL1C, pas du MSIL2A. "
        "Si le zip L1C est déjà sur le Bureau, ne retéléchargez pas."
    )
    return 0


def _default_aoi_path() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "aois" / "la-rochelle.yaml"
        if candidate.is_file():
            return candidate
    return Path.cwd() / "aois" / "la-rochelle.yaml"


def _cmd_coastline(args: argparse.Namespace) -> int:
    from navimap_satellites.correct.l2r import L2RError
    from navimap_satellites.pipeline_coastline import coastline_from_l2r

    aoi_path = args.aoi or _default_aoi_path()
    try:
        aoi = load_aoi(aoi_path)
    except (OSError, ValueError, KeyError) as exc:
        print(f"Fichier AOI illisible : {exc}", file=sys.stderr)
        return 1
    print(NOT_FOR_NAVIGATION, file=sys.stderr)
    print("Aucun sondage ne sera écrit (ICESat-2 = v0.3).", file=sys.stderr)
    try:
        dest = coastline_from_l2r(args.l2r, aoi, args.out)
    except (L2RError, ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(dest)
    return 0


def _cmd_download(args: argparse.Namespace) -> int:
    from navimap_satellites.acquire.download import download_l1c_scene
    from navimap_satellites.acquire.l1c import L2ARejected

    try:
        rec = download_l1c_scene(args.scene_id, args.out, dry_run=args.dry_run)
    except L2ARejected as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"Téléchargement impossible : {exc}", file=sys.stderr)
        return 1
    print(json.dumps(rec, indent=2, ensure_ascii=False))
    return 0


def _cmd_icesat(args: argparse.Namespace) -> int:
    from navimap_satellites.icesat_gate import presence_report

    aoi_path = args.aoi or _default_aoi_path()
    try:
        aoi = load_aoi(aoi_path)
    except (OSError, ValueError, KeyError) as exc:
        print(f"Fichier AOI illisible : {exc}", file=sys.stderr)
        return 1
    report = presence_report(aoi.bbox)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print("Aucun fichier de sondage n'a été écrit.", file=sys.stderr)
    return 0


def _cmd_demo(args: argparse.Namespace) -> int:
    from navimap_satellites.demo import run_demo

    print(NOT_FOR_NAVIGATION, file=sys.stderr)
    paths = run_demo(args.out)
    for key, path in paths.items():
        print(f"{key}: {path}")
    return 0


def _cmd_schema() -> int:
    from navimap_satellites.vectorize.osm_schema import schema_rows

    print(f"{'entité':<22} {'OSM':<42} {'S-57':<8} {'S-101'}")
    for row in schema_rows():
        print(f"{row['feature']:<22} {row['osm']:<42} {row['s57']:<8} {row['s101']}")
    print(f"\n{NOT_FOR_NAVIGATION} Pas de fichier ENC dans cette version.")
    return 0


def _cmd_auth(args: argparse.Namespace) -> int:
    from navimap_satellites.acquire.auth import CdseAuthError, fetch_cdse_token
    from navimap_satellites.acquire.envfile import load_cdse_env

    loaded = load_cdse_env()
    if loaded:
        print("Fichier(s) .env lu(s) (le mot de passe n'est pas affiché) :")
        for path in loaded:
            print(f"  {path}")
    try:
        token = fetch_cdse_token(args.username, args.password)
    except CdseAuthError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"Jeton CDSE obtenu ({len(token)} caractères). La recherche STAC n'en a pas besoin.")
    return 0
