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
    p_search.add_argument(
        "--l1c",
        action="store_true",
        help="Forcer la collection sentinel-2-l1c (entrée ACOLITE)",
    )

    p_download = sub.add_parser(
        "download",
        help="Télécharger un L1C : YAML d'AOI ou identifiant MSIL1C (refuse MSIL2A)",
    )
    p_download.add_argument("target", help="Fichier aois/*.yaml ou identifiant MSIL1C")
    p_download.add_argument("--scene", default=None, help="Identifiant de scène (si target est un YAML)")
    p_download.add_argument("--out", type=Path, default=None)
    p_download.add_argument("--limit", type=int, default=12)
    p_download.add_argument("--dry-run", action="store_true")

    p_acolite = sub.add_parser("acolite", help="Correction marine ACOLITE (CLI, fenêtre AOI)")
    p_acolite.add_argument("aoi", type=Path)
    p_acolite.add_argument("--input", type=Path, required=True, help="Dossier .SAFE ou ZIP L1C")
    p_acolite.add_argument("--out", type=Path, default=Path("work/acolite"))

    p_l2w = sub.add_parser("process-l2w", help="L2W ACOLITE → GeoJSON (côte, plats clairs, sondages si calés)")
    p_l2w.add_argument("aoi", type=Path)
    p_l2w.add_argument("--l2w", type=Path, required=True)
    p_l2w.add_argument("--out", type=Path, default=Path("work/out"))
    p_l2w.add_argument("--stumpf-m0", type=float, default=None)
    p_l2w.add_argument("--stumpf-m1", type=float, default=None)
    p_l2w.add_argument("--no-glint", action="store_true")

    p_process = sub.add_parser(
        "process",
        help="Une baie : chercher L1C, télécharger, ACOLITE, GeoJSON",
    )
    p_process.add_argument("aoi", type=Path)
    p_process.add_argument("--scene", default=None)
    p_process.add_argument("--input", type=Path, default=None, help="SAFE déjà local (saute le téléchargement)")
    p_process.add_argument("--l2w", type=Path, default=None, help="L2W déjà local (saute ACOLITE)")
    p_process.add_argument("--out", type=Path, default=Path("work"))
    p_process.add_argument("--stumpf-m0", type=float, default=None)
    p_process.add_argument("--stumpf-m1", type=float, default=None)
    p_process.add_argument("--no-glint", action="store_true")
    p_process.add_argument("--limit", type=int, default=12)

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

    p_camp = sub.add_parser("campaign", help="Lister / chercher les baies d'une campagne (Berry-Mappemonde)")
    p_camp.add_argument("path", type=Path, help="Dossier aois/berry ou manifest.yaml")
    p_camp.add_argument("--phase", choices=["expedition", "route", "world"], default=None)
    p_camp.add_argument("--search", action="store_true", help="Interroger le STAC pour chaque baie")
    p_camp.add_argument("--limit", type=int, default=5)
    p_camp.add_argument("--json", action="store_true", dest="as_json")

    args = parser.parse_args(argv)
    handlers = {
        "search": _cmd_search,
        "download": _cmd_download,
        "acolite": _cmd_acolite,
        "process-l2w": _cmd_process_l2w,
        "process": _cmd_process,
        "coastline": _cmd_coastline,
        "icesat-check": _cmd_icesat,
        "demo": _cmd_demo,
        "schema": lambda _a: _cmd_schema(),
        "auth-check": _cmd_auth,
        "campaign": _cmd_campaign,
    }
    handler = handlers.get(args.cmd)
    if handler is None:
        parser.error(f"commande inconnue : {args.cmd}")
        return 2
    return handler(args)


def _load_aoi_or_fail(path: Path):
    try:
        return load_aoi(path)
    except (OSError, ValueError, KeyError) as exc:
        print(f"Fichier AOI illisible : {exc}", file=sys.stderr)
        return None


def _is_scene_id(value: str) -> bool:
    upper = value.upper()
    return "MSIL1C" in upper or "MSIL2A" in upper


def _default_aoi_path() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "aois" / "la-rochelle.yaml"
        if candidate.is_file():
            return candidate
    return Path.cwd() / "aois" / "la-rochelle.yaml"


