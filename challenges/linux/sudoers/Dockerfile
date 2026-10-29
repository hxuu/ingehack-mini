FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    openssh-server \
    gcc \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash ctf && \
    echo 'ctf:ctf' | chpasswd

RUN mkdir -p /var/run/sshd
COPY src/sshd_config /etc/ssh/sshd_config

COPY src/auditdrop.c /home/ctf/auditdrop.c
RUN gcc -o /usr/local/bin/auditdrop /home/ctf/auditdrop.c && \
    chown root:root /usr/local/bin/auditdrop && \
    chmod 4755 /usr/local/bin/auditdrop && \
    chown ctf:ctf /home/ctf/auditdrop.c && \
    chmod 644 /home/ctf/auditdrop.c

RUN mkdir -p /home/ctf/notes && \
    echo "Welcome to AuditDrop! Your notes are safe here." \
      > /home/ctf/notes/welcome.txt && \
    chown -R ctf:ctf /home/ctf/notes

# ADR 0004: the real flag is injected at deploy time from GitHub Actions
# secrets / the VM. It must NOT be committed to this repo. Follow the
# repo's existing static-container convention for injecting /flag at
# runtime (mount, env, init script, placeholder overwritten by CI).
# Document whichever convention you use in solution/README.md.
COPY src/entrypoint.sh /entrypoint.sh
RUN chmod 755 /entrypoint.sh && \
    touch /flag && \
    chown root:root /flag && \
    chmod 600 /flag

RUN touch /var/log/auditdrop.log && \
    chown root:root /var/log/auditdrop.log && \
    chmod 644 /var/log/auditdrop.log

EXPOSE 22

ENTRYPOINT ["/entrypoint.sh"]
