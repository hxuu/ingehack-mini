#!/bin/bash
set -euo pipefail

###############################################################################
# entrypoint.sh — Rumor Mill #2 — The Encoded Rumor
# Creates users, files, permissions, hardening at CONTAINER START.
# NO secrets are baked into the Docker image.
###############################################################################

SSH_PORT="${SSH_PORT:-2222}"

###############################################################################
# 1. CREATE USERS (no GECOS, home dirs, specific shells)
###############################################################################
useradd -m -s /bin/bash -c '' y4ss1n3  2>/dev/null || true
useradd -m -s /bin/bash -c '' n0d4     2>/dev/null || true
useradd -m -s /bin/bash -c '' boul3h14 2>/dev/null || true
useradd -m -s /bin/bash -c '' gh3nj4   2>/dev/null || true

# Clear GECOS for all four users (in case anything was set)
for u in y4ss1n3 n0d4 boul3h14 gh3nj4; do
    usermod -c '' "$u"
done

###############################################################################
# 2. SET PASSWORDS
###############################################################################
echo 'y4ss1n3:Welcome123' | chpasswd
echo 'n0d4:K4r4k0_1962_v2' | chpasswd
echo 'boul3h14:h4y_3l1y4_ws4y' | chpasswd

# Generate gh3nj4's random password at container start
GH3NJ4_PW="$(head -c 24 /dev/urandom | base64 | tr -d '/+=' | head -c 32)"
echo "gh3nj4:${GH3NJ4_PW}" | chpasswd
# Store ONLY in root-readable file
echo -n "${GH3NJ4_PW}" > /root/gh3nj4_password.txt
chmod 600 /root/gh3nj4_password.txt
chown root:root /root/gh3nj4_password.txt

# Clear the variable from this script's environment after use
# (we still need it for the image-layer check, but it's only in /root/)

###############################################################################
# 3. REMOVE USERS FROM DANGEROUS GROUPS
###############################################################################
for u in y4ss1n3 n0d4 boul3h14 gh3nj4; do
    for g in sudo wheel adm disk shadow docker lxd; do
        gpasswd -d "$u" "$g" 2>/dev/null || true
    done
done

###############################################################################
# 4. CREATE FILES — y4ss1n3's home
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

chown y4ss1n3:y4ss1n3 /home/y4ss1n3/onboarding.txt /home/y4ss1n3/.bash_history /home/y4ss1n3/.env
chmod 600 /home/y4ss1n3/onboarding.txt /home/y4ss1n3/.bash_history /home/y4ss1n3/.env

###############################################################################
# 5. CREATE FILES — n0d4's home
###############################################################################
cat > /home/n0d4/README << 'N0D4_EOF'
boul3h14's password = join(decode(.part<order[0]>), decode(.part<order[1]>),
decode(.part<order[2]>)) with "_"

All parts are base64. The order is base64-encoded in .part_order.
There is a .part4 — it is a decoy. Do not use it.
N0D4_EOF

echo -n 'd3M0eQ==' > /home/n0d4/.part1.b64
echo -n 'aDR5' > /home/n0d4/.part2.b64
echo -n 'M2wxeTQ=' > /home/n0d4/.part3.b64
echo -n 'bjBwMw==' > /home/n0d4/.part4.b64
echo -n 'MiwzLDE=' > /home/n0d4/.part_order

chown n0d4:n0d4 /home/n0d4/README /home/n0d4/.part1.b64 /home/n0d4/.part2.b64 \
    /home/n0d4/.part3.b64 /home/n0d4/.part4.b64 /home/n0d4/.part_order
chmod 600 /home/n0d4/README /home/n0d4/.part1.b64 /home/n0d4/.part2.b64 \
    /home/n0d4/.part3.b64 /home/n0d4/.part4.b64 /home/n0d4/.part_order

###############################################################################
# 6. CREATE FILES — boul3h14's home
###############################################################################

