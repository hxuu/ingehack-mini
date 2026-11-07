FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=UTC \
    LANG=C.UTF-8

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      openssh-server \
      postgresql \
      postgresql-client \
      netcat-openbsd \
      libcap2-bin \
      nmap \
      iproute2 \
      util-linux \
      procps \
 && rm -rf /var/lib/apt/lists/* \
 && apt-get clean

# --- sshd ---------------------------------------------------------------------
RUN mkdir -p /var/run/sshd \
 && ssh-keygen -A \
 && sed -i -E 's/^#?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config \
 && sed -i -E 's/^#?PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config

# --- entry user ---------------------------------------------------------------
RUN useradd -m -s /bin/bash player \
 && echo 'player:player123' | chpasswd \
 && printf 'psql -h <??????????????> -U appuser -d appdb # pass: devpass123\n' \
      >> /home/player/.bash_history \
 && chown player:player /home/player/.bash_history

COPY docker/player_readme.txt /home/player/.README
COPY docker/sysadmin_note.txt /opt/escape/sysadmin_note.txt
COPY docker/entry-start.sh    /opt/escape/entry-start.sh
COPY docker/db-start.sh       /opt/escape/db-start.sh
COPY docker/entrypoint.sh     /entrypoint.sh

RUN chown player:player /home/player/.README \
 && chmod 755 /entrypoint.sh /opt/escape/*.sh \
 && chmod 644 /home/player/.README /opt/escape/sysadmin_note.txt \
 && mkdir -p /opt/escape

# --- postgres listens on the internal network (needed for the lateral hop) ----
RUN sed -i -E "s/^#?listen_addresses.*/listen_addresses = '*'/" \
      /etc/postgresql/14/main/postgresql.conf \
 && printf 'host all all 172.16.0.0/12 scram-sha-256\n' \
      >> /etc/postgresql/14/main/pg_hba.conf

EXPOSE 22

ENTRYPOINT ["/entrypoint.sh"]
