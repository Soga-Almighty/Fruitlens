"""Fruit Lens data, stored in the InsForge database (PostgreSQL behind PostgREST).

Every call is made AS THE SIGNED-IN USER: Flask sends that user's own InsForge access token, so the database's
Row Level Security guarantees a user can only ever read or change their own scans, even if this code had a bug.
The 15-minute access token is renewed automatically with the user's refresh token (kept in the signed session).

Tables (created by insforge_setup.sql): scans, fruits, conditions, tips. Function: scan_stats().
"""
import logging
import re
import threading
import time
from datetime import datetime, timedelta, timezone

from flask import g, session

import db
import insforge
from insforge import InsforgeError, call

log = logging.getLogger("fruitlens.store")

CONDITION_ORDER = ["Unripe", "Ripe", "Rotten"]
REF_TTL = 300  # seconds the fruit guide content is cached
REFRESH_MARGIN = 60  # renew the access token when it has less than this many seconds left
RECORDS = "/api/database/records"
RPC = "/api/database/rpc"
SETUP_HINT = ("The InsForge database is not set up yet. In InsForge open SQL Editor and run the file "
              "insforge_setup.sql (see README, section Database).")

_ref = {"at": 0.0, "data": None}
_ref_lock = threading.Lock()


class AuthExpired(Exception):
    """The user's InsForge session can no longer be renewed: they have to sign in again."""


# --------------------------------------------------------------------------- #
# Acting as the signed-in user
# --------------------------------------------------------------------------- #
def refresh_session():
    refresh_token = session.get("rt")
    if not refresh_token:
        raise AuthExpired()
    try:
        res = call("POST", "/api/auth/refresh", params={"client_type": "server"}, json={"refreshToken": refresh_token})
    except InsforgeError as e:
        if e.status in (400, 401, 403):
            session.clear()
            raise AuthExpired() from e
        raise
    if not res.get("accessToken"):
        session.clear()
        raise AuthExpired()
    session["at"] = res["accessToken"]
    session["at_exp"] = insforge.jwt_exp(res["accessToken"])
    if res.get("refreshToken"):  # InsForge hands out a rotated refresh token: keep the newest
        session["rt"] = res["refreshToken"]
    return session["at"]


def access_token():
    if session.get("at") and (session.get("at_exp") or 0) - time.time() > REFRESH_MARGIN:
        return session["at"]
    return refresh_session()


def _db(method, path, *, params=None, body=None, prefer=None):
    """One database call as the current user. Renews the token once if InsForge rejects it."""
    headers = {"Prefer": prefer} if prefer else None
    for attempt in (1, 2):
        token = access_token() if attempt == 1 else refresh_session()
        try:
            return call(method, path, params=params, json=body, token=token, headers=headers, raw=True)
        except InsforgeError as e:
            if e.status == 401:
                if attempt == 1:
                    continue
                session.clear()
                raise AuthExpired() from e
            low = (e.message or "").lower()
            if e.status == 404 or "schema cache" in low or "could not find the" in low or "does not exist" in low:
                raise InsforgeError(503, SETUP_HINT) from e
            raise


# --------------------------------------------------------------------------- #
# Fruit guide content (cached; falls back to the content built into db.py)
# --------------------------------------------------------------------------- #
def _build_reference(fruits, conditions, tips):
    by_slug = {f["slug"]: f for f in fruits}
    cond = {}
    for c in conditions:
        cond.setdefault(c["fruit"], {})[c["condition"]] = c
    return {"fruits": fruits, "by_slug": by_slug, "conditions": cond, "tips": tips}


def builtin_reference():
    keys = ("slug", "name", "scientific", "category", "description", "image_url", "ripen_duration",
            "storage_temp", "storage_place", "ethylene")
    fruits = sorted((dict(zip(keys, f)) for f in db.FRUITS), key=lambda f: f["name"])
    ckeys = ("freshness_label", "base_freshness", "stage", "ripen_time", "spoil_time", "storage", "consume", "culinary")
    conditions = []
    for fruit, by in db.CONDITIONS.items():
        for name in ("Unripe", "Ripe"):
            conditions.append({"fruit": fruit, "condition": name, **dict(zip(ckeys, by[name]))})
        conditions.append({"fruit": fruit, "condition": "Rotten", **dict(zip(ckeys, db.ROTTEN))})
    tips = [{"id": i + 1, "title": t[0], "priority": t[1], "icon": t[2], "body": t[3]} for i, t in enumerate(db.TIPS)]
    return _build_reference(fruits, conditions, tips)


def reference():
    now = time.time()
    with _ref_lock:
        if _ref["data"] and now - _ref["at"] < REF_TTL:
            return _ref["data"]
    try:
        fruits = _db("GET", f"{RECORDS}/fruits", params={"select": "*", "order": "name.asc", "limit": "1000"})
        conditions = _db("GET", f"{RECORDS}/conditions", params={"select": "*", "limit": "1000"})
        tips = _db("GET", f"{RECORDS}/tips", params={"select": "*", "order": "id.asc", "limit": "1000"})
        if not fruits or not conditions:
            raise ValueError("the fruit guide tables are empty")
        data, fresh_until = _build_reference(fruits, conditions, tips), now
    except AuthExpired:
        raise
    except Exception as error:  # tables missing / InsForge unreachable: keep the app usable with the built-in guide
        log.warning("Using the built-in fruit guide (%s)", error)
        data = _ref["data"] or builtin_reference()
        fresh_until = now - REF_TTL + 30  # try InsForge again in 30 seconds
    with _ref_lock:
        _ref.update(at=fresh_until, data=data)
    return data


