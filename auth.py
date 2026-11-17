"""Accounts for Fruit Lens, powered by InsForge (https://insforge.dev).

InsForge owns identities: sign-up, passwords, e-mail verification, password reset and Google sign-in.
This Flask server talks to InsForge's REST API on behalf of the browser (a "backend for frontend"),
so no InsForge key ever reaches the browser. After InsForge confirms who the user is, Flask opens its
own signed session cookie and mirrors the user in the local SQLite `users` table (scans reference it).
"""
import base64
import hashlib
import os
import re
import logging
import secrets
import time
from collections import defaultdict
from pathlib import Path

from flask import Blueprint, g, jsonify, redirect, request, session

import db
import legacy
from insforge import (HTTP_TIMEOUT, InsforgeError, _cfg, anon_key, call, friendly, insforge_url, jwt_exp,
                      password_problem, public_config)

log = logging.getLogger("fruitlens.auth")

BASE_DIR = Path(__file__).resolve().parent
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")
CODE_RE = re.compile(r"^\d{6}$")
CSRF_HEADER = ("X-Requested-With", "fruitlens")
MAX_FAILS, FAIL_WINDOW = 8, 600  # wrong passwords / codes per 10 minutes per (ip, email)
_fails = defaultdict(list)

bp = Blueprint("auth", __name__, url_prefix="/api/auth")
pages = Blueprint("auth_pages", __name__)


# --------------------------------------------------------------------------- #
# Settings (.env)
# --------------------------------------------------------------------------- #
def load_dotenv():
    """Tiny .env reader (KEY=VALUE per line) so no extra dependency is needed."""
    path = BASE_DIR / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():  # utf-8-sig: Notepad may add a BOM
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if value and value[0] in "\"'" and value.count(value[0]) >= 2:
            value = value[1:value.index(value[0], 1)]  # quoted: keep what is inside the quotes
        else:
            value = re.split(r"\s+#", value, maxsplit=1)[0].strip()  # unquoted: drop a trailing "  # comment"
        os.environ.setdefault(key.strip(), value)


def get_secret_key():
    """SECRET_KEY from the environment, otherwise a random key persisted in instance/ so logins survive restarts."""
    if os.environ.get("SECRET_KEY"):
        return os.environ["SECRET_KEY"]
    path = db.DATA_DIR / "instance" / "secret.key"
    if not path.exists():
        path.parent.mkdir(exist_ok=True)
        path.write_text(secrets.token_hex(32))
        try:
            path.chmod(0o600)
        except OSError:
            pass
    return path.read_text().strip()


def app_url():
    """Public address of this app, used for OAuth/e-mail redirects. Defaults to the address the browser used."""
    explicit = os.environ.get("APP_URL", "").strip().rstrip("/")
    if explicit:
        return explicit
    railway = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "").strip()  # set automatically by Railway
    return f"https://{railway}" if railway else request.host_url.rstrip("/")


def https_deployment():
    """True when the site is served over HTTPS, so session cookies must be marked Secure."""
    return (os.environ.get("COOKIE_SECURE") == "1" or os.environ.get("APP_URL", "").strip().lower().startswith("https://")
            or bool(os.environ.get("RAILWAY_PUBLIC_DOMAIN")))


def init_auth(app):
    load_dotenv()
    app.secret_key = get_secret_key()
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",  # Lax still sends the cookie on the top-level redirect back from Google
        SESSION_COOKIE_SECURE=https_deployment(),
        PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 7,  # same as InsForge's refresh token
    )
    app.register_blueprint(bp)
    app.register_blueprint(pages)

    @app.before_request
    def guard():
        g.user = load_user()
        path = request.path
        if not path.startswith("/api/"):
            return None
        # Cross-site forms/scripts cannot set custom headers, so this blocks CSRF on top of SameSite=Lax.
        if request.method not in ("GET", "HEAD", "OPTIONS") and request.headers.get(CSRF_HEADER[0]) != CSRF_HEADER[1]:
            return jsonify({"error": "Invalid request."}), 403
        if not g.user and not path.startswith("/api/auth/") and path != "/api/health":
            return jsonify({"error": "Please sign in first.", "auth_required": True}), 401
        return None

    @app.after_request
    def no_cache(resp):
        if request.path.startswith(("/api/", "/uploads/")) or request.path in ("/", "/login") or request.path.startswith("/auth/"):
            resp.headers["Cache-Control"] = "no-store"  # back button after logout must not show private data
        return resp


