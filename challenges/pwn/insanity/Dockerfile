FROM debian:bookworm-slim

# socat is the per-connection listener. The challenge binary is the exact
# handout players download (files/chall), compiled from src/chall.c.
RUN apt-get update \
    && apt-get install -y --no-install-recommends socat \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 ctf

WORKDIR /app

COPY files/chall /app/chall
COPY src/entrypoint.sh /app/entrypoint.sh

RUN chmod 0755 /app/chall /app/entrypoint.sh \
    && chown -R ctf:ctf /app

USER ctf

EXPOSE 1337

ENTRYPOINT ["/app/entrypoint.sh"]
