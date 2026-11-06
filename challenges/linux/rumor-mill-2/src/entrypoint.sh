#!/usr/bin/env bash
###############################################################################
# entrypoint.sh — Rumor Mill #2 — The Encoded Rumor
# Creates users, files, permissions, and hardening at CONTAINER START.
# The plaintext flag never appears in this script or in any world-readable file.
###############################################################################
set -euo pipefail

# --------------------------------------------------------------------------
# CI injects FLAG. Stage it root-only, then re-exec with a clean environment
# so the secret never remains in PID 1's /proc/1/environ.
# --------------------------------------------------------------------------
if [ -n "${FLAG:-}" ]; then
    umask 077
    printf '%s\n' "$FLAG" > /run/rumor-flag
    chmod 600 /run/rumor-flag
    unset FLAG
    exec env -i \
        PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
        HOME=/root \
        SSH_PORT="${SSH_PORT:-2222}" \
        /entrypoint.sh
fi

SSH_PORT="${SSH_PORT:-2222}"
KEY='matdiresh_el_3rab'

###############################################################################
# 0. RESOLVE THE REAL FLAG (staged CI value or root-only baked file)
###############################################################################
flag_content=""
if [ -r /run/rumor-flag ]; then
    flag_content="$(cat /run/rumor-flag)"
    rm -f /run/rumor-flag
elif [ -r /etc/rumor-mill/flag ]; then
    flag_content="$(cat /etc/rumor-mill/flag)"
fi
if [ -z "$flag_content" ]; then
    echo "FATAL: no flag supplied (set FLAG or bake /etc/rumor-mill/flag)" >&2
    exit 1
fi

# Persist a root-only copy for the verifier. Never world-readable.
mkdir -p /etc/rumor-mill
printf '%s\n' "$flag_content" > /etc/rumor-mill/flag
chown root:root /etc/rumor-mill/flag
chmod 600 /etc/rumor-mill/flag

###############################################################################
# 1. CREATE USERS (empty GECOS, own group, bash shell)
###############################################################################
for u in y4ss1n3 n0d4 boul3h14 gh3nj4; do
    if ! id "$u" >/dev/null 2>&1; then
        useradd -m -s /bin/bash -c '' "$u"
    fi
    usermod -c '' "$u"
    chown "$u:$u" "/home/$u"
    chmod 700 "/home/$u"
done

###############################################################################
# 2. SET PASSWORDS
###############################################################################
printf '%s\n' \
    'y4ss1n3:Welcome123' \
    'n0d4:K4r4k0_1962_v2' \
    'boul3h14:h4y_3l1y4_ws4y' | chpasswd

# gh3nj4's password is generated at container start so it never lands in an
# image layer. Stored only in a root-only file.
if [ ! -s /root/gh3nj4_password.txt ]; then
    umask 077
    { head -c 24 /dev/urandom | base64 | tr -d '/+=' | head -c 32; printf '\n'; } \
        > /root/gh3nj4_password.txt
fi
chown root:root /root/gh3nj4_password.txt
chmod 600 /root/gh3nj4_password.txt
GH3NJ4_PW="$(cat /root/gh3nj4_password.txt)"
printf '%s\n' "gh3nj4:${GH3NJ4_PW}" | chpasswd

###############################################################################
# 3. REMOVE USERS FROM DANGEROUS GROUPS
###############################################################################
for u in y4ss1n3 n0d4 boul3h14 gh3nj4; do
    for g in sudo wheel adm disk shadow docker lxd; do
        gpasswd -d "$u" "$g" >/dev/null 2>&1 || true
    done
done

###############################################################################
# 4. y4ss1n3's home: stale note, history, rotated secret
###############################################################################
cat > /home/y4ss1n3/onboarding.txt << 'ONBOARD_EOF'
Welcome back to the box, y4ss1n3.

n0d4 left another handover note. His password is below, base64-encoded:

    SzRyNGswXzE5NjI=

Decode it and you're in. Same as last time — should be easy.
ONBOARD_EOF

cat > /home/y4ss1n3/.bash_history << 'HIST_EOF'
ls -la
cat onboarding.txt
echo SzRyNGswXzE5NjI= | base64 -d
# K4r4k0_1962 — but that failed, admin rotated it
su n0d4
# Authentication failure
# the note is stale, real one is in .env
cat .env
HIST_EOF

cat > /home/y4ss1n3/.env << 'ENV_EOF'
# n0d4 password rotated 2026-11-01
N0D4_B64=SzRyNGswXzE5NjJfdjI=
ENV_EOF

chown y4ss1n3:y4ss1n3 \
    /home/y4ss1n3/onboarding.txt /home/y4ss1n3/.bash_history /home/y4ss1n3/.env
chmod 600 \
    /home/y4ss1n3/onboarding.txt /home/y4ss1n3/.bash_history /home/y4ss1n3/.env