# --------------------------------------------------------------------------- #
# Errors
# --------------------------------------------------------------------------- #
class AuthRefused(Exception):
    """We refuse to open a session even though InsForge accepted the credentials."""
    def __init__(self, status, message):
        super().__init__(message)
        self.status, self.message = status, message


# --------------------------------------------------------------------------- #
# Sessions
#
# The signed Flask cookie (HttpOnly) holds who the user is plus their InsForge tokens. The 15-minute access token and
# the 7-day refresh token are what store.py uses to talk to the InsForge database AS that user.
# --------------------------------------------------------------------------- #
def load_user():
    uid = session.get("uid")
    if not uid:
        return None
    if not session.get("rt"):  # a cookie from before the InsForge database: it has no tokens, so sign in again
        session.clear()
        return None
    return {"id": uid, "name": session.get("name") or "", "email": session.get("email") or "",
            "avatar_url": session.get("avatar") or None}


def public_user(u):
    return {"id": u["id"], "name": u["name"], "email": u["email"], "avatar_url": u["avatar_url"]}


def start_session(user, access_token, refresh_token, remember=True):
    session.clear()  # new session on every login (prevents fixation)
    session.update(uid=user["id"], name=user["name"], email=user["email"], avatar=user["avatar_url"],
                   at=access_token, at_exp=jwt_exp(access_token), rt=refresh_token)
    session.permanent = bool(remember)


def sign_in(result, remember=True):
    """Open a Flask session from an InsForge {user, accessToken, refreshToken} response."""
    iu = result.get("user") or {}
    access_token, refresh_token = result.get("accessToken"), result.get("refreshToken")
    email = str(iu.get("email") or "").strip().lower()
    if not iu.get("id") or not access_token or not refresh_token or not email:
        raise InsforgeError(502, "InsForge returned an unexpected response.")
    profile = iu.get("profile") or {}
    user = {"id": str(iu["id"]), "email": email,
            "name": " ".join(str(profile.get("name") or email.split("@")[0]).split())[:60] or "User",
            "avatar_url": profile.get("avatar_url") or None}
    start_session(user, access_token, refresh_token, remember)
    legacy.import_scans(user, bool(iu.get("emailVerified")))  # brings back scans saved before the InsForge database
    return public_user(user)


def body():
    return request.get_json(silent=True) or {}


def clean_email(value):
    return str(value or "").strip().lower()


def throttled(key):
    now = time.time()
    _fails[key] = [t for t in _fails[key] if now - t < FAIL_WINDOW]
    return len(_fails[key]) >= MAX_FAILS


def fail(status, message, **extra):
    return jsonify({"error": message, **extra}), status


def run(ctx, fn):
    """Run an InsForge-backed view and convert errors into JSON responses."""
    try:
        return fn()
    except InsforgeError as e:
        return fail(e.status if 400 <= e.status < 600 else 502, friendly(e, ctx))
    except AuthRefused as e:
        return fail(e.status, e.message)


# --------------------------------------------------------------------------- #
# JSON API
# --------------------------------------------------------------------------- #
@bp.get("/config")
def config():
    """What the login page needs: is InsForge reachable, which methods are on, password rules, one-time message."""
    out = {"configured": bool(insforge_url()), "flash": session.pop("flash", None),
           "redirect_urls": [app_url() + "/auth/callback", app_url() + "/login"]}
    if not out["configured"]:
        out["error"] = "InsForge is not configured. Add INSFORGE_URL and INSFORGE_ANON_KEY to your .env file."
        return jsonify(out)
    try:
        cfg = public_config(force=True)  # the login page always shows the current InsForge settings
    except InsforgeError as e:
        out["error"] = friendly(e)
        return jsonify(out)
    out.update({
        "google": "google" in (cfg.get("oAuthProviders") or []),
        "verify_method": cfg.get("verifyEmailMethod") or "code",
        "reset_method": cfg.get("resetPasswordMethod") or "code",
        "require_verification": bool(cfg.get("requireEmailVerification")),
        "password": {"min_length": cfg.get("passwordMinLength") or 8, "number": bool(cfg.get("requireNumber")),
                     "lowercase": bool(cfg.get("requireLowercase")), "uppercase": bool(cfg.get("requireUppercase")),
                     "special": bool(cfg.get("requireSpecialChar"))},
    })
    return jsonify(out)


