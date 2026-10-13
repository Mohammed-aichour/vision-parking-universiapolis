import argparse
import functools
import http.server
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Démo parking intelligent sur vidéo enregistrée")
    sub = parser.add_subparsers(dest="command", required=True)

    annotate = sub.add_parser("annotate", help="Dessiner les places sur une image de la vidéo")
    annotate.add_argument("--video", type=Path, required=True)
    annotate.add_argument("--out", type=Path, default=Path("02_POLYGONES/places_18.json"))
    annotate.add_argument("--at", type=float, default=0, help="Seconde à capturer pour la calibration")

    analyze = sub.add_parser("analyze", help="Analyser une vidéo avec YOLO")
    analyze.add_argument("--video", type=Path, required=True)
    analyze.add_argument("--zones", type=Path, default=Path("02_POLYGONES/places_18.json"))
    analyze.add_argument("--out-dir", type=Path, default=Path("05_RESULTATS_DEMO"))
    analyze.add_argument("--model", default="07_MODELE_YOLO/yolo26n.pt")
    analyze.add_argument("--stride", type=int, default=2)
    analyze.add_argument("--confidence", type=float, default=0.25)
    analyze.add_argument("--stable-sec", type=float, default=1.5)
    analyze.add_argument("--free-stable-sec", type=float, default=None,
                         help="Durée de confirmation avant de déclarer une place libre")
    analyze.add_argument("--recording-start", default=None,
                         help="Heure HH:MM:SS lue sur la première image de la caméra")

    serve = sub.add_parser("serve", help="Ouvrir les résultats dans un navigateur")
    serve.add_argument("--dir", type=Path, default=Path("05_RESULTATS_DEMO"))
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--host", default="127.0.0.1")

    args = parser.parse_args()
    if args.command == "annotate":
        from .annotate import run
        run(args.video, args.out, args.at)
    elif args.command == "analyze":
        from .analyze import run
        out = run(args.video, args.zones, args.out_dir, args.model, args.stride,
                  args.confidence, args.stable_sec, args.free_stable_sec, args.recording_start)
        print(f"Analyse terminée : {out.resolve()}")
        print(f"Tableau de bord : python -m parking_demo serve --dir \"{out}\"")
    else:
        if not args.dir.is_dir() or not (args.dir / "resultats.json").exists():
            parser.error(f"Aucun résultat dans {args.dir}. Lance d'abord analyze.")
        from .server import RangeHTTPRequestHandler
        handler = functools.partial(RangeHTTPRequestHandler, directory=str(args.dir.resolve()))
        server = http.server.ThreadingHTTPServer((args.host, args.port), handler)
        print(f"Ouvre http://{args.host}:{args.port} ; Ctrl+C pour arrêter")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()


if __name__ == "__main__":
    main()
