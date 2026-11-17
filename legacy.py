"""One-time import of scans saved in the OLD local SQLite database (fruitlens.db) into the InsForge database.

It runs by itself when someone signs in whose (verified) e-mail matches an account in the old database, so
nobody loses their history. The old file is only read; the import is remembered in it so it never runs twice.
"""
import json
import logging
import shutil
import sqlite3
from datetime import datetime

import db
import store

log = logging.getLogger("fruitlens.legacy")
CHUNK = 100


def _iso(local_text):
    """Old rows stored local server time as 'YYYY-MM-DD HH:MM:SS'; InsForge wants a timestamp with a time zone."""
    try:
        return datetime.strptime(str(local_text)[:19], "%Y-%m-%d %H:%M:%S").astimezone().isoformat()
    except ValueError:
        return None


def import_scans(user, verified):
    """Returns the number of scans imported. Never raises: a failed import must not block signing in."""
    try:
        return _import(user, verified)
    except Exception:
        log.exception("Could not import the old scans of %s (they stay in fruitlens.db; it will retry at the next sign-in)",
                      user.get("email"))
        return 0


def _import(user, verified):
    path = db.DB_PATH
    if not verified or not path.exists():  # only the proven owner of an e-mail address gets its old history
        return 0
    con = sqlite3.connect(path, timeout=15)
    con.row_factory = sqlite3.Row
    try:
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        if not {"users", "scans"} <= tables:
            return 0
        con.execute("CREATE TABLE IF NOT EXISTS legacy_imported (email TEXT PRIMARY KEY, imported_at TEXT)")
        email = user["email"].strip().lower()
        if con.execute("SELECT 1 FROM legacy_imported WHERE email = ?", (email,)).fetchone():
            return 0
        owner = con.execute("SELECT id FROM users WHERE lower(email) = ?", (email,)).fetchone()
        if not owner:
            return 0

        old = con.execute("SELECT * FROM scans WHERE user_id = ? ORDER BY id", (owner["id"],)).fetchall()
        already = store.existing_legacy_ids()  # makes a retry after a half-finished import safe
        target_dir = db.UPLOAD_DIR / user["id"]
        target_dir.mkdir(parents=True, exist_ok=True)

        rows, moved = [], []
        for s in old:
            if s["id"] in already:
                continue
            image = s["image_file"]
            if image:
                source = db.UPLOAD_DIR / image
                if source.exists() and not (target_dir / image).exists():
                    shutil.copy2(source, target_dir / image)
                if source.exists():
                    moved.append(source)
            try:
                probabilities = json.loads(s["probabilities"] or "[]")
            except ValueError:
                probabilities = []
            rows.append({"user_id": user["id"], "fruit": s["fruit"], "label": s["label"], "condition": s["condition"],
                         "confidence": s["confidence"], "freshness": s["freshness"], "stage": s["stage"],
                         "probabilities": probabilities, "image_file": image, "legacy_id": s["id"],
                         **({"created_at": _iso(s["created_at"])} if _iso(s["created_at"]) else {})})
        for i in range(0, len(rows), CHUNK):
            store.add_scans(rows[i:i + CHUNK])

        con.execute("INSERT OR REPLACE INTO legacy_imported (email, imported_at) VALUES (?, datetime('now'))", (email,))
        con.commit()
        for source in moved:  # the photos now live in uploads/<user id>/
            source.unlink(missing_ok=True)
        log.info("Imported %d old scans for %s", len(rows), email)
        return len(rows)
    finally:
        con.close()
