"""Fruit Lens built-in content + the OLD local SQLite database.

Since the InsForge database took over, this file is only used for (1) the built-in fruit guide content, which is the
fallback and the source of insforge_setup.sql, and (2) reading old scans from fruitlens.db so legacy.py can import them.
"""
import os
import sqlite3
from pathlib import Path

# Where the database, scan photos and the secret key live. On a server set the DATA_DIR environment variable
# to the persistent disk (e.g. /data); otherwise everything stays next to the code.
DATA_DIR = Path(os.environ.get("DATA_DIR") or Path(__file__).resolve().parent)
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "fruitlens.db"
UPLOAD_DIR = DATA_DIR / "uploads"  # scan photos (one sub-folder per user)

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    name TEXT NOT NULL,
    password_hash TEXT,            -- legacy, no longer used: InsForge owns passwords (always NULL now)
    google_sub TEXT UNIQUE,        -- legacy, no longer used
    insforge_id TEXT,              -- id of the account in InsForge (the real identity)
    avatar_url TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    last_login TEXT
);
CREATE TABLE IF NOT EXISTS fruits (
    slug TEXT PRIMARY KEY, name TEXT, scientific TEXT, category TEXT,
    description TEXT, image_url TEXT, ripen_duration TEXT,
    storage_temp TEXT, storage_place TEXT, ethylene TEXT
);
CREATE TABLE IF NOT EXISTS conditions (
    fruit TEXT, condition TEXT, freshness_label TEXT, base_freshness INTEGER,
    stage INTEGER, ripen_time TEXT, spoil_time TEXT,
    storage TEXT, consume TEXT, culinary TEXT,
    PRIMARY KEY (fruit, condition)
);
CREATE TABLE IF NOT EXISTS scans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    fruit TEXT NOT NULL, label TEXT, condition TEXT, confidence REAL,
    freshness INTEGER, stage INTEGER, probabilities TEXT, image_file TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_scans_created ON scans(created_at DESC);
