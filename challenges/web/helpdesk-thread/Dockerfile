# Self-contained: python:3.12-slim + Flask + a non-root app user. The author's
# local base image (ingehack-web-base) is replaced inline because CI builds
# from this directory alone.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir Flask==3.1.0

RUN useradd --create-home --uid 10001 app

WORKDIR /app

COPY src/ /app/

USER app

EXPOSE 8080

CMD ["python", "app.py"]
