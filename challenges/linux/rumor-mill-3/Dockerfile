FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=UTC \
    LANG=C.UTF-8

# Runtime for Rumor Mill #3: sshd, git (dangling-blob recovery), gnupg
# (symmetric dead drop), sudo (the archive helper), plus the audit tools the
# verifier needs (getcap/getfacl/lsattr).
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        openssh-server \
        openssl \
        git \
        gnupg \
        sudo \
        acl \
        attr \
        libcap2-bin \
        libpam-modules \
        libpam-modules-bin \
        coreutils \
        bash \
        grep \
        sed \
        findutils \
        tar \
        procps \
        util-linux \
        passwd \
        login \
        tzdata \
 && rm -rf /var/lib/apt/lists/* \
 && apt-get clean

RUN ln -sf /usr/share/zoneinfo/UTC /etc/localtime \
 && printf 'UTC\n' > /etc/timezone \
 && mkdir -p /run/sshd /var/run/faillock /var/mail /srv/archive /srv/backups \
            /etc/rumor-mill \
 && chmod 700 /var/run/faillock /etc/rumor-mill /srv/backups \
 && chmod 755 /var/mail \
 && chmod 750 /srv/archive \
 && touch /etc/rumor-mill/flag \
 && chown root:root /etc/rumor-mill/flag \
 && chmod 600 /etc/rumor-mill/flag

COPY src/sshd_config  /etc/ssh/sshd_config
COPY src/entrypoint.sh /entrypoint.sh
COPY verify.sh         /verify.sh

RUN chmod 700 /entrypoint.sh /verify.sh \
 && rm -rf /etc/update-motd.d/* /etc/legal \
 && ssh-keygen -A

EXPOSE 2222

ENTRYPOINT ["/entrypoint.sh"]
