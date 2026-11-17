# Fruit Lens

Fruit ripeness scanner: Flask + Teachable Machine models + SQLite, with user accounts
(email/password and Google Sign-In). Every user only sees their own scans.

## Requirements
- **Python 3.11, 64-bit.** TensorFlow 2.15.1 runs on Python 3.9-3.11 only: **3.12 / 3.13 / 3.14 will NOT work**
  (`No matching distribution found for tensorflow==2.15.1`).
- Windows only: Microsoft Visual C++ Redistributable 2015-2022 x64 (https://aka.ms/vs/17/release/vc_redist.x64.exe).
- About 3 GB free disk space and internet for the first install.
- Extract the zip to a short path such as `C:\FruitLens` (do not run it from inside the zip).

## Run
Requires **Python 3.10 or 3.11, 64-bit**. Python 3.12 or newer will NOT work (TensorFlow 2.15.1 does not support it).
Windows (use `py -3.11` if you have several Pythons installed):

    py -3.11 -m venv .venv
    .venv\Scripts\python -m pip install --upgrade pip
    .venv\Scripts\python -m pip install -r requirements.txt
    .venv\Scripts\python app.py

macOS / Linux: the same with `python3.11` and `.venv/bin/python`.
Then open **http://localhost:5000**. Next time you only need the last command.
(Calling `.venv\Scripts\python` directly means you never have to "activate" the environment.)

Port 5000 busy (macOS AirPlay uses it)? Put `PORT=5001` in a `.env` file and open `http://localhost:5001`.
The red TensorFlow lines about CUDA / cuDNN / TensorRT in the terminal are harmless.
Optional: `pip install opencv-python` is only needed for the webcam scripts in `models/`.

Your data lives in the **InsForge database** (see *Database* below). On first run only `uploads/` (scan photos) and
`instance/secret.key` are created next to the code.
You are sent to the login page first; the app itself is only available after signing in.

## Accounts (InsForge)
Accounts are handled by **InsForge** (https://insforge.dev): sign-up, passwords, e-mail verification,
password reset and "Continue with Google". Fruit Lens keeps scans in its own SQLite database, linked to the
InsForge account. Flask talks to InsForge on the server, so no key ever reaches the browser.

### One-time setup
1. Create a free account at https://insforge.dev, click **Create New Project** and wait a few seconds.
2. Open the project, click **Connect** (opens *Connect Project*), tab **API Keys**, and copy the **Project URL** and the
   **Anon Key** (usually starts with `anon_`; older projects: a long text starting with `eyJ`).
   Never use the "API Key" (starts with `ik_`): it is an admin key and the app refuses it.
3. `copy .env.example .env` (macOS/Linux: `cp`) and paste both values into `.env`.
4. In the InsForge dashboard open **Authentication > Auth Settings**:
   - **General > Allowed Redirect URLs**: add `http://localhost:5000/auth/callback` and `http://localhost:5000/login`
     (use your own address/port if different).
   - **Email Verification**: turn on **Require Email Verification** and choose method **Code**.
5. **Authentication > Auth Methods**: add **Google** and switch on **Shared Keys** (quick start, no Google Cloud needed).
   For production use your own Google OAuth client instead: in Google Cloud add the redirect URI
   `https://<your-project>.insforge.app/api/auth/oauth/google/callback`, then paste the Client ID and Secret into InsForge.
6. `python app.py`, open http://localhost:5000 and create an account.

Existing scans from before InsForge: sign up (or use Google) with the **same e-mail** as your old local account and
the old account and its scans are linked automatically (only once the e-mail is verified).

## Database (InsForge)
Scans, the fruit guide texts and the tips live in your InsForge project's PostgreSQL database, no local database file.
The app talks to it **as the signed-in user** (their own InsForge token), and Row Level Security makes every user see
only their own scans, even if the app had a bug. Scan photos still stay on this server (`uploads/<user id>/`).

One-time setup:
1. InsForge dashboard > **SQL Editor**, paste the whole file `insforge_setup.sql`, click **Run**.
   It creates the tables `scans`, `fruits`, `conditions`, `tips`, switches Row Level Security on, adds the
   `scan_stats()` function and fills the fruit guide. Safe to run again (it never deletes your scans or your edits).
2. Check in **Database > Tables** (4 tables, each with RLS on) and **Database > Policies**.
3. Restart the app, sign in again (old sessions have no database token), scan something and look at
   **Database > Tables > scans**.

Good to know:
- Edit the fruit guide texts right in **Database > Tables** (fruits / conditions / tips); the app picks changes up within 5 minutes.
- Old history: if `fruitlens.db` and the old `uploads/` photos are still in the data folder, each person's old scans are
  imported automatically the first time they sign in with the **same verified e-mail** as their old account.
- If the tables are missing the app says so (*"The InsForge database is not set up yet..."*) instead of failing silently.
- Sessions last 7 days (the length of InsForge's refresh token), then you sign in again.

## Deploy (put it on the internet)
The project ships with everything a server needs: `Dockerfile`, `gunicorn.conf.py`, `railway.json` (Railway),
`docker-compose.yml` + `Caddyfile` (your own VPS with automatic HTTPS).

Needs (with the small TensorFlow Lite models, see below): about **0.5 GB RAM** is enough (measured ~120 MB after
loading, ~155 MB under load), a **persistent disk** mounted at `/data` (scan photos; the data itself lives in InsForge) and **HTTPS**
(Google sign-in requires it). With the original TensorFlow instead, count on ~550-700 MB RAM and a 1.3 GB install.

Variables to set on the host (never put them in Git):

| Variable | Value |
|---|---|
| `INSFORGE_URL`, `INSFORGE_ANON_KEY` | same as in your `.env` |
| `SECRET_KEY` | long random text (`python -c "import secrets; print(secrets.token_hex(32))"`) |
| `DATA_DIR` | `/data` (already the default inside the Docker image) |
| `APP_URL` | `https://your-domain` (Railway: filled automatically from `RAILWAY_PUBLIC_DOMAIN`) |

Then in InsForge: **Authentication > Auth Settings > Allowed Redirect URLs**, add
`https://your-domain/auth/callback` and `https://your-domain/login`.

## Small and fast: TensorFlow Lite
The five models are also stored as `models/<fruit>_model/model.tflite` (made by `python tools/convert_models.py`).
The app uses them automatically and only needs the tiny TensorFlow Lite runtime instead of the whole TensorFlow:

| | TensorFlow + .h5 | TFLite runtime + .tflite |
|---|---|---|
| Python environment on disk | ~1.3 GB (your Windows `.venv`: ~2 GB) | ~180 MB |
| RAM of the running app | ~550-700 MB | ~120-155 MB |
| Predictions | original | identical (checked on 180 predictions: same class every time, max difference 0.003 percentage points) |

- Small local environment: `pip install -r requirements-lite.txt` (Python 3.10-3.12, no TensorFlow needed).
- Retrained a model in Teachable Machine? Replace its `keras_model.h5`/`labels.txt`, then run
  `python tools/convert_models.py` (needs TensorFlow) to refresh the `.tflite` files.
- `MODEL_BACKEND=keras` forces the original .h5 models (needs TensorFlow), `MODEL_BACKEND=tflite` allows only TFLite.

## Structure
- `tools/convert_models.py`   Converts the .h5 models to .tflite and checks the predictions are the same
- `app.py`     Flask API: predict, scan history, stats, fruit guides, recommendations, CSV export (all scoped to the logged-in user)
- `auth.py`    Accounts through InsForge: sign-up, sign-in, e-mail codes, password reset, Google (OAuth + PKCE), Flask sessions
- `store.py`   All data access through the InsForge database (as the user), token renewal, cached fruit guide
- `insforge.py` Small shared client for InsForge's REST API
- `legacy.py`  One-time import of old local scans (fruitlens.db) into InsForge
- `insforge_setup.sql`   Run once in InsForge's SQL Editor: tables, Row Level Security, scan_stats(), fruit guide
- `db.py`      Built-in fruit guide content (fallback + source of insforge_setup.sql) and the reader for the old local database
- `login.html` Sign in / Create account / verify code / forgot password page
- `fruit lens2.html`   Main single-page UI (requires login)
- `models/<fruit>_model/`   Teachable Machine `keras_model.h5` + `labels.txt`
- `.env`       Your InsForge URL + Anon Key (not shared; see `.env.example`)

## Security notes
- Passwords never touch this app's database: InsForge stores and checks them. Flask opens a signed HttpOnly cookie
  session (SameSite=Lax); state-changing requests also need an `X-Requested-With` header (CSRF defence).
- Google sign-in uses PKCE: the secret verifier stays in the browser's session cookie that started the flow.
- 8 wrong passwords/codes per 10 minutes lock that e-mail on this server; InsForge adds its own per-IP limits
  (shared by everyone behind one server, fine for a laptop or small demo).
- Scan data is protected by Row Level Security inside InsForge; scan photos are served only to the account that took them.
- Deploying publicly? Use HTTPS, set `COOKIE_SECURE=1` and `APP_URL`, add your real URLs to *Allowed Redirect URLs*.

## Add a new fruit
1. Put `keras_model.h5` and `labels.txt` in `models/<fruit>_model/`
2. Add the slug to `FRUITS` in `app.py`, and to `FRUITS` / `CONDITIONS` in `db.py`
3. Add an `<option>` to the fruit selects in the HTML
Labels must contain *ripe* / *unripe* / *rotten* words (English or Indonesian: matang / mentah / busuk).
