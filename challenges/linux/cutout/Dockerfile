FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=UTC \
    LANG=C.UTF-8

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      openssh-server \
      systemd \
      python3 \
      acl \
      procps \
      psmisc \
      libpam-runtime \
      libpam-modules \
      util-linux \
      tzdata \
 && apt-get -y autoremove \
 && rm -rf /var/lib/apt/lists/* \
 && apt-get clean

COPY files/gen_setup.sh  /tmp/build-assets/gen_setup.sh

COPY files/ch41n.py      /home/ch41n/ch41n.py
COPY files/keeper.py     /usr/local/bin/keeper.py
COPY files/keeper.sh     /usr/local/bin/keeper.sh
COPY files/watchdog.sh   /usr/local/bin/watchdog.sh
COPY files/supervisor.sh /usr/local/bin/supervisor.sh
COPY entrypoint.sh       /entrypoint.sh

COPY files/opt/                    /opt/
COPY files/var/                    /var/
COPY systemd/*.service             /etc/systemd/system/
COPY systemd/cutout-watchdog.timer /etc/systemd/system/

RUN chmod +x /entrypoint.sh /usr/local/bin/supervisor.sh /usr/local/bin/watchdog.sh \
      /usr/local/bin/keeper.sh /usr/local/bin/keeper.py \
 && chmod +x /opt/vendor-tool/bin/tool \
 && bash /tmp/build-assets/gen_setup.sh \
 && chmod 700 /home/ch41n/ch41n.py \
 && chown ch41n:ch41n /home/ch41n/ch41n.py \
 && rm -rf /tmp/build-assets

EXPOSE 22

ENTRYPOINT ["/entrypoint.sh"]
