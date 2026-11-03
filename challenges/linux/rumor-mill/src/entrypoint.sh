#!/usr/bin/env bash
# Rumor Mill — runtime provisioning.
# Runs as root on every container start; idempotent.
set -euo pipefail

# If CI injects FLAG, stage it root-only and re-exec with a clean environment
# so the secret never remains in PID 1's /proc/1/environ.
if [ -n "${FLAG:-}" ]; then
    umask 077
    printf '%s\n' "$FLAG" > /run/rumor-flag
    chmod 600 /run/rumor-flag
    unset FLAG
    exec env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
        /entrypoint.sh
fi

# ---------------------------------------------------------------- identity --
printf 'challenge-rumor-mill\n' > /etc/hostname
hostname challenge-rumor-mill 2>/dev/null || true
ln -sf /usr/share/zoneinfo/UTC /etc/localtime
printf 'UTC\n' > /etc/timezone
export TZ=UTC

# --------------------------------------------------------------- gh3nj4 pw --
# Generated at runtime so it never lands in an image layer. Stored root-only.
if [ ! -s /root/gh3nj4_password.txt ]; then
    umask 077
    { head -c 24 /dev/urandom | base64 | tr -d '/+=' | head -c 32; printf '\n'; } \
        > /root/gh3nj4_password.txt
fi
chown root:root /root/gh3nj4_password.txt
chmod 600 /root/gh3nj4_password.txt
gh3nj4_pw="$(cat /root/gh3nj4_password.txt)"

# ------------------------------------------------------------------- users --
ensure_user() {
    local u="$1"
    if ! id "$u" >/dev/null 2>&1; then
        useradd -m -s /bin/bash "$u"
    fi
    usermod -c "" "$u"                 # GECOS must be empty
    chown "$u:$u" "/home/$u"
    chmod 700 "/home/$u"
}

ensure_user y4ss1n3
ensure_user n0d4
ensure_user boul3h14
ensure_user gh3nj4

printf '%s\n' \
    'y4ss1n3:Welcome123' \
    'n0d4:K4r4k0_1962' \
    'boul3h14:h4y_3l1y4' \
    "gh3nj4:${gh3nj4_pw}" | chpasswd

# ------------------------------------------------------------------- files --
cat > /home/y4ss1n3/onboarding.txt <<'EOF'
Welcome to the box, y4ss1n3.

Your colleague n0d4 left you a handover note. His account password is:

    K4r4k0_1962

Use it wisely. Everything you need is in his home directory.
EOF
chown y4ss1n3:y4ss1n3 /home/y4ss1n3/onboarding.txt
chmod 600 /home/y4ss1n3/onboarding.txt

# .part1/.part2 have NO trailing newline: the README's join rule is literal.
printf '%s' 'h4y'   > /home/n0d4/.part1
printf '%s' '3l1y4' > /home/n0d4/.part2
cat > /home/n0d4/README <<'EOF'
boul3h14's password = .part1 + "_" + .part2
EOF
chown n0d4:n0d4 /home/n0d4/.part1 /home/n0d4/.part2 /home/n0d4/README
chmod 600 /home/n0d4/.part1 /home/n0d4/.part2 /home/n0d4/README

# Real flag: staged CI value, or the root-only baked file (standalone build).
flag_content=""
if [ -r /run/rumor-flag ]; then
    flag_content="$(cat /run/rumor-flag)"
    rm -f /run/rumor-flag
elif [ -r /etc/rumor-mill/flag ]; then
    flag_content="$(cat /etc/rumor-mill/flag)"
fi
if [ -z "$flag_content" ]; then
    flag_content='ingehack{placeholder_flag_replaced_at_deploy}'
fi
printf '%s\n' "$flag_content" > /home/boul3h14/flag.txt
chown boul3h14:boul3h14 /home/boul3h14/flag.txt
chmod 600 /home/boul3h14/flag.txt

cat > /home/boul3h14/verify_gh3nj4.txt <<'EOF'
If you can read this, you are boul3h14.
gh3nj4's "flag" is a decoy — check /home/gh3nj4/flag.txt to confirm.
EOF
chown boul3h14:boul3h14 /home/boul3h14/verify_gh3nj4.txt
chmod 600 /home/boul3h14/verify_gh3nj4.txt

