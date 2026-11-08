FROM python:3.12-slim-bookworm

RUN apt-get update && \
    apt-get install -y --no-install-recommends socat && \
    rm -rf /var/lib/apt/lists/* && \
    useradd ctf

WORKDIR /app
COPY src/ /app/
USER ctf
EXPOSE 13417

CMD ["sh", "-c", "exec socat -T300 TCP-LISTEN:13417,reuseaddr,fork EXEC:\"python3 -u chall.py\""]
