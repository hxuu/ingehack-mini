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
 && sed -i -E 's/^#?PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config \
 && sed -i -E 's/^#?LogLevel.*/LogLevel VERBOSE/' /etc/ssh/sshd_config

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

# --- interaction logging (author-side observability) --------------------------
# Per-session bash/psql history plus a command log. The root tails mirror the
# log to the container output (live) and, when the instancer mounts the `logs`
# volume, to a per-instance host directory that survives instance deletion.
# Not a security boundary.
COPY docker/escape-log-common.sh /usr/local/lib/escape/log.sh
COPY docker/escape-persist.sh    /usr/local/lib/escape/persist.sh
COPY docker/escape-mirror.sh     /usr/local/lib/escape/mirror.sh
COPY docker/profile-escape.sh    /etc/profile.d/escape-session.sh
COPY docker/bashrc-escape.sh     /etc/bash.bashrc.escape
COPY docker/escape-shell.sh      /usr/local/bin/escape-shell

RUN cat /etc/bash.bashrc.escape >> /etc/bash.bashrc \
 && rm -f /etc/bash.bashrc.escape \
 && mkdir -p /var/log/escape/sessions \
 && chmod 755 /usr/local/bin/escape-shell /usr/local/lib/escape/log.sh \
      /usr/local/lib/escape/persist.sh /usr/local/lib/escape/mirror.sh \
      /etc/profile.d/escape-session.sh \
 && usermod -s /usr/local/bin/escape-shell player

RUN chown player:player /home/player/.README \
 && chmod 755 /entrypoint.sh /opt/escape/*.sh \
 && chmod 644 /home/player/.README /opt/escape/sysadmin_note.txt \
 && mkdir -p /opt/escape

# --- postgres listens on the internal network (needed for the lateral hop) ----
# Query/connection logging is for the author to review player interactions;
# db-start.sh mirrors the cluster log to the container log (`docker logs <db>`).
RUN sed -i -E "s/^#?listen_addresses.*/listen_addresses = '*'/" \
      /etc/postgresql/14/main/postgresql.conf \
 && sed -i -E "s/^#?log_connections.*/log_connections = on/" \
      /etc/postgresql/14/main/postgresql.conf \
 && sed -i -E "s/^#?log_disconnections.*/log_disconnections = on/" \
      /etc/postgresql/14/main/postgresql.conf \
 && printf "log_statement = 'all'\n" \
      >> /etc/postgresql/14/main/postgresql.conf \
 && printf 'host all all 0.0.0.0/0 scram-sha-256\nhost all all ::/0 scram-sha-256\n' \
      >> /etc/postgresql/14/main/pg_hba.conf

EXPOSE 22

ENTRYPOINT ["/entrypoint.sh"]