printf '%s\n' 'ingehack{th1s_1s_4_f4k3_fl4g}' > /home/gh3nj4/flag.txt
chown gh3nj4:gh3nj4 /home/gh3nj4/flag.txt
chmod 600 /home/gh3nj4/flag.txt

# Sanctioned ACL fallback (section 5): a named-user ACL would force
# /home/gh3nj4 to 0710 and flag.txt to 0640, violating the mandatory
# mode-700/600 hardening. Copy the decoy into boul3h14's own 0700 home.
printf '%s\n' 'ingehack{th1s_1s_4_f4k3_fl4g}' > /home/boul3h14/gh3nj4_flag_copy.txt
chown boul3h14:boul3h14 /home/boul3h14/gh3nj4_flag_copy.txt
chmod 600 /home/boul3h14/gh3nj4_flag_copy.txt

# -------------------------------------------------------------- hardening --
# No sudo/wheel membership, no sudoers drop-ins.
for u in y4ss1n3 n0d4 boul3h14 gh3nj4; do
    deluser "$u" sudo  >/dev/null 2>&1 || true
    deluser "$u" wheel >/dev/null 2>&1 || true
    deluser "$u" admin >/dev/null 2>&1 || true
done
rm -f /etc/sudoers.d/y4ss1n3 /etc/sudoers.d/n0d4 \
      /etc/sudoers.d/boul3h14 /etc/sudoers.d/gh3nj4

# Shadow: 0640 root:shadow, players never in shadow.
chown root:shadow /etc/shadow
chmod 640 /etc/shadow

# pam_faillock on /etc/pam.d/su (preauth + authfail), idempotent.
if ! grep -q 'pam_faillock' /etc/pam.d/su; then
    awk '
    /@include common-auth/ {
        print "auth required pam_faillock.so preauth";
        print "auth [success=1 default=ignore] pam_unix.so nullok";
        print "auth [default=die] pam_faillock.so authfail";
        print "auth sufficient pam_faillock.so authsucc";
        next
    }
    /@include common-account/ {
        print "account required pam_faillock.so";
        print;
        next
    }
    { print }
    ' /etc/pam.d/su > /etc/pam.d/su.new
    mv /etc/pam.d/su.new /etc/pam.d/su
fi
chown root:root /etc/pam.d/su
chmod 644 /etc/pam.d/su

mkdir -p /var/run/faillock
chown root:root /var/run/faillock
chmod 700 /var/run/faillock
cat > /etc/security/faillock.conf <<'EOF'
dir = /var/run/faillock
deny = 5
unlock_time = 300
EOF

# Banner files: exactly one line, nothing else.
printf 'Authorized access only.\n' > /etc/issue
printf 'Authorized access only.\n' > /etc/motd
rm -rf /etc/update-motd.d/*

# pam_motd writes ~/.cache/motd.legal-displayed (0644) into a player's home on
# every login, which would break the 0600 invariant at runtime. Drop the
# module and the legal notice; sshd's PrintMotd still shows /etc/motd.
rm -f /etc/legal
sed -i 's/^session[[:space:]]\+optional[[:space:]]\+pam_motd\.so/# &/' /etc/pam.d/sshd
if grep -qE '^UMASK' /etc/login.defs; then
    sed -i 's/^UMASK.*/UMASK 077/' /etc/login.defs
else
    printf 'UMASK 077\n' >> /etc/login.defs
fi
rm -rf /home/*/.cache/motd.legal-displayed
find /home -type d -name .cache -empty -delete 2>/dev/null || true

# Sweep: every home 0700, every file 0600.
chmod 700 /home/*
find /home -type f -exec chmod 600 {} +

# No leftovers in shared scratch space.
rm -rf /tmp/* /var/tmp/* /dev/shm/* 2>/dev/null || true

# SSH host keys + runtime dir.
ssh-keygen -A >/dev/null 2>&1 || true
mkdir -p /var/run/sshd
chmod 755 /var/run/sshd

exec /usr/sbin/sshd -D -e