def clear_reference_cache():
    with _ref_lock:
        _ref.update(at=0.0, data=None)


def fruits():
    return reference()["fruits"]


def fruit(slug):
    return reference()["by_slug"].get(slug)


def conditions_for(slug):
    rows = list(reference()["conditions"].get(slug, {}).values())
    return sorted(rows, key=lambda c: CONDITION_ORDER.index(c["condition"]) if c["condition"] in CONDITION_ORDER else 9)


def condition(slug, name):
    return reference()["conditions"].get(slug, {}).get(name)


def tips():
    return reference()["tips"]


# --------------------------------------------------------------------------- #
# Scans (Row Level Security limits every query below to the caller's own rows)
# --------------------------------------------------------------------------- #
_UNSAFE = re.compile(r"[^0-9A-Za-z \-_]")  # anything that has a special meaning inside a PostgREST filter


def scan_params(fruit_slug=None, condition_name=None, q=None):
    params = {}
    if fruit_slug:
        params["fruit"] = f"eq.{fruit_slug}"
    if condition_name:
        params["condition"] = f"eq.{condition_name}"
    term = _UNSAFE.sub("", q or "").strip().lower()[:50]
    if term:
        params["or"] = f"(fruit.ilike.*{term}*,condition.ilike.*{term}*,label.ilike.*{term}*)"
    return params


def add_scan(row):
    rows = _db("POST", f"{RECORDS}/scans", body=[row], prefer="return=representation")
    if not rows:
        raise InsforgeError(502, "InsForge did not return the saved scan.")
    return rows[0]


def add_scans(rows):
    return _db("POST", f"{RECORDS}/scans", body=rows, prefer="return=minimal")


def list_scans(fruit_slug=None, condition_name=None, q=None, limit=100, offset=0, columns="*"):
    params = {"select": columns, "order": "id.desc", "limit": str(min(max(int(limit), 1), 1000)),
              **scan_params(fruit_slug, condition_name, q)}
    if offset:
        params["offset"] = str(int(offset))
    return _db("GET", f"{RECORDS}/scans", params=params)


def get_scan(scan_id):
    rows = _db("GET", f"{RECORDS}/scans", params={"select": "*", "id": f"eq.{int(scan_id)}", "limit": "1"})
    return rows[0] if rows else None


def set_scan_image(scan_id, image_file):
    """Replace the photo of one of the caller's own scans (Row Level Security hides everybody else's rows)."""
    _db("PATCH", f"{RECORDS}/scans", params={"id": f"eq.{int(scan_id)}"}, body={"image_file": image_file},
        prefer="return=minimal")


def delete_scan(scan_id):
    """Delete one of the caller's own scans; returns the deleted row (or None when there was no such scan)."""
    row = get_scan(scan_id)  # also proves it is the caller's: RLS hides everybody else's rows
    if not row:
        return None
    _db("DELETE", f"{RECORDS}/scans", params={"id": f"eq.{int(scan_id)}"})
    return row


def recent_scans(fruit_slug, n=5):
    return list_scans(fruit_slug=fruit_slug, limit=n)


def scans_since(days=14, limit=500):
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return _db("GET", f"{RECORDS}/scans", params={"select": "*", "created_at": f"gte.{since}",
                                                  "order": "created_at.desc", "limit": str(limit)})


def export_scans(fruit_slug=None, condition_name=None, q=None, cap=10000):
    rows, offset = [], 0
    while offset < cap:
        page = list_scans(fruit_slug, condition_name, q, limit=1000, offset=offset,
                          columns="id,created_at,fruit,condition,confidence,freshness")  # no pictures in a CSV
        rows.extend(page)
        if len(page) < 1000:
            break
        offset += 1000
    return rows


def existing_legacy_ids():
    rows = _db("GET", f"{RECORDS}/scans", params={"select": "legacy_id", "legacy_id": "not.is.null", "limit": "1000"})
    return {r["legacy_id"] for r in rows}


def stats():
    """The dashboard numbers, counted inside the database by scan_stats() (only the caller's own scans)."""
    if "fl_stats" not in g:
        raw = _db("POST", f"{RPC}/scan_stats", body={}) or {}
        by_condition = {c: 0 for c in CONDITION_ORDER}
        by_condition.update(raw.get("by_condition") or {})
        g.fl_stats = {"total": raw.get("total") or 0, "avg_freshness": raw.get("avg_freshness"),
                      "by_condition": by_condition, "by_fruit": raw.get("by_fruit") or {},
                      "by_fruit_condition": raw.get("by_fruit_condition") or {},
                      "this_week": raw.get("this_week") or 0, "last_week": raw.get("last_week") or 0}
    return g.fl_stats