# Encrypted flag (generated fresh each start)
echo -n 'ingehack{rum0rs_4r3_b4s364_4ll_th3_w4y_d0wn}' | \
    openssl enc -aes-256-cbc -a -salt -pbkdf2 -k 'matdiresh_el_3rab' \
    > /home/boul3h14/flag.txt

# Key file
echo -n 'matdiresh_el_3rab' | base64 > /home/boul3h14/.key.b64

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
# 7. CREATE FILES — gh3nj4's home (decoy)
###############################################################################
echo -n 'ingehack{th1s_1s_4_f4k3_fl4g}' > /home/gh3nj4/flag.txt
chown gh3nj4:gh3nj4 /home/gh3nj4/flag.txt
chmod 600 /home/gh3nj4/flag.txt

###############################################################################
# 8. VERIFY ENCRYPTED FLAG DECRYPTS CORRECTLY
###############################################################################
DECRYPTED=$(su -s /bin/bash -c 'openssl enc -d -aes-256-cbc -a -pbkdf2 -in /home/boul3h14/flag.txt -k "$(base64 -d /home/boul3h14/.key.b64)"' boul3h14)
if [ "$DECRYPTED" != 'ingehack{rum0rs_4r3_b4s364_4ll_th3_w4y_d0wn}' ]; then
    echo "FATAL: Flag decryption verification failed!" >&2
    echo "Got: $DECRYPTED" >&2
    exit 1
fi
echo "[entrypoint] Flag encryption verified OK."

###############################################################################
# 9. HARDENING
###############################################################################

# H1: Home directory permissions
chmod 711 /home
chown root:root /home
chmod 700 /home/y4ss1n3 /home/n0d4 /home/boul3h14 /home/gh3nj4

# H2: All files in homes are mode 600 (already set above, but enforce)
find /home -type f -exec chmod 600 {} \;

