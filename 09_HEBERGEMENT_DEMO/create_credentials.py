"""Generate a strong password and its hash for the hosting provider."""

from __future__ import annotations

import argparse
import secrets
from pathlib import Path

from werkzeug.security import generate_password_hash


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="Private local text file outside the deployable repository")
    args = parser.parse_args()
    target = args.output.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        parser.error("Le fichier privé existe déjà ; il ne sera pas remplacé.")
    password = "-".join(secrets.token_urlsafe(5) for _ in range(4))
    password_hash = generate_password_hash(password, method="scrypt")
    target.write_text(
        "ACCÈS PRIVÉ — NE PAS PUBLIER DANS UN DÉPÔT GIT\n"
        "Identifiant : parking.universiapolis@e-polytechnique.ma\n"
        f"Mot de passe : {password}\n"
        f"PARKING_PASSWORD_HASH : {password_hash}\n",
        encoding="utf-8",
    )
    print(f"Identifiants créés dans : {target}")


if __name__ == "__main__":
    main()
