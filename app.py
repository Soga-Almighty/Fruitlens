import base64
import csv
import io
import json
import os
import re
import threading
import uuid
from pathlib import Path

import importlib
import importlib.util

# TF >= 2.16 ships Keras 3, which struggles with old Teachable Machine .h5 files; the legacy Keras 2 lives in
# the optional "tf_keras" package. Only switch to it when it is installed: on TF 2.15 (requirements.txt)
# this flag would otherwise make `import tensorflow.keras` fail.
if importlib.util.find_spec("tf_keras"):
    os.environ.setdefault("TF_USE_LEGACY_KERAS", "1")

import numpy as np
from PIL import Image, ImageOps
from flask import Flask, Response, abort, g, jsonify, redirect, request, send_from_directory
from werkzeug.middleware.proxy_fix import ProxyFix

import auth
import db
import insforge
import store

BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"
UPLOAD_DIR = db.UPLOAD_DIR
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
HTML_FILE = "fruit lens2.html"

FRUITS = ["banana", "orange", "papaya", "rambutan", "tomato"]
CONDITION_ORDER = ["Unripe", "Ripe", "Rotten"]
LOW_CONFIDENCE = 60.0  # below this the UI asks the user to retake the photo

# auto   = use the small TensorFlow Lite model (model.tflite) when there is one, otherwise the Keras .h5 model
# tflite = only TensorFlow Lite (servers: fails loudly instead of quietly needing TensorFlow)
# keras  = always the original .h5 model (needs TensorFlow)
MODEL_BACKEND = os.environ.get("MODEL_BACKEND", "auto").strip().lower()
MODEL_CACHE = {}
MODEL_LOCK = threading.Lock()
PREDICT_LOCK = threading.Lock()  # one prediction at a time: bounded memory, no thread-safety surprises

app = Flask(__name__)
if os.environ.get("TRUST_PROXY") == "1":  # behind Railway / Caddy / Nginx: use the real scheme, host and client IP
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024
auth.init_auth(app)


@app.errorhandler(store.AuthExpired)
def session_expired(_error):
    return jsonify({"error": "Your session has expired. Please sign in again.", "auth_required": True}), 401


@app.errorhandler(413)
def too_large(_error):
    return jsonify({"error": "That photo is too large (maximum 12 MB). Try again or choose a smaller photo."}), 413


@app.errorhandler(insforge.InsforgeError)
def insforge_failed(error):
    return jsonify({"error": insforge.friendly(error)}), (error.status if 400 <= error.status < 600 else 502)


# --------------------------------------------------------------------------- #
# Model loading & prediction
# --------------------------------------------------------------------------- #
def find_tflite_interpreter():
    """The smallest TensorFlow Lite runtime that is installed: ai-edge-litert, tflite-runtime or TensorFlow itself."""
    for package, module in (("ai_edge_litert", "ai_edge_litert.interpreter"), ("tflite_runtime", "tflite_runtime.interpreter")):
        if importlib.util.find_spec(package):
            try:
                return importlib.import_module(module).Interpreter
            except ImportError:
                continue
    if importlib.util.find_spec("tensorflow"):
        import tensorflow as tf
        return tf.lite.Interpreter
    return None


class TFLiteModel:
    """model.tflite read by the TensorFlow Lite runtime: same predictions, a fraction of the memory."""
    backend = "tflite"

    def __init__(self, path, interpreter_class):
        self.interpreter = interpreter_class(model_path=str(path), num_threads=1)
        self.interpreter.allocate_tensors()
        self.input = self.interpreter.get_input_details()[0]
        self.output = self.interpreter.get_output_details()[0]
        self.input_shape = tuple(int(n) for n in self.input["shape"])

    def predict(self, batch):
        self.interpreter.set_tensor(self.input["index"], batch.astype(self.input["dtype"]))
        self.interpreter.invoke()
        return self.interpreter.get_tensor(self.output["index"]).copy()