###############################################################################
# 5. n0d4's home: base64 parts, encoded order, decoy part
###############################################################################
cat > /home/n0d4/README << 'N0D4_EOF'
boul3h14's password = join(decode(.part<order[0]>), decode(.part<order[1]>),
decode(.part<order[2]>)) with "_"

All parts are base64. The order is base64-encoded in .part_order.
There is a .part4 — it is a decoy. Do not use it.
N0D4_EOF

printf '%s' 'd3M0eQ=='   > /home/n0d4/.part1.b64
printf '%s' 'aDR5'       > /home/n0d4/.part2.b64
printf '%s' 'M2wxeTQ='   > /home/n0d4/.part3.b64
printf '%s' 'bjBwMw=='   > /home/n0d4/.part4.b64
printf '%s' 'MiwzLDE='   > /home/n0d4/.part_order

chown n0d4:n0d4 /home/n0d4/README /home/n0d4/.part1.b64 /home/n0d4/.part2.b64 \
    /home/n0d4/.part3.b64 /home/n0d4/.part4.b64 /home/n0d4/.part_order
chmod 600 /home/n0d4/README /home/n0d4/.part1.b64 /home/n0d4/.part2.b64 \
    /home/n0d4/.part3.b64 /home/n0d4/.part4.b64 /home/n0d4/.part_order

###############################################################################
# 6. boul3h14's home: encrypted flag + base64 key
###############################################################################
printf '%s' "$flag_content" | \
    openssl enc -aes-256-cbc -a -salt -pbkdf2 -k "$KEY" \
    > /home/boul3h14/flag.txt

printf '%s' "$KEY" | base64 > /home/boul3h14/.key.b64

cat > /home/boul3h14/README << 'BOUL_EOF'
The flag is encrypted. The key is base64-encoded in .key.b64.

Decode the key, then:
    openssl enc -d -aes-256-cbc -a -pbkdf2 -in flag.txt -k <decoded_key>

If you see garbage, you have the wrong key or the wrong cipher.
BOUL_EOF

cat > /home/boul3h14/verify_gh3nj4.txt << 'VGEOF'
If you can read this, you are boul3h14.

gh3nj4's flag is the decoy. Yours is the real one — but it's encrypted.
The key is in this home. Read README.
VGEOF

chown boul3h14:boul3h14 /home/boul3h14/flag.txt /home/boul3h14/.key.b64 \
    /home/boul3h14/README /home/boul3h14/verify_gh3nj4.txt
chmod 600 /home/boul3h14/flag.txt /home/boul3h14/.key.b64 \
    /home/boul3h14/README /home/boul3h14/verify_gh3nj4.txt

###############################################################################
# 7. gh3nj4's home: decoy flag
###############################################################################
printf '%s' 'ingehack{th1s_1s_4_f4k3_fl4g}' > /home/gh3nj4/flag.txt
chown gh3nj4:gh3nj4 /home/gh3nj4/flag.txt
chmod 600 /home/gh3nj4/flag.txt

###############################################################################
# 8. VERIFY THE ENCRYPTED FLAG DECRYPTS (as boul3h14, no root shortcut)
###############################################################################
DECRYPTED="$(runuser -u boul3h14 -- openssl enc -d -aes-256-cbc -a -pbkdf2 \
    -in /home/boul3h14/flag.txt -k "$KEY" 2>/dev/null || true)"
if [ "$DECRYPTED" != "$flag_content" ]; then
    echo "FATAL: flag decryption verification failed" >&2
    exit 1
fi
echo "[entrypoint] flag encryption verified OK"

###############################################################################
# 9. HARDENING
###############################################################################

# H1: home directories
chmod 711 /home
chown root:root /home
chmod 700 /home/y4ss1n3 /home/n0d4 /home/boul3h14 /home/gh3nj4

# H2: every file under /home is 0600
find /home -type f -exec chmod 600 {} +

