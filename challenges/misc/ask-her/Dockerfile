FROM python:3.12-slim-bookworm

# openssl is used by generate.py for AES-128-CBC record encryption.
RUN apt-get update \
    && apt-get install -y --no-install-recommends openssl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/ask-her

RUN useradd -m -u 1000 app \
    && mkdir -p /srv \
    && chown app:app /srv

COPY src/ /opt/ask-her/
RUN chmod 0755 /opt/ask-her/entrypoint.sh \
    && chown -R app:app /opt/ask-her

USER app
EXPOSE 5000

ENTRYPOINT ["/opt/ask-her/entrypoint.sh"]