@bp.get("/me")
def me():
    if not g.user:
        return jsonify({"error": "Not signed in.", "auth_required": True}), 401
    return jsonify(public_user(g.user))


@bp.post("/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})


@bp.post("/register")
def register():
    data = body()
    name = " ".join(str(data.get("name") or "").split())
    email = clean_email(data.get("email"))
    password = str(data.get("password") or "")
    if not 2 <= len(name) <= 60:
        return fail(400, "Name must be 2-60 characters.", field="name")
    if not EMAIL_RE.match(email) or len(email) > 254:
        return fail(400, "Please enter a valid email address.", field="email")
    if not password or len(password) > 128:
        return fail(400, "Please enter a password (max. 128 characters).", field="password")

    def go():
        cfg = public_config()
        method = cfg.get("verifyEmailMethod") or "code"
        problem = password_problem(password, cfg)
        if problem:
            return fail(400, problem, field="password")
        payload = {"email": email, "password": password, "name": name}
        if cfg.get("requireEmailVerification") and method == "link":
            payload["redirectTo"] = app_url() + "/login"
        result = call("POST", "/api/auth/users", params={"client_type": "server"}, json=payload)
        if result.get("requireEmailVerification") or not result.get("accessToken"):
            return jsonify({"verify": True, "email": email, "method": method})
        return jsonify(sign_in(result)), 201
    return run("register", go)


@bp.post("/login")
def login():
    data = body()
    email = clean_email(data.get("email"))
    password = str(data.get("password") or "")
    key = (request.remote_addr, email)
    if throttled(key):
        return fail(429, "Too many attempts. Please try again in a few minutes.")
    if not EMAIL_RE.match(email) or not password:
        return fail(400, "Please enter your email and password.")

    def go():
        try:
            result = call("POST", "/api/auth/sessions", params={"client_type": "server"},
                          json={"method": "password", "email": email, "password": password})
        except InsforgeError as e:
            if e.status in (400, 401):
                _fails[key].append(time.time())
            if e.status == 403 and "verif" in (e.message or "").lower():
                return fail(403, "Please verify your email first.", verify=True, email=email)
            raise
        _fails.pop(key, None)
        return jsonify(sign_in(result, remember=bool(data.get("remember", True))))
    return run("login", go)


@bp.post("/verify")
def verify():
    data = body()
    email, code = clean_email(data.get("email")), str(data.get("code") or "").strip()
    key = (request.remote_addr, email)
    if throttled(key):
        return fail(429, "Too many attempts. Please try again in a few minutes.")
    if not EMAIL_RE.match(email) or not CODE_RE.match(code):
        return fail(400, "Enter the 6-digit code from your email.", field="code")

    def go():
        try:
            result = call("POST", "/api/auth/email/verify", params={"client_type": "server"},
                          json={"email": email, "otp": code})
        except InsforgeError as e:
            if e.status in (400, 401, 404):
                _fails[key].append(time.time())
            raise
        _fails.pop(key, None)
        return jsonify(sign_in(result))
    return run("verify", go)


@bp.post("/resend")
def resend():
    email = clean_email(body().get("email"))
    if not EMAIL_RE.match(email):
        return fail(400, "Please enter a valid email address.", field="email")

    def go():
        cfg = public_config()
        payload = {"email": email}
        if (cfg.get("verifyEmailMethod") or "code") == "link":
            payload["redirectTo"] = app_url() + "/login"
        call("POST", "/api/auth/email/send-verification", json=payload)
        return jsonify({"ok": True, "method": cfg.get("verifyEmailMethod") or "code"})
    return run("resend", go)


@bp.post("/forgot")
def forgot():
    email = clean_email(body().get("email"))
    if not EMAIL_RE.match(email):
        return fail(400, "Please enter a valid email address.", field="email")

    def go():
        cfg = public_config()
        method = cfg.get("resetPasswordMethod") or "code"
        payload = {"email": email}
        if method == "link":
            payload["redirectTo"] = app_url() + "/login"
        call("POST", "/api/auth/email/send-reset-password", json=payload)
        return jsonify({"ok": True, "method": method})  # InsForge answers the same whether or not the email exists
    return run("forgot", go)


@bp.post("/reset")
def reset():
    data = body()
    email, code = clean_email(data.get("email")), str(data.get("code") or "").strip()
    token, password = str(data.get("token") or "").strip(), str(data.get("password") or "")
    if not password or len(password) > 128:
        return fail(400, "Please enter a new password.", field="password")
    if not token and not (EMAIL_RE.match(email) and CODE_RE.match(code)):
        return fail(400, "Enter the 6-digit code from your email.", field="code")

    def go():
        problem = password_problem(password, public_config())
        if problem:  # checked first, so a weak password never burns the one-time code
            return fail(400, problem, field="password")
        reset_token = token
        if not reset_token:  # "code" method: swap the 6-digit code for a reset token first
            try:
                reset_token = call("POST", "/api/auth/email/exchange-reset-password-token",
                                   json={"email": email, "code": code}).get("token")
            except InsforgeError as e:
                if e.status in (400, 401, 404):
                    return fail(400, "That code is invalid or has expired.", field="code")
                raise
            if not reset_token:
                return fail(400, "That code is invalid or has expired.", field="code")
        try:
            call("POST", "/api/auth/email/reset-password", json={"newPassword": password, "otp": reset_token})
        except InsforgeError as e:
            if e.status in (400, 401, 404) and token:
                return fail(400, "This reset link is invalid or has expired. Please request a new one.")
            raise
        return jsonify({"ok": True})
    return run("reset", go)


# --------------------------------------------------------------------------- #
# Google sign-in (browser redirects, OAuth 2.0 + PKCE handled server-side)
# --------------------------------------------------------------------------- #
def b64url(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def flash_and_login(message):
    session["flash"] = message
    return redirect("/login")


@pages.get("/auth/google")
def google_start():
    if g.user:
        return redirect("/")
    verifier = b64url(secrets.token_bytes(32))  # 43 chars, as PKCE requires
    challenge = b64url(hashlib.sha256(verifier.encode()).digest())
    try:
        data = call("GET", "/api/auth/oauth/google", params={
            "redirect_uri": app_url() + "/auth/callback", "code_challenge": challenge, "prompt": "select_account"})
    except InsforgeError as e:
        return flash_and_login(friendly(e, "oauth"))
    auth_url = str(data.get("authUrl") or "")
    if not auth_url.startswith(("https://", "http://")):
        return flash_and_login("Google sign-in is not set up in InsForge yet (Authentication > Auth Methods > Google).")
    session["oauth_verifier"] = verifier  # only this browser can finish the flow it started
    return redirect(auth_url)


@pages.get("/auth/callback")
def google_callback():
    verifier = session.pop("oauth_verifier", None)
    code = request.args.get("insforge_code")
    if request.args.get("error") or request.args.get("insforge_error") or not code:
        return flash_and_login("Google sign-in was cancelled or did not finish. Please try again.")
    if not verifier:
        return flash_and_login("Your sign-in session expired. Please try again.")
    try:
        result = call("POST", "/api/auth/oauth/exchange", params={"client_type": "server"},
                      json={"code": code, "code_verifier": verifier})
        sign_in(result)
    except InsforgeError as e:
        return flash_and_login(friendly(e, "oauth-exchange"))
    except AuthRefused as e:
        return flash_and_login(e.message)
    return redirect("/")
