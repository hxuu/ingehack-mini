FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=UTC \
    LANG=C.UTF-8

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        openssh-server \
        openssl \
        attr \
        acl \
        libpam-pwquality \
        libpam-modules \
        coreutils \
        bash \
        grep \
        findutils \
        procps \
        util-linux \
        passwd \
        login \
        tzdata \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN ln -sf /usr/share/zoneinfo/UTC /etc/localtime \
 && printf 'UTC\n' > /etc/timezone \
 && printf 'challenge-rumor-mill-2\n' > /etc/hostname \
 && mkdir -p /var/run/sshd /var/run/faillock \
 && chmod 700 /var/run/faillock

COPY src/sshd_config /etc/ssh/sshd_config
COPY src/motd        /etc/motd
COPY src/issue.net   /etc/issue.net
COPY src/issue.net   /etc/issue
COPY src/entrypoint.sh /entrypoint.sh
COPY verify.sh         /verify.sh
COPY solution/         /solutions/

RUN chmod 700 /entrypoint.sh /verify.sh \
 && chmod 755 /solutions/solve.sh \
 && rm -rf /etc/update-motd.d/* \
 && ssh-keygen -A

ENV SSH_PORT=2222
EXPOSE 2222

ENTRYPOINT ["/entrypoint.sh"]
