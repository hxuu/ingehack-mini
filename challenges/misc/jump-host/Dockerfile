FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server \
    sudo \
    less \
    findutils \
    gcc \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash admin \
    && useradd -m -s /usr/local/bin/guest-shell guest \
    && echo 'guest:guest' | chpasswd \
    && echo /usr/local/bin/guest-shell >> /etc/shells

RUN mkdir -p /home/guest/bin \
    && ln -s /bin/ls /home/guest/bin/ls \
    && ln -s /usr/bin/less /home/guest/bin/less \
    && ln -s /usr/bin/find /home/guest/bin/find

COPY src/guest-shell.sh /usr/local/bin/guest-shell
COPY src/backup.c /opt/tools/backup.c
RUN chmod 755 /usr/local/bin/guest-shell \
    && gcc -O2 -o /opt/tools/backup /opt/tools/backup.c \
    && chown root:root /opt/tools/backup \
    && chmod 4755 /opt/tools/backup \
    && rm -f /opt/tools/backup.c

COPY src/sudoers-guest /etc/sudoers.d/guest-awk
RUN chmod 440 /etc/sudoers.d/guest-awk

COPY src/sshd_config /etc/ssh/sshd_config
COPY src/entrypoint.sh /entrypoint.sh
RUN chmod 755 /entrypoint.sh \
    && mkdir -p /var/run/sshd \
    && touch /home/admin/flag.txt \
    && chown admin:admin /home/admin/flag.txt \
    && chmod 600 /home/admin/flag.txt

COPY src/bash_history /home/guest/.bash_history
COPY src/README.txt /home/guest/README.txt
RUN chown guest:guest /home/guest/.bash_history /home/guest/README.txt \
    && chmod 644 /home/guest/.bash_history /home/guest/README.txt

EXPOSE 22
ENTRYPOINT ["/entrypoint.sh"]
