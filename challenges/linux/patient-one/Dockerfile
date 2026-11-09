FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server \
    krb5-kdc \
    krb5-admin-server \
    krb5-user \
    libpam-krb5 \
    ldb-tools \
    sudo \
    procps \
    cron \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy configuration files
COPY src/configs/krb5.conf /configs/krb5.conf
COPY src/configs/kdc.conf /configs/kdc.conf
COPY src/configs/sshd_config /etc/ssh/sshd_config
COPY src/configs/sudoers_esi /etc/sudoers_esi
COPY src/configs/sba-backup /usr/local/bin/sba-backup.src
COPY src/entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

EXPOSE 22

ENTRYPOINT ["/entrypoint.sh"]