def _cmd_search(args: argparse.Namespace) -> int:
    from navimap_satellites.acquire.stac import search_scenes

    aoi = _load_aoi_or_fail(args.aoi)
    if aoi is None:
        return 1
    if args.l1c:
        aoi = aoi.for_l1c()
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
    print(_scenes_table(scenes))
    print(
        f"\n{len(scenes)} scène(s). ACOLITE veut du MSIL1C, pas du MSIL2A. "
        f"Téléchargement : navimap-sat download {args.aoi}"
    )
    return 0


def _cmd_download(args: argparse.Namespace) -> int:
    import httpx

    from navimap_satellites.acquire.auth import CdseAuthError, fetch_cdse_session
    from navimap_satellites.acquire.download import DownloadError, download_best_l1c, download_l1c_scene
    from navimap_satellites.acquire.l1c import L2ARejected
    from navimap_satellites.acquire.odata import ODataError

    print(NOT_FOR_NAVIGATION, file=sys.stderr)
    target = str(args.target)
    if _is_scene_id(target):
        try:
            rec = download_l1c_scene(target, args.out, dry_run=args.dry_run)
        except L2ARejected as exc:
            print(str(exc), file=sys.stderr)
            return 2
        except (ODataError, DownloadError, CdseAuthError, OSError, httpx.HTTPError) as exc:
            print(f"Téléchargement impossible : {exc}", file=sys.stderr)
            return 1
        print(json.dumps(rec, indent=2, ensure_ascii=False))
        return 0

    aoi = _load_aoi_or_fail(Path(target))
    if aoi is None:
        return 1
    dest = args.out or Path("work/scenes")
    try:
        fetch_cdse_session()
        path = download_best_l1c(aoi, dest, scene_id=args.scene, limit=args.limit)
    except (ODataError, DownloadError, LookupError, CdseAuthError, OSError, httpx.HTTPError) as exc:
        print(f"Téléchargement impossible : {exc}", file=sys.stderr)
        return 1
    print(path)
    return 0


def _cmd_acolite(args: argparse.Namespace) -> int:
    from navimap_satellites.correct.acolite import AcoliteError, find_l2w, run_acolite, write_settings

    aoi = _load_aoi_or_fail(args.aoi)
    if aoi is None:
        return 1
    print(NOT_FOR_NAVIGATION, file=sys.stderr)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    try:
        settings = write_settings(out / "acolite_settings.txt", inputfile=args.input, output=out, aoi=aoi)
        run_acolite(settings)
        l2w = find_l2w(out)
    except AcoliteError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(l2w)
    return 0


def _cmd_process_l2w(args: argparse.Namespace) -> int:
    from navimap_satellites.extract.l2w import L2WError, read_l2w
    from navimap_satellites.process import vectorize_reflectance

    aoi = _load_aoi_or_fail(args.aoi)
    if aoi is None:
        return 1
    print(NOT_FOR_NAVIGATION, file=sys.stderr)
    try:
        scene = read_l2w(args.l2w, bbox=aoi.bbox)
        paths = vectorize_reflectance(
            scene,
            args.out,
            aoi=aoi,
            apply_glint=not args.no_glint,
            stumpf_m0=args.stumpf_m0,
            stumpf_m1=args.stumpf_m1,
        )
    except (L2WError, OSError, ValueError) as exc:
        print(f"Traitement L2W impossible : {exc}", file=sys.stderr)
        return 1
    for key, path in paths.items():
        print(f"{key}: {path}")
    if "soundings" not in paths:
        print(
            "Sondages non écrits : donnez --stumpf-m0 et --stumpf-m1 "
            "(calage, plus tard ICESat-2). Sans ça le ratio n'est pas une profondeur.",
            file=sys.stderr,
        )
    return 0