# H4: Remove any sudoers.d entries for challenge users
rm -f /etc/sudoers.d/*y4ss1n3* /etc/sudoers.d/*n0d4* /etc/sudoers.d/*boul3h14* /etc/sudoers.d/*gh3nj4* 2>/dev/null || true

# H5: pam_faillock configuration
cat > /etc/security/faillock.conf << 'FAILLOCK_EOF'
deny=5
unlock_time=900
fail_interval=900
FAILLOCK_EOF

# Configure pam_faillock on su
# First, backup and rewrite /etc/pam.d/su
cat > /etc/pam.d/su << 'SU_PAM_EOF'
auth       required     pam_faillock.so preauth
auth       sufficient   pam_rootok.so
auth       required     pam_unix.so
auth       [default=die] pam_faillock.so authfail
account    required     pam_unix.so
session    required     pam_unix.so
password   required     pam_unix.so
SU_PAM_EOF

# Configure pam_faillock on sshd
cat > /etc/pam.d/sshd << 'SSHD_PAM_EOF'
auth       required     pam_faillock.so preauth
auth       required     pam_unix.so
auth       [default=die] pam_faillock.so authfail
account    required     pam_unix.so
session    required     pam_unix.so
session    required     pam_loginuid.so
session    optional     pam_keyinit.so force revoke
password   required     pam_unix.so
SSHD_PAM_EOF

# Configure pam_faillock on login
cat > /etc/pam.d/login << 'LOGIN_PAM_EOF'
auth       required     pam_faillock.so preauth
auth       required     pam_securetty.so
auth       required     pam_unix.so
auth       [default=die] pam_faillock.so authfail
account    required     pam_unix.so
session    required     pam_unix.so
session    required     pam_loginuid.so
session    optional     pam_lastlog.so
password   required     pam_unix.so
LOGIN_PAM_EOF

# H12: Clear GECOS (already done above, but ensure)
for u in y4ss1n3 n0d4 boul3h14 gh3nj4; do
    usermod -c '' "$u"
done

# H13: /etc/shadow permissions
chmod 640 /etc/shadow
chown root:shadow /etc/shadow

# H14: SSH configuration
cat > /etc/ssh/sshd_config << SSHD_EOF
Port ${SSH_PORT}
Protocol 2
PermitRootLogin no
PasswordAuthentication yes
PermitEmptyPasswords no
AllowUsers y4ss1n3 n0d4 boul3h14 gh3nj4
AllowTcpForwarding no
PermitTunnel no
X11Forwarding no
KbdInteractiveAuthentication no
PermitUserEnvironment no
MaxAuthTries 3
LoginGraceTime 30
MaxSessions 2
MaxStartups 10:30:60
AllowAgentForwarding no
Banner /etc/issue.net
UsePAM yes
Subsystem sftp /usr/lib/openssh/sftp-server
SSHD_EOF

# Generate SSH host keys if they don't exist
ssh-keygen -A 2>/dev/null || true

# H15: Banners
echo 'Authorized access only.' > /etc/issue
echo 'Authorized access only.' > /etc/issue.net
echo 'Authorized access only.' > /etc/motd

# H17: hidepid — try to remount /proc with hidepid=2
# In containers this often fails; fall back to ptrace_scope
if mount -o remount,hidepid=2 /proc 2>/dev/null; then
    echo "[entrypoint] /proc remounted with hidepid=2"
else
    echo "[entrypoint] WARNING: Cannot remount /proc with hidepid=2 (container limitation)"
    echo "[entrypoint] Relying on ptrace_scope for process isolation"
fi

# H18: Sysctl hardening (best-effort in containers)
for sc in \
    "kernel.yama.ptrace_scope=3" \
    "kernel.kptr_restrict=2" \
    "kernel.dmesg_restrict=1" \
    "kernel.kexec_load_disabled=1" \
    "kernel.unprivileged_bpf_disabled=1"; do
    sysctl -w "$sc" 2>/dev/null || echo "[entrypoint] WARNING: Cannot set $sc (container limitation)"
done

# H19: No core dumps for challenge users
cat >> /etc/security/limits.conf << 'LIMITS_EOF'
y4ss1n3  hard  core  0
y4ss1n3  soft  core  0
n0d4     hard  core  0
n0d4     soft  core  0
boul3h14 hard  core  0
boul3h14 soft  core  0
gh3nj4   hard  core  0
gh3nj4   soft  core  0
LIMITS_EOF

# H20: No authorized_keys
find /home -name authorized_keys -delete 2>/dev/null || true
for u in y4ss1n3 n0d4 boul3h14 gh3nj4; do
    rm -rf "/home/$u/.ssh" 2>/dev/null || true
done

# H21: Timezone UTC
ln -sf /usr/share/zoneinfo/UTC /etc/localtime
echo UTC > /etc/timezone

# H22: Already enforced by find above, but double-check
find /home -type f ! -perm 600 -exec chmod 600 {} \;

# H25: chattr +i on flag.txt if supported
if chattr +i /home/boul3h14/flag.txt 2>/dev/null; then
    if lsattr /home/boul3h14/flag.txt 2>/dev/null | grep -q 'i'; then
        echo "[entrypoint] chattr +i applied to flag.txt"
    else
        echo "[entrypoint] chattr +i did not stick (filesystem limitation)"
    fi
else
    echo "[entrypoint] chattr not supported on this filesystem — relying on mode 600 + ownership"
fi

# H9: Disable cron/at
# Remove any challenge-user cron jobs
for u in y4ss1n3 n0d4 boul3h14 gh3nj4; do
    crontab -r -u "$u" 2>/dev/null || true
done

# H10: Clean temp dirs
rm -rf /tmp/* /var/tmp/* /dev/shm/* 2>/dev/null || true

# H6/H7: We don't add any SUID binaries or file capabilities.
# The base image has only standard distro SUID binaries.

###############################################################################
# 10. CLEAR ENVIRONMENT — prevent process/env leaks (H11)
###############################################################################
unset GH3NJ4_PW
unset DECRYPTED

###############################################################################
# 11. START SSHD (foreground)
###############################################################################
echo "[entrypoint] Starting sshd on port ${SSH_PORT}..."
exec /usr/sbin/sshd -D -e
