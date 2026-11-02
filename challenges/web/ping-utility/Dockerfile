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

# uid 10001 backs the image USER. /flag.txt is a symlink to the writable /tmp
# because the local compose root filesystem is read-only; the entrypoint fills
# the target at startup from FLAG and then unsets it.
RUN useradd --no-create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app \
    && chmod +x /app/entrypoint.sh \
    && ln -s /tmp/flag.txt /flag.txt

USER appuser

EXPOSE 8080

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--access-logfile", "-", "app:app"]
