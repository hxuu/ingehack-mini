FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=UTC \
    LANG=C.UTF-8

# Rumor Mill #3 — The Liars' Club
#
# No sudo, no baked secrets. The flag arrives as FLAG from ops/deploy-static.sh
# and is staged root-only at container start.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        openssh-server \
        openssl \
        attr \
        acl \
        e2fsprogs \
        binutils \
        libpam-pwquality \
        libpam-modules \
        libpam-modules-bin \
        libpwquality-tools \
        coreutils \
        bash \
        grep \
        sed \
        findutils \
        procps \
        util-linux \
        passwd \
        login \
        tzdata \
 && rm -rf /var/lib/apt/lists/* \
 && apt-get clean

RUN ln -sf /usr/share/zoneinfo/UTC /etc/localtime \
 && printf 'UTC\n' > /etc/timezone \
 && mkdir -p /run/sshd /var/run/faillock /var/log/rumor /etc/sudoers.d \
 && chmod 700 /var/run/faillock /var/log/rumor \
 && chmod 755 /etc/sudoers.d \
 && rm -rf /etc/update-motd.d/* /etc/legal

COPY src/sshd_config  /etc/ssh/sshd_config
COPY src/entrypoint.sh /entrypoint.sh
COPY verify.sh         /verify.sh

RUN chmod 700 /entrypoint.sh /verify.sh \
 && ssh-keygen -A

EXPOSE 2222

ENTRYPOINT ["/entrypoint.sh"]
