FROM python:3.12-slim-bookworm

RUN apt-get update && \
    apt-get install -y --no-install-recommends socat && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir py_ecc==8.0.0 && \
    useradd ctf

WORKDIR /app
COPY src/ /app/
USER ctf
EXPOSE 13416

CMD ["sh", "-c", "exec socat -T300 TCP-LISTEN:13416,reuseaddr,fork EXEC:\"python3 -u chall.py\""]