CREATE TABLE IF NOT EXISTS tips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT, body TEXT, priority TEXT, icon TEXT
);
"""

U = "https://images.unsplash.com/"
FRUITS = [
    # slug, name, scientific, category, description, image, ripen, temp, place, ethylene
    ("banana", "Banana", "Musa acuminata", "Tropical",
     "High-potassium climacteric fruit. The peel shifts from green to yellow, then brown-spotted as starch turns to sugar.",
     U + "photo-1571771894821-ce9b6c11b08e?auto=format&fit=crop&q=80&w=400",
     "3-7 days", "13°C - 15°C", "Cool room, away from direct sun", "High ethylene producer"),
    ("tomato", "Tomato", "Solanum lycopersicum", "Fruit vegetable",
     "Rich in lycopene. Colour moves from green to deep red while the flesh softens; cold storage dulls flavour.",
     U + "photo-1592924357228-91a4daadcfea?auto=format&fit=crop&q=80&w=400",
     "2-5 days", "13°C - 18°C", "Counter, stem-side down", "Moderate ethylene producer"),
    ("papaya", "Papaya", "Carica papaya", "Tropical",
     "Tropical fruit with papain enzyme. Skin turns from green to yellow-orange and the flesh softens as it ripens.",
     U + "photo-1617112848923-cc2234396a8d?auto=format&fit=crop&q=80&w=400",
     "4-8 days", "20°C - 24°C (10°C - 13°C once ripe)", "Room temperature, fridge once ripe", "High ethylene producer"),
    ("rambutan", "Rambutan", "Nephelium lappaceum", "Tropical",
     "Hairy-shelled fruit that does not ripen after harvest. Spines turn from yellow-green to red; the skin browns fast.",
     U + "photo-1635830092719-0e3b5aedc364?auto=format&fit=crop&q=80&w=800",
     "Does not ripen after harvest", "10°C - 12°C", "Fridge, perforated bag", "Low ethylene producer"),
    ("orange", "Orange", "Citrus × sinensis", "Citrus",
     "Citrus rich in Vitamin C. Non-climacteric, so it will not sweeten after picking; a firm rind with even colour is best.",
     U + "photo-1611080626919-7cf5a9dbab5b?auto=format&fit=crop&q=80&w=400",
     "Does not ripen after harvest", "4°C - 8°C", "Cool ventilated area or fridge crisper", "Very low ethylene producer"),
]

ROTTEN = ("Decomposed surface", 10, 4, "Expired", "0 Days",
          "Isolate immediately so mould spores do not spread to nearby fruit.",
          "Do not eat. Discard if you see mould, slime, leaking juice or a fermented smell.",
          "Not suitable for cooking. Send to compost or organic waste.")

# per fruit: Unripe / Ripe rows (label, base_freshness, stage, ripen, spoil, storage, consume, culinary)
CONDITIONS = {
    "banana": {
        "Unripe": ("Green & starchy", 65, 1, "3-6 Days", "8-12 Days",
                   "Keep at room temperature. A paper bag or a ripe fruit nearby speeds ripening.",
                   "Wait until yellow with a few spots; green bananas are starchy.",
                   "Green bananas can be boiled or fried as a savoury side or chips."),
        "Ripe": ("Optimal peak freshness", 90, 2, "0 Days", "3-5 Days",
                 "Keep away from other ethylene-sensitive produce. Wrap the crown in foil to slow ripening.",
                 "Best eaten within 2-3 days for the ideal sugar and texture balance.",
                 "Great for snacking, smoothies, oatmeal or fried banana."),
    },
    "tomato": {
        "Unripe": ("Green & firm", 65, 1, "3-7 Days", "10-14 Days",
                   "Ripen at room temperature out of direct sun. Do not refrigerate: cold blocks ripening.",
                   "Wait until fully red and slightly soft for the best flavour.",
                   "Green tomatoes can be fried, pickled or made into green sambal."),
        "Ripe": ("Peak firm ripeness", 90, 2, "0 Days", "3-5 Days",
                 "Store stem-side down on the counter. Chill only to extend life, then warm up before eating.",
                 "Eat within 3-4 days, raw for the best flavour.",
                 "Ideal for salads, sandwiches, fresh sauces and sambal."),
    },
    "papaya": {
        "Unripe": ("Maturing phase", 65, 1, "3-5 Days", "8-10 Days",
                   "Keep at room temperature until about 70% of the skin is yellow. Avoid the fridge while green.",
                   "Wait for yellow-orange skin and a slight give before cutting for sweet flesh.",
                   "Green papaya works in savoury dishes such as urap, vegetable soup or som tum."),
        "Ripe": ("Optimal peak freshness", 90, 2, "0 Days", "2-4 Days",
                 "Move to the fridge to slow ripening and keep the flesh firm.",
                 "Eat within 2-3 days; ripe papaya bruises easily.",
                 "Fresh slices, fruit salad, smoothies or iced fruit desserts."),
    },
    "rambutan": {
        "Unripe": ("Immature (yellow-green)", 65, 1, "Won't ripen further", "3-5 Days",
                   "Rambutan does not ripen after picking. Keep cool in a perforated bag.",
                   "Likely sour or astringent; choose fully red fruit when possible.",
                   "Add to fruit salad or syrup to balance the sourness."),
        "Ripe": ("Peak freshness", 90, 2, "0 Days", "3-5 Days",
                 "Refrigerate in a perforated bag; the skin browns quickly at room temperature.",
                 "Eat within 2-3 days while the flesh is at its sweetest.",
                 "Eat fresh, serve chilled, or add to mixed fruit desserts."),
    },
    "orange": {
        "Unripe": ("Immature rind", 65, 1, "Won't ripen further", "1-2 Weeks",
                   "Oranges do not ripen after picking. Keep in a cool, ventilated place.",
                   "May taste sour. Rind colour alone is not a reliable maturity sign for every variety.",
                   "Juice with a little honey, or use zest and slices in marinades."),
        "Ripe": ("Optimal peak freshness", 90, 2, "0 Days", "1-2 Weeks",
                 "Keep in a cool ventilated place or the fridge crisper. Keep dry to avoid mould.",
                 "Eat or juice within 1-2 weeks for the best juiciness and Vitamin C.",
                 "Fresh segments, juice, dressings, or zest in baking."),
    },
}

TIPS = [
    ("Ethylene Gas Separation", "High Priority", "split",
     "Bananas, tomatoes and papayas release ethylene, which speeds up ripening of nearby produce. Store them apart from fruit you want to keep longer, such as oranges."),
    ("Refrigeration Timing", "Pro Tip", "refrigerator",
     "Do not refrigerate tomatoes or papayas while they are still green: chilling interrupts ripening. Once ripe, the fridge helps papaya and rambutan last longer."),
    ("Check Fruit Daily", "Habit", "calendar-check",
     "Inspect stored fruit every day. One rotting fruit can spread mould to the rest of the bowl."),
    ("Wash Just Before Eating", "Pro Tip", "droplets",
     "Moisture speeds up mould growth. Keep fruit dry in storage and rinse it right before eating."),
]


def connect():
    conn = sqlite3.connect(DB_PATH, timeout=15)  # wait instead of failing when another request is writing
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create tables and (re)seed the reference data. Scan history is never touched."""
    with connect() as conn:
        conn.executescript(SCHEMA)
        conn.execute("PRAGMA journal_mode = WAL")  # readers no longer block the writer (several web threads)
        # Databases created before accounts existed have no scans.user_id column.
        if "user_id" not in [r[1] for r in conn.execute("PRAGMA table_info(scans)")]:
            conn.execute("ALTER TABLE scans ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_scans_user ON scans(user_id, id DESC)")
        # Databases from before InsForge have no users.insforge_id column.
        if "insforge_id" not in [r[1] for r in conn.execute("PRAGMA table_info(users)")]:
            conn.execute("ALTER TABLE users ADD COLUMN insforge_id TEXT")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_insforge ON users(insforge_id)")
        # Passwords now live only in InsForge: drop any hash left over from the old local login.
        conn.execute("UPDATE users SET password_hash = NULL WHERE password_hash IS NOT NULL")
        conn.executemany("INSERT OR REPLACE INTO fruits VALUES (?,?,?,?,?,?,?,?,?,?)", FRUITS)
        for fruit, rows in CONDITIONS.items():
            for cond, r in rows.items():
                conn.execute("INSERT OR REPLACE INTO conditions VALUES (?,?,?,?,?,?,?,?,?,?)",
                             (fruit, cond, *r))
            conn.execute("INSERT OR REPLACE INTO conditions VALUES (?,?,?,?,?,?,?,?,?,?)",
                         (fruit, "Rotten", *ROTTEN))
        conn.execute("DELETE FROM tips")
        conn.executemany("INSERT INTO tips (title, priority, icon, body) VALUES (?,?,?,?)", TIPS)


def rows(sql, params=()):
    with connect() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def one(sql, params=()):
    with connect() as conn:
        r = conn.execute(sql, params).fetchone()
        return dict(r) if r else None
