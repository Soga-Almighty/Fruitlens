FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MODEL_BACKEND=tflite \
    TRUST_PROXY=1 \
    DATA_DIR=/data \
    PORT=8000

WORKDIR /app
COPY requirements-docker.txt .
RUN pip install -r requirements-docker.txt

COPY . .
RUN mkdir -p /data

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=180s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/api/health' % os.environ.get('PORT','8000'), timeout=5)"

CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:app"]
