FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp

# iputils-ping is the only tool added on top of the base image.
RUN apt-get update \
    && apt-get install -y --no-install-recommends iputils-ping \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir flask==3.0.3 gunicorn==22.0.0

COPY src/ /app/

# The app code stays ROOT-owned and read-only for uid 10001, so injected
# commands cannot deface app.py or the templates. uid 10001 is only the
# identity the entrypoint drops to (setpriv); there is deliberately no USER
# line, because the entrypoint needs root to write the flag file.
# /flag.txt is a root-owned symlink to /tmp/flag.txt (the compose root
# filesystem is read-only, /tmp is writable).
RUN useradd --no-create-home --uid 10001 appuser \
    && chmod -R go-w /app \
    && chmod 0755 /app/entrypoint.sh \
    && ln -s /tmp/flag.txt /flag.txt

EXPOSE 8080

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--access-logfile", "-", "app:app"]