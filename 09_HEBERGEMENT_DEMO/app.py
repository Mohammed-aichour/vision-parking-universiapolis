"""Private, read-only presentation of the precomputed IP7 parking demo."""

from __future__ import annotations

import hmac
import os
import re
import time
from datetime import timedelta
from pathlib import Path

from flask import Flask, Response, abort, redirect, render_template, request, send_from_directory, session, url_for
from werkzeug.security import check_password_hash


BASE = Path(__file__).resolve().parent
PRIVATE_ASSETS = BASE / "private_assets"
USERNAME = "parking.universiapolis@e-polytechnique.ma"
PASSWORD_HASH = os.getenv("PARKING_PASSWORD_HASH", "")
SECRET_KEY = os.getenv("SECRET_KEY", "vision-parking-secret-key-fallback")

app = Flask(__name__, template_folder=str(BASE / "templates"))
app.secret_key = SECRET_KEY
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("PARKING_COOKIE_SECURE", "true" if os.getenv("VERCEL") else "false").lower() == "true",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
)

ASSETS = {
    "video_annotee.mp4": "video/mp4",
    "resultats.json": "application/json",
    "plan_18_places.jpg": "image/jpeg",
    "apercu.jpg": "image/jpeg",
}
ATTEMPTS: dict[str, list[float]] = {}
VIDEO_CHUNK_BYTES = 2 * 1024 * 1024


@app.after_request
def privacy_headers(response):
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
        "media-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'self'"
    )
    return response


def signed_in() -> bool:
    return session.get("authenticated") is True


def blocked(ip: str) -> bool:
    now = time.monotonic()
    ATTEMPTS[ip] = [instant for instant in ATTEMPTS.get(ip, []) if now - instant < 900]
    return len(ATTEMPTS[ip]) >= 8


@app.route("/connexion", methods=["GET", "POST"])
def login():
    if signed_in():
        return redirect(url_for("home"))
    error = None
    if request.method == "POST":
        ip = request.remote_addr or "unknown"
        if blocked(ip):
            error = "Trop de tentatives. Réessayez dans quelques minutes."
        else:
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            if not PASSWORD_HASH:
                error = "Configuration serveur : variable PARKING_PASSWORD_HASH non définie."
            else:
                valid_user = hmac.compare_digest(username.encode("utf-8"), USERNAME.encode("utf-8"))
                valid_password = check_password_hash(PASSWORD_HASH, password)
                if valid_user and valid_password:
                    ATTEMPTS.pop(ip, None)
                    session.clear()
                    session["authenticated"] = True
                    session.permanent = True
                    return redirect(url_for("home"))
                ATTEMPTS.setdefault(ip, []).append(time.monotonic())
                error = "Identifiant ou mot de passe incorrect."
    return render_template("login.html", error=error, username=USERNAME), 200


@app.post("/deconnexion")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.get("/")
def home():
    if not signed_in():
        return redirect(url_for("login"))
    return send_from_directory(PRIVATE_ASSETS, "index.html", mimetype="text/html")


def video_chunk():
    """Serve authenticated byte ranges below Vercel's function response limit."""
    path = PRIVATE_ASSETS / "video_annotee.mp4"
    size = path.stat().st_size
    raw = request.headers.get("Range", "")
    if raw:
        match = re.fullmatch(r"bytes=(\d*)-(\d*)", raw.strip())
        if not match or not any(match.groups()):
            response = Response(status=416)
            response.headers["Content-Range"] = f"bytes */{size}"
            return response
        first, last = match.groups()
        if first:
            start = int(first)
            end = min(int(last) if last else size - 1, size - 1)
        else:
            count = int(last)
            start = max(0, size - count)
            end = size - 1
        if start >= size or end < start:
            response = Response(status=416)
            response.headers["Content-Range"] = f"bytes */{size}"
            return response
    else:
        start, end = 0, size - 1
    end = min(end, start + VIDEO_CHUNK_BYTES - 1)
    with path.open("rb") as source:
        source.seek(start)
        payload = source.read(end - start + 1)
    response = Response(payload, status=206, mimetype="video/mp4")
    response.headers["Accept-Ranges"] = "bytes"
    response.headers["Content-Range"] = f"bytes {start}-{end}/{size}"
    response.headers["Content-Length"] = str(len(payload))
    return response


@app.get("/<path:filename>")
def asset(filename: str):
    if filename not in ASSETS:
        abort(404)
    if not signed_in():
        abort(401)
    if filename == "video_annotee.mp4":
        return video_chunk()
    return send_from_directory(PRIVATE_ASSETS, filename, mimetype=ASSETS[filename], conditional=True)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8010)
