"""Gunicorn settings for running Fruit Lens on a server (used by the Dockerfile)."""
import os
import threading

bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
workers = 1        # ONE process: the 5 models (and their memory) are loaded once and shared by all threads
threads = 4        # several visitors can be served at the same time
timeout = 180      # a scan is quick, but the very first request may wait for the models to load
graceful_timeout = 30
accesslog = "-"
errorlog = "-"


def post_worker_init(worker):
    """Load the models in the background right after the worker starts, so visitors never wait for them."""
    import app
    threading.Thread(target=app.warm_up, daemon=True).start()