class KerasModel:
    """The original Teachable Machine .h5 model (needs the full TensorFlow)."""
    backend = "keras"

    def __init__(self, path):
        try:
            if importlib.util.find_spec("tf_keras"):  # TF >= 2.16 ships Keras 3; tf_keras keeps the legacy loader
                import tf_keras as keras
            else:  # TF 2.15 (see requirements.txt)
                from tensorflow import keras
        except ImportError:
            raise RuntimeError("TensorFlow is not installed, so the .h5 model cannot be used. Create the small "
                               ".tflite models with `python tools/convert_models.py`, or install tensorflow==2.15.1.")

        class CompatibleDepthwiseConv2D(keras.layers.DepthwiseConv2D):
            def __init__(self, *args, groups=1, **kwargs):
                # Old Teachable Machine exports store groups=1, which newer Keras rejects.
                super().__init__(*args, **kwargs)

        self.model = keras.models.load_model(str(path), compile=False,
                                             custom_objects={"DepthwiseConv2D": CompatibleDepthwiseConv2D})
        shape = self.model.input_shape
        self.input_shape = tuple(shape[0] if isinstance(shape, list) else shape)

    def predict(self, batch):
        output = self.model.predict(batch, verbose=0)
        return output[0] if isinstance(output, list) else output


def softmax(values):
    e = np.exp(values - np.max(values))
    return e / e.sum()


