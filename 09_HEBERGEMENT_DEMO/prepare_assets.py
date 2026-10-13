"""Refresh the protected presentation assets from the latest local analysis."""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path


FILES = ("index.html", "video_annotee.mp4", "resultats.json", "plan_18_places.jpg", "apercu.jpg")
LOGOUT = '<form action="/deconnexion" method="post" style="margin:0"><button type="submit" style="background:transparent;color:#d3e5f0;border:1px solid #55718a;border-radius:7px;padding:6px 10px;cursor:pointer">Déconnexion</button></form>'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Dossier contenant le tableau de bord et les résultats")
    args = parser.parse_args()
    source = args.source.resolve()
    target = Path(__file__).resolve().parent / "private_assets"
    if not all((source / name).is_file() for name in FILES):
        parser.error("Le dossier source ne contient pas les cinq fichiers requis.")
    target.mkdir(exist_ok=True)
    for name in FILES:
        if (source / name).resolve() != (target / name).resolve():
            shutil.copy2(source / name, target / name)
    html = (target / "index.html").read_text(encoding="utf-8")
    if LOGOUT not in html:
        marker = '<span class="pill">DÉMONSTRATION VIDÉO</span>'
        if marker not in html:
            raise RuntimeError("En-tête du tableau de bord modifié : ajouter manuellement Déconnexion.")
        html = html.replace(marker, marker + LOGOUT, 1)
    html = re.sub(r'\s*·\s*<a href="video_annotee\.mp4[^"]*" download>Télécharger la vidéo</a>', '', html)
    (target / "index.html").write_text(html, encoding="utf-8")
    print("Fichiers de présentation actualisés.")


if __name__ == "__main__":
    main()
