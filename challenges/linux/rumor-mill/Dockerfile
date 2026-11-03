FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=UTC \
    LANG=C.UTF-8

# Minimal runtime: SSH, POSIX ACL tooling, PAM (pam_faillock lives in
# libpam-modules on Ubuntu 22.04), and coreutils/ps for verify.sh.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        openssh-server \
        acl \
        libpam-modules \
        coreutils \
        bash \
        passwd \
        util-linux \
        procps \
        tzdata \
 && rm -rf /var/lib/apt/lists/* \
 && apt-get clean

RUN ln -sf /usr/share/zoneinfo/UTC /etc/localtime \
 && printf 'UTC\n' > /etc/timezone \
 && printf 'challenge-rumor-mill\n' > /etc/hostname \
 && mkdir -p /var/run/sshd /var/run/faillock \
 && chmod 700 /var/run/faillock

COPY src/sshd_config /etc/ssh/sshd_config
COPY src/motd        /etc/motd
COPY src/issue       /etc/issue
COPY src/entrypoint.sh /entrypoint.sh
COPY verify.sh         /verify.sh

RUN chmod 700 /entrypoint.sh /verify.sh \
 && rm -rf /etc/update-motd.d/* \
 && ssh-keygen -A

EXPOSE 2222

ENTRYPOINT ["/entrypoint.sh"]
