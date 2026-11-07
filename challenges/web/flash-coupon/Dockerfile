FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp

WORKDIR /app

RUN pip install --no-cache-dir flask==3.0.3 gunicorn==22.0.0

COPY src/ /app/

# uid 10001 backs the image USER (the compose harness also pins it).
RUN useradd --no-create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8080

# One worker + many threads: the threaded worker is what lets the requests in
# /redeem interleave inside the vulnerable check-then-use window.
CMD ["gunicorn", \
     "--bind", "0.0.0.0:8080", \
     "--worker-class", "gthread", \
     "--workers", "1", \
     "--threads", "16", \
     "--access-logfile", "-", \
     "app:app"]