def _cmd_process(args: argparse.Namespace) -> int:
    """Enchaîne download → ACOLITE → GeoJSON, en sautant les étapes déjà fournies."""
    if args.l2w:
        args.l2w = Path(args.l2w)
        return _cmd_process_l2w(args)
    aoi = _load_aoi_or_fail(args.aoi)
    if aoi is None:
        return 1
    safe = args.input
    if safe is None:
        import httpx

        from navimap_satellites.acquire.auth import CdseAuthError, fetch_cdse_session
        from navimap_satellites.acquire.download import DownloadError, download_best_l1c
        from navimap_satellites.acquire.odata import ODataError

        print(NOT_FOR_NAVIGATION, file=sys.stderr)
        try:
            fetch_cdse_session()
            safe = download_best_l1c(
                aoi,
                Path(args.out) / "scenes",
                scene_id=args.scene,
                limit=args.limit,
            )
        except (ODataError, DownloadError, LookupError, CdseAuthError, OSError, httpx.HTTPError) as exc:
            print(f"Téléchargement impossible : {exc}", file=sys.stderr)
            return 1
        print(f"safe: {safe}")
    aco_out = Path(args.out) / "acolite"
    aco = argparse.Namespace(aoi=args.aoi, input=Path(safe), out=aco_out)
    if _cmd_acolite(aco) != 0:
        return 1
    from navimap_satellites.correct.acolite import find_l2w

    try:
        l2w = find_l2w(aco_out)
    except Exception as exc:  # noqa: BLE001
        print(f"L2W introuvable après ACOLITE : {exc}", file=sys.stderr)
        return 1
    l2w_args = argparse.Namespace(
        aoi=args.aoi,
        l2w=l2w,
        out=Path(args.out) / "out",
        stumpf_m0=args.stumpf_m0,
        stumpf_m1=args.stumpf_m1,
        no_glint=args.no_glint,
    )
    return _cmd_process_l2w(l2w_args)


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


def _cmd_campaign(args: argparse.Namespace) -> int:
    from navimap_satellites.acquire.stac import search_scenes
    from navimap_satellites.campaign import load_campaign

    print(NOT_FOR_NAVIGATION, file=sys.stderr)
    try:
        campaign = load_campaign(args.path).filter_phase(args.phase)
    except (OSError, ValueError, KeyError) as exc:
        print(f"Campagne illisible : {exc}", file=sys.stderr)
        return 1
    if not campaign.stages:
        print("Aucune baie pour cette phase.")
        return 0
    rows = []
    for aoi, path in zip(campaign.stages, campaign.paths, strict=True):
        row = {
            "id": aoi.id,
            "name": aoi.name,
            "phase": aoi.phase,
            "order": aoi.order,
            "water_type": aoi.water_type,
            "path": str(path),
            "bbox": list(aoi.bbox),
        }
        if args.search:
            try:
                scenes = search_scenes(aoi.for_l1c(), limit=args.limit)
                row["scenes"] = [s.as_dict() for s in scenes]
                row["best"] = scenes[0].id if scenes else None
            except Exception as exc:  # noqa: BLE001
                row["error"] = str(exc)
        rows.append(row)
    if args.as_json:
        print(
            json.dumps(
                {"id": campaign.id, "name": campaign.name, "notes": campaign.notes, "stages": rows},
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0
    print(f"# {campaign.name}  [{campaign.id}]")
    if campaign.notes:
        print(campaign.notes)
        print()
    print(f"{'ordre':>5} {'phase':<12} {'id':<28} {'eau':<14} nom")
    for aoi in campaign.stages:
        print(
            f"{aoi.order:5d} {aoi.phase or '—':<12} {aoi.id:<28} {aoi.water_type:<14} {aoi.name}"
        )
    print(
        f"\n{len(campaign.stages)} baie(s). Une à la fois : "
        f"navimap-sat process {campaign.paths[0]}"
    )
    if args.search:
        for row in rows:
            best = row.get("best") or row.get("error") or "aucune scène"
            print(f"- {row['id']}: {best}")
    return 0


def _scenes_table(scenes) -> str:
    lines = [
        f"{'date':<22} {'nuages%':>8} {'eau%':>7} {'tuile':<14} {'plateforme':<14} id"
    ]
    for scene in scenes:
        cloud = "—" if scene.cloud_cover is None else f"{scene.cloud_cover:7.2f}"
        water = "—" if scene.water_percent is None else f"{scene.water_percent:6.1f}"
        lines.append(
            f"{scene.datetime:<22} {cloud:>8} {water:>7} {scene.tile:<14} "
            f"{scene.platform:<14} {scene.id}"
        )
    return "\n".join(lines)
