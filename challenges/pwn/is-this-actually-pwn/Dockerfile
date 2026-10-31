FROM python:3.12-slim-bookworm

# crop_image binary needs ImageMagick 6 MagickWand
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagickwand-6.q16-6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir flask flask_sqlalchemy flask_login flask_bcrypt

RUN useradd -m -u 1000 app

COPY src/ /app/
RUN chown -R app:app /app

USER app
EXPOSE 5000

CMD ["python", "app.py"]
