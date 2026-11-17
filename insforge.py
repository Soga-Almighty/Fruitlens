"""Low-level client for InsForge's REST API, shared by the account code (auth.py) and the data code (store.py).

Everything goes through the Flask server ("backend for frontend"): the browser never sees an InsForge key.
"""
import base64
import json as jsonlib
import os
import re
import time

import requests

HTTP_TIMEOUT = 15
_cfg = {"at": 0.0, "data": None}  # cached /api/auth/public-config


def insforge_url():
    return os.environ.get("INSFORGE_URL", "").strip().rstrip("/")


def anon_key():
    return os.environ.get("INSFORGE_ANON_KEY", "").strip()


class InsforgeError(Exception):
    def __init__(self, status, message, code=None, next_actions=None):
        super().__init__(message)
        self.status, self.message, self.code, self.next_actions = status, message, code, next_actions


def call(method, path, *, json=None, params=None, token=None, headers=None, raw=False):
    """One call to InsForge. Always asks for client_type=server where it matters, so no browser cookies are involved.

    token: a user's access token (acts as that user, Row Level Security applies). Without it the anon key is sent.
    raw:   return the JSON body as it is (database calls return lists); otherwise always a dict.
    """
    base = insforge_url()
    if not base.startswith(("http://", "https://")):
        raise InsforgeError(503, "InsForge is not configured. Add INSFORGE_URL to your .env file (see README).")
    if anon_key().startswith("ik_"):
        raise InsforgeError(503, "INSFORGE_ANON_KEY contains the admin API Key (it starts with ik_). "
                                 "Use the Anon Key instead: InsForge dashboard > Connect > API Keys > Anon Key.")
    all_headers = {"Accept": "application/json"}
    if token:
        all_headers["Authorization"] = f"Bearer {token}"
    elif anon_key():
        all_headers["Authorization"] = f"Bearer {anon_key()}"
    all_headers.update(headers or {})
    try:
        resp = requests.request(method, base + path, json=json, params=params, headers=all_headers,
                                timeout=HTTP_TIMEOUT, allow_redirects=False)
    except requests.RequestException:
        raise InsforgeError(502, "Could not reach InsForge. Check INSFORGE_URL and your internet connection.")
    try:
        data = resp.json()
    except ValueError:
        data = None
    if resp.status_code >= 400:
        err = data if isinstance(data, dict) else {}
        raise InsforgeError(resp.status_code, err.get("message") or "", err.get("error") or err.get("code"),
                            err.get("nextActions"))
    if raw:
        return data if data is not None else []
    return data if isinstance(data, dict) else {}


def jwt_exp(token):
    """Expiry (unix seconds) written inside a JWT. Not a security check: InsForge verifies the signature."""
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return int(jsonlib.loads(base64.urlsafe_b64decode(payload)).get("exp") or 0)
    except Exception:
        return 0


def friendly(e, ctx=""):
    """Turn an InsForge error into a short English message for the user."""
    s, m = e.status, (e.message or "").strip()
    low = m.lower()
    if s in (502, 503):
        return m
    if "redirect" in low and "allowed" in low:
        return (f"{m}. In InsForge open Authentication > Auth Settings > Allowed Redirect URLs and add that address.")
    if ctx == "register" and s == 401:
        return "InsForge rejected the Anon Key. Check INSFORGE_ANON_KEY in your .env file."
    if s == 409:
        return "This email is already registered. Please sign in."
    if ctx == "login" and s in (400, 401):
        return "Incorrect email or password."
    if s == 403 and "verif" in low:
        return "Please verify your email first."
    if s == 403 and ("signup" in low or "sign-up" in low or "disabled" in low):
        return "New sign-ups are disabled for this project."
    if s == 429:
        return "Too many attempts. Please wait a few minutes and try again."
    if ctx == "verify" and s in (400, 401, 404):
        return "That code is invalid or has expired."
    if ctx == "oauth" and s >= 500:
        return "Google sign-in is not set up in InsForge yet (Authentication > Auth Methods > Google)."
    return m or f"InsForge returned an error (HTTP {s})."


def password_problem(pw, cfg):
    """Check a password against the rules set in InsForge (Auth Settings > Password); None when it is fine."""
    need = []
    if len(pw) < (cfg.get("passwordMinLength") or 8):
        need.append(f"at least {cfg.get('passwordMinLength') or 8} characters")
    if cfg.get("requireNumber") and not re.search(r"\d", pw):
        need.append("a number")
    if cfg.get("requireLowercase") and not re.search(r"[a-z]", pw):
        need.append("a lowercase letter")
    if cfg.get("requireUppercase") and not re.search(r"[A-Z]", pw):
        need.append("an uppercase letter")
    if cfg.get("requireSpecialChar") and not re.search(r"[^A-Za-z0-9]", pw):
        need.append("a special character")
    return ("Password needs " + ", ".join(need) + ".") if need else None


def public_config(force=False):
    """InsForge's public auth settings (verification method, password rules, enabled providers). Cached 60 s."""
    if not force and _cfg["data"] and time.time() - _cfg["at"] < 60:
        return _cfg["data"]
    data = call("GET", "/api/auth/public-config")
    _cfg.update(at=time.time(), data=data)
    return data
