"""Preview the protected site on this computer only."""

from __future__ import annotations

import os
import secrets
import sys
from pathlib import Path


private_file = (Path(__file__).resolve().parent.parent / "_ACCES_PRIVE" / "ACCES_PARKING_IP7_PRIVE.local.txt")
if not private_file.is_file():
    raise SystemExit(f"Fichier d'accès privé manquant : {private_file}")
for line in private_file.read_text(encoding="utf-8").splitlines():
    if line.startswith("PARKING_PASSWORD_HASH : "):
        os.environ["PARKING_PASSWORD_HASH"] = line.split(" : ", 1)[1]
        break
else:
    raise SystemExit("Empreinte du mot de passe introuvable.")

os.environ["SECRET_KEY"] = secrets.token_urlsafe(32)
os.environ["PARKING_COOKIE_SECURE"] = "false"
sys.dont_write_bytecode = True

from app import app  # noqa: E402


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8010)