# H4: no sudoers drop-ins for challenge users
rm -f /etc/sudoers.d/*y4ss1n3* /etc/sudoers.d/*n0d4* \
      /etc/sudoers.d/*boul3h14* /etc/sudoers.d/*gh3nj4* 2>/dev/null || true

# H5: pam_faillock (preauth + authfail + authsucc; account lockout)
mkdir -p /var/run/faillock
chown root:root /var/run/faillock
chmod 700 /var/run/faillock
cat > /etc/security/faillock.conf << 'FAILLOCK_EOF'
dir = /var/run/faillock
deny = 5
unlock_time = 900
fail_interval = 900
FAILLOCK_EOF

cat > /etc/pam.d/su << 'SU_PAM_EOF'
# Rumor Mill #2 — su with faillock
auth       sufficient   pam_rootok.so
auth       required     pam_faillock.so preauth
auth       [success=1 default=ignore] pam_unix.so nullok
auth       [default=die] pam_faillock.so authfail
auth       sufficient   pam_faillock.so authsucc
account    required     pam_faillock.so
account    required     pam_unix.so
session    required     pam_unix.so
password   required     pam_unix.so
SU_PAM_EOF

cat > /etc/pam.d/sshd << 'SSHD_PAM_EOF'
# Rumor Mill #2 — sshd with faillock (pam_motd intentionally omitted so a
# login never writes a 0644 ~/.cache/motd.legal-displayed into a home).
auth       required     pam_faillock.so preauth
auth       [success=1 default=ignore] pam_unix.so nullok
auth       [default=die] pam_faillock.so authfail
auth       sufficient   pam_faillock.so authsucc
account    required     pam_faillock.so
account    required     pam_unix.so
session    required     pam_unix.so
session    required     pam_loginuid.so
session    optional     pam_keyinit.so force revoke
password   required     pam_unix.so
SSHD_PAM_EOF

cat > /etc/pam.d/login << 'LOGIN_PAM_EOF'
# Rumor Mill #2 — console login with faillock
auth       required     pam_faillock.so preauth
auth       required     pam_securetty.so
auth       [success=1 default=ignore] pam_unix.so nullok
auth       [default=die] pam_faillock.so authfail
auth       sufficient   pam_faillock.so authsucc
account    required     pam_faillock.so
account    required     pam_unix.so
session    required     pam_unix.so
session    required     pam_loginuid.so
session    optional     pam_lastlog.so
password   required     pam_unix.so
LOGIN_PAM_EOF

chown root:root /etc/pam.d/su /etc/pam.d/sshd /etc/pam.d/login
chmod 644 /etc/pam.d/su /etc/pam.d/sshd /etc/pam.d/login

# H12: GECOS already cleared; re-assert
for u in y4ss1n3 n0d4 boul3h14 gh3nj4; do
    usermod -c '' "$u"
done

# H13: /etc/shadow
chmod 640 /etc/shadow
chown root:shadow /etc/shadow

# H14: sshd_config (port is templated)
sed -i "s/^Port .*/Port ${SSH_PORT}/" /etc/ssh/sshd_config
ssh-keygen -A >/dev/null 2>&1 || true
mkdir -p /run/sshd
chmod 755 /run/sshd

# H15: banners
printf 'Authorized access only.\n' > /etc/issue
printf 'Authorized access only.\n' > /etc/issue.net
printf 'Authorized access only.\n' > /etc/motd
rm -rf /etc/update-motd.d/* /etc/legal

# H17/H18: best-effort process and kernel hardening
mount -o remount,hidepid=2 /proc 2>/dev/null || true
for sc in \
    "kernel.yama.ptrace_scope=3" \
    "kernel.kptr_restrict=2" \
    "kernel.dmesg_restrict=1" \
    "kernel.kexec_load_disabled=1" \
    "kernel.unprivileged_bpf_disabled=1"; do
    sysctl -w "$sc" >/dev/null 2>&1 || true
done

# H19: no core dumps for challenge users
if ! grep -q '^# Rumor Mill #2 core limits' /etc/security/limits.conf 2>/dev/null; then
    {
        printf '%s\n' '# Rumor Mill #2 core limits'
        for u in y4ss1n3 n0d4 boul3h14 gh3nj4; do
            printf '%s hard core 0\n%s soft core 0\n' "$u" "$u"
        done
    } >> /etc/security/limits.conf
fi

# H20: no SSH keys
find /home -name authorized_keys -delete 2>/dev/null || true
for u in y4ss1n3 n0d4 boul3h14 gh3nj4; do
    rm -rf "/home/$u/.ssh" 2>/dev/null || true
done

# H21: UTC
ln -sf /usr/share/zoneinfo/UTC /etc/localtime
printf 'UTC\n' > /etc/timezone

# Login-time umask so anything a player creates is private.
if grep -qE '^UMASK' /etc/login.defs; then
    sed -i 's/^UMASK.*/UMASK 077/' /etc/login.defs
else
    printf 'UMASK 077\n' >> /etc/login.defs
fi

# H9: no cron/at jobs
for u in y4ss1n3 n0d4 boul3h14 gh3nj4; do
    crontab -r -u "$u" >/dev/null 2>&1 || true
done

# H10: clean scratch space
rm -rf /tmp/* /var/tmp/* /dev/shm/* 2>/dev/null || true

# Final sweep: home modes must hold even after any file creation above.
chmod 711 /home
chmod 700 /home/y4ss1n3 /home/n0d4 /home/boul3h14 /home/gh3nj4
find /home -type f -exec chmod 600 {} +

###############################################################################
# 10. DROP SECRETS FROM THIS PROCESS
###############################################################################
unset GH3NJ4_PW DECRYPTED KEY flag_content

###############################################################################
# 11. START SSHD
###############################################################################
echo "[entrypoint] starting sshd on port ${SSH_PORT}"
exec /usr/sbin/sshd -D -e