def read_labels(path):
    if not path.exists():
        return []
    lines = [l.strip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    return [re.sub(r"^\s*\d+\s*[:.)-]?\s*", "", l) for l in lines]


def load_model_data(fruit):
    with MODEL_LOCK:
        if fruit in MODEL_CACHE:
            return MODEL_CACHE[fruit]
        folder = MODELS_DIR / f"{fruit}_model"
        tflite_path, h5_path = folder / "model.tflite", folder / "keras_model.h5"
        model = None
        if MODEL_BACKEND in ("auto", "tflite") and tflite_path.exists():
            interpreter_class = find_tflite_interpreter()
            if interpreter_class:
                model = TFLiteModel(tflite_path, interpreter_class)
                if h5_path.exists() and h5_path.stat().st_mtime > tflite_path.stat().st_mtime + 2:
                    app.logger.warning("%s is newer than %s: the old TFLite model is still in use. "
                                       "Run `python tools/convert_models.py` after retraining a model.", h5_path.name, tflite_path)
            elif MODEL_BACKEND == "tflite":
                raise RuntimeError("No TensorFlow Lite runtime is installed. Run: pip install ai-edge-litert")
        if model is None:
            if MODEL_BACKEND == "tflite" or not h5_path.exists():
                raise FileNotFoundError(f"Model file not found: {tflite_path if MODEL_BACKEND == 'tflite' else h5_path}"
                                        " (create the .tflite files with: python tools/convert_models.py)")
            model = KerasModel(h5_path)
        MODEL_CACHE[fruit] = {"model": model, "labels": read_labels(folder / "labels.txt")}
        return MODEL_CACHE[fruit]


def warm_up():
    """Load every model once so the first scan is fast. Problems are logged; /api/test-models shows details."""
    for fruit in FRUITS:
        try:
            load_model_data(fruit)
        except Exception:
            app.logger.exception("Could not preload the %s model", fruit)


def prepare_image(image, shape):
    height, width = int(shape[1] or 224), int(shape[2] or 224)
    # Same preprocessing as the Teachable Machine export: centre-crop, no distortion.
    image = ImageOps.fit(image.convert("RGB"), (width, height), Image.Resampling.LANCZOS)
    pixels = np.asarray(image, dtype=np.float32) / 127.5 - 1.0
    return np.expand_dims(pixels, axis=0)


def get_condition(label):
    text = label.lower()
    if re.search(r"rotten|spoil|mou?ld|busuk|\bbad\b", text):
        return "Rotten"
    if re.search(r"unripe|\braw\b|green|immature|mentah|belum", text):
        return "Unripe"
    return "Ripe"


def predict_probabilities(fruit, image):
    data = load_model_data(fruit)
    with PREDICT_LOCK:
        output = data["model"].predict(prepare_image(image, data["model"].input_shape))
    probs = np.asarray(output).reshape(-1).astype(np.float32)
    if not np.all(np.isfinite(probs)):
        raise ValueError("The model returned invalid values.")
    if np.any(probs < 0) or not np.isclose(probs.sum(), 1.0, atol=0.05):
        probs = softmax(probs)
    return data["labels"], probs


# --------------------------------------------------------------------------- #
# Scan persistence (the data lives in the InsForge database, see store.py; photos stay on this server)
# --------------------------------------------------------------------------- #
def save_thumbnail(image, user_id=None):
    """Small JPEG stored as a data: URL inside the scan row itself (InsForge database).

    Keeping the photo with the scan means it survives restarts and redeploys; a file on the server's disk is wiped
    on hosts without a persistent volume (e.g. Railway), which left the history without pictures.
    """
    thumb = image.convert("RGB")
    thumb.thumbnail((256, 256))
    buf = io.BytesIO()
    thumb.save(buf, "JPEG", quality=72, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def scan_payload(scan):
    """Join a scan row with the fruit guide and condition info (same JSON the web page has always received)."""
    guide = store.fruit(scan["fruit"]) or {}
    info = store.condition(scan["fruit"], scan["condition"]) or {}
    scan = dict(scan)
    probabilities = scan.get("probabilities") or []
    scan["probabilities"] = json.loads(probabilities) if isinstance(probabilities, str) else probabilities
    image = scan.get("image_file")
    if image and image.startswith("data:image/"):
        scan["image_url"] = image  # new scans: the picture is part of the row
    elif image:
        scan["image_url"] = f"/uploads/{scan['user_id']}/{image}"  # older scans: file on the server's disk
    else:
        scan["image_url"] = None
    scan.pop("image_file", None)  # the picture is already in image_url; do not send it twice
    scan["fruit_name"] = guide.get("name", scan["fruit"].title())
    scan["low_confidence"] = (scan.get("confidence") or 0) < LOW_CONFIDENCE
    scan["fruit_info"] = guide
    scan["info"] = info
    return scan


def predict_and_save(user_id, fruit, image):
    labels, probs = predict_probabilities(fruit, image)
    base = {name: row["base_freshness"] for name, row in store.reference()["conditions"].get(fruit, {}).items()}

    breakdown = []
    for i, p in enumerate(probs):
        label = labels[i] if i < len(labels) else f"class_{i}"
        breakdown.append({"label": label, "condition": get_condition(label),
                          "probability": round(float(p) * 100, 2)})

    top = int(np.argmax(probs))
    condition = breakdown[top]["condition"]
    # Freshness index = model probabilities weighted by each condition's base score.
    freshness = round(sum(float(p) * base.get(b["condition"], 0) for p, b in zip(probs, breakdown)))
    stage = (store.condition(fruit, condition) or {}).get("stage", 2)

    photo = save_thumbnail(image, user_id)
    row = store.add_scan({"user_id": user_id, "fruit": fruit, "label": breakdown[top]["label"],
                          "condition": condition, "confidence": round(float(probs[top]) * 100, 2),
                          "freshness": freshness, "stage": stage, "probabilities": breakdown, "image_file": photo})
    return scan_payload(row)


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #
@app.get("/")
def home():
    if not g.user:
        return redirect("/login")
    return send_from_directory(str(BASE_DIR), HTML_FILE)


@app.get("/sw.js")
def service_worker():
    # The service worker must be served from the site root so it can control every page (scope "/").
    resp = send_from_directory(str(BASE_DIR / "static"), "sw.js", mimetype="application/javascript")
    resp.headers["Cache-Control"] = "no-cache"  # browsers must re-check it, otherwise updates never reach phones
    resp.headers["Service-Worker-Allowed"] = "/"
    return resp


@app.get("/offline.html")
def offline_page():
    return send_from_directory(str(BASE_DIR / "static"), "offline.html")


@app.get("/manifest.webmanifest")
def web_manifest():
    resp = send_from_directory(str(BASE_DIR / "static"), "manifest.webmanifest", mimetype="application/manifest+json")
    resp.headers["Cache-Control"] = "no-cache"
    return resp


@app.get("/login")
def login_page():
    if g.user:
        return redirect("/")
    return send_from_directory(str(BASE_DIR), "login.html")


@app.get("/uploads/<user_id>/<path:name>")
def uploads(user_id, name):
    # Scan photos are private: only the account that took the scan may open the file.
    if not g.user or g.user["id"] != user_id:
        abort(404)
    return send_from_directory(str(UPLOAD_DIR / user_id), name)


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/api/predict")
def predict():
    uploaded = request.files.get("image")
    fruit = request.form.get("fruit", "").strip().lower()

    if not uploaded or not uploaded.filename:
        return jsonify({"error": "No image selected."}), 400
    if fruit not in FRUITS:
        return jsonify({"error": "Please choose a valid fruit type.",
                        "available_fruits": FRUITS}), 400
    try:
        image = ImageOps.exif_transpose(Image.open(uploaded.stream)).convert("RGB")
    except Exception:
        return jsonify({"error": "That file is not a valid image."}), 400

    try:
        return jsonify(predict_and_save(g.user["id"], fruit, image))
    except (store.AuthExpired, insforge.InsforgeError):
        raise  # not a model problem: handled by the error handlers above
    except Exception as error:
        app.logger.exception("Prediction for %s failed", fruit)
        return jsonify({"error": f"The {fruit} model could not process this image: {error}"}), 500


@app.get("/api/fruits")
def fruits():
    counts = store.stats()["by_fruit"]
    return jsonify([{**f, "scan_count": counts.get(f["slug"], 0)} for f in store.fruits()])


@app.get("/api/fruits/<slug>")
def fruit_detail(slug):
    guide = store.fruit(slug)
    if not guide:
        return jsonify({"error": "Fruit not found."}), 404
    recent = [scan_payload(s) for s in store.recent_scans(slug, 5)]
    counts = store.stats()["by_fruit_condition"].get(slug, {})
    return jsonify({**guide, "conditions": store.conditions_for(slug), "recent_scans": recent, "counts": counts})


def scan_filters():
    fruit = request.args.get("fruit")
    condition = request.args.get("condition")
    return (fruit if fruit in FRUITS else None, condition if condition in CONDITION_ORDER else None,
            request.args.get("q", ""))


@app.get("/api/scans")
def list_scans():
    limit = min(max(request.args.get("limit", 100, type=int), 1), 500)
    return jsonify([scan_payload(s) for s in store.list_scans(*scan_filters(), limit=limit)])


@app.get("/api/scans/export.csv")
def export_scans():
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["id", "timestamp", "fruit", "condition", "confidence_pct", "freshness_pct"])
    for s in store.export_scans(*scan_filters()):
        writer.writerow([s["id"], s["created_at"], s["fruit"], s["condition"], s["confidence"], s["freshness"]])
    return Response(out.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=fruit_lens_log.csv"})


@app.get("/api/scans/<int:scan_id>")
def get_scan(scan_id):
    scan = store.get_scan(scan_id)
    if not scan:
        return jsonify({"error": "Scan not found."}), 404
    return jsonify(scan_payload(scan))


@app.get("/api/restore-photos")
def restore_photos():
    """One-time repair: copy old photo files found in THIS computer's uploads/ folder into the signed-in user's scans.

    Scans made on a computer whose photos never reached the server show an empty picture. Run the app on that
    computer, sign in, and open /api/restore-photos once. It is safe to repeat: scans that already have their
    picture inside the row are skipped.
    """
    files = {p.name: p for p in UPLOAD_DIR.rglob("*") if p.is_file()}
    restored = no_file = already = 0
    errors = []
    for row in store.list_scans(limit=1000, columns="id,image_file"):
        name = row.get("image_file")
        if not name or name.startswith("data:"):
            already += 1
            continue
        path = files.get(name)
        if not path:
            no_file += 1
            continue
        try:
            with Image.open(path) as im:
                data = save_thumbnail(ImageOps.exif_transpose(im))
            store.set_scan_image(row["id"], data)
            restored += 1
        except Exception as e:  # keep going: one bad file must not stop the rest
            errors.append(f"scan {row['id']}: {e}")
    return jsonify({"restored": restored, "already_ok_or_no_photo": already, "photo_not_on_this_computer": no_file,
                    "errors": errors[:5]})


@app.delete("/api/scans/<int:scan_id>")
def delete_scan(scan_id):
    scan = store.delete_scan(scan_id)
    if not scan:
        return jsonify({"error": "Scan not found."}), 404
    image = scan.get("image_file")
    if image and not image.startswith("data:"):  # old-style photo file on the disk; new ones go away with the row
        (UPLOAD_DIR / g.user["id"] / image).unlink(missing_ok=True)
    return jsonify({"deleted": scan_id})


@app.get("/api/stats")
def stats():
    numbers = store.stats()
    return jsonify({k: numbers[k] for k in ("total", "avg_freshness", "by_condition", "by_fruit", "this_week", "last_week")})


@app.get("/api/recommendations")
def recommendations():
    """Personalised alerts from each fruit's latest scan in the last 14 days + general tips."""
    seen, latest = set(), []
    for s in store.scans_since(14):  # newest first, so the first one per fruit is its latest scan
        if s["fruit"] not in seen:
            seen.add(s["fruit"])
            latest.append(s)
    latest.sort(key=lambda s: s["id"], reverse=True)
    alerts = []
    for s in latest:
        p = scan_payload(s)
        name, info = p["fruit_name"], p["info"]
        if s["condition"] == "Rotten":
            alerts.append({"title": f"Discard your {name}", "priority": "Act Now", "icon": "trash-2",
                           "body": info.get("storage", ""), "scan_id": s["id"]})
        elif s["condition"] == "Ripe":
            alerts.append({"title": f"Eat your {name} soon", "priority": "Eat Soon", "icon": "clock",
                           "body": f"Latest scan: ripe, about {info.get('spoil_time')} left. {info.get('consume', '')}",
                           "scan_id": s["id"]})
        else:
            alerts.append({"title": f"Your {name} is still maturing", "priority": "Wait", "icon": "hourglass",
                           "body": f"Estimated {info.get('ripen_time')} to ripen. {info.get('storage', '')}",
                           "scan_id": s["id"]})
    tips = [{k: t.get(k) for k in ("title", "body", "priority", "icon")} for t in store.tips()]
    return jsonify({"alerts": alerts, "tips": tips})


@app.get("/api/test-models")
def test_models():
    results = {}
    for fruit in FRUITS:
        try:
            data = load_model_data(fruit)
            results[fruit] = {"status": "ok", "backend": data["model"].backend,
                              "input_shape": str(data["model"].input_shape), "labels": data["labels"]}
        except Exception as error:
            results[fruit] = {"status": "failed", "error": str(error)}
    return jsonify(results)


if __name__ == "__main__":
    import socket
    import sys

    host, port = os.environ.get("HOST", "127.0.0.1"), int(os.environ.get("PORT", 5000))
    with socket.socket() as probe:  # fail early and clearly instead of crashing while models are loading
        if probe.connect_ex(("127.0.0.1" if host == "0.0.0.0" else host, port)) == 0:
            sys.exit(f"\nPort {port} is already in use (maybe Fruit Lens is already running in another window).\n"
                     f"Close that program, or add PORT=5001 to your .env file and run again.\n")
    # Warm up models in the background so the first scan is not slow.
    threading.Thread(target=warm_up, daemon=True).start()
    app.run(host=host, port=port,
            debug=os.environ.get("FLASK_DEBUG") == "1", use_reloader=False)
