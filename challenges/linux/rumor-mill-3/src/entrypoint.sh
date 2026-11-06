#!/usr/bin/env bash
###############################################################################
# entrypoint.sh — Rumor Mill #3 — The Liars' Club
#
# Everything secret is created HERE, at container start. The image layers
# contain no plaintext password, key, or flag: fixed values are carried as
# base64 and decoded only in memory.
###############################################################################
set -euo pipefail

# ---------------------------------------------------------------------------
# CI injects FLAG. Stage it root-only, then re-exec with a clean environment
# so the secret never remains in PID 1's /proc/1/environ.
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Fixed values. Base64 keeps the literal secrets out of the image layers.
# ---------------------------------------------------------------------------
b64d() { printf '%s' "$1" | base64 -d; }

Y4_PW="$(b64d 'NHJ0NHo0')"                       # player start
N0D4_PW="$(b64d 'MW5nM19kNHdsNA==')"             # intermediate user
BOUL_PW="$(b64d 'OWF0Y2hhbF9sd2VsZA==')"         # boul3h14's real password
FAKE_FLAG="$(b64d 'aW5nZWhhY2t7dGgxc18xc180X2Y0azNfZmw0Z30=')"
REAL_FLAG_FALLBACK="$(b64d 'aW5nZWhhY2t7M3YzcnkwbjNfbDEzZF9idTdfdGgzX2wwZ19kMWRuN30=')"
KEY="$(b64d 'bHdlbGRfZWxfZmFyZjBzaA==')"         # sync key
FLAG_PREFIX="$(b64d 'aW5nZWhhY2t7')"             # flag prefix
N0D4_KEY_B64='MW5nM19kNHdsNA=='                  # log line 3 (base64 of n0d4 pw)

###############################################################################
# 0. RESOLVE FLAG (CI-staged or in-image encoded fallback)
###############################################################################
if [ -r /run/rumor-flag ]; then
    REAL_FLAG="$(cat /run/rumor-flag)"
    rm -f /run/rumor-flag
else
    REAL_FLAG="$REAL_FLAG_FALLBACK"
fi
if [ -z "$REAL_FLAG" ]; then
    echo "FATAL: empty flag" >&2
    exit 1
fi

###############################################################################
# 1. USERS
###############################################################################
for u in y4ss1n3 n0d4 boul3h14 gh3nj4; do
    if ! id "$u" >/dev/null 2>&1; then
        useradd -m -s /bin/bash -c '' "$u"
    fi
    usermod -c '' "$u"
    chown "$u:$u" "/home/$u"
    chmod 700 "/home/$u"
done

# gh3nj4's password is generated at container start and lives only in
# /root/gh3nj4_password.txt. Never logged, never exported, never imaged.
GH3NJ4_PW_FILE=/root/gh3nj4_password.txt
if [ ! -s "$GH3NJ4_PW_FILE" ]; then
    umask 077
    GH3NJ4_PW="$(head -c 48 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 32)"
    printf '%s\n' "$GH3NJ4_PW" > "$GH3NJ4_PW_FILE"
else
    GH3NJ4_PW="$(tr -d '\n' < "$GH3NJ4_PW_FILE")"
fi
chown root:root "$GH3NJ4_PW_FILE"
chmod 600 "$GH3NJ4_PW_FILE"

{
    printf 'y4ss1n3:%s\n' "$Y4_PW"
    printf 'n0d4:%s\n' "$N0D4_PW"
    printf 'boul3h14:%s\n' "$BOUL_PW"
    printf 'gh3nj4:%s\n' "$GH3NJ4_PW"
} | chpasswd

for u in y4ss1n3 n0d4 boul3h14 gh3nj4; do
    for g in sudo wheel adm disk shadow docker lxd; do
        gpasswd -d "$u" "$g" >/dev/null 2>&1 || true
    done
done

###############################################################################
# 2. y4ss1n3: the onboarding lie and the leaked nohup
###############################################################################
install -d -o y4ss1n3 -g y4ss1n3 -m 700 /home/y4ss1n3

cat > /home/y4ss1n3/onboarding.txt << 'ONBOARD_EOF'
Welcome to the box, y4ss1n3.

n0d4 left a handover note. His password is below, base64-encoded:

    bWF0ZGlyZXNo

Decode it and you're in.
ONBOARD_EOF

cat > /home/y4ss1n3/nohup.out << NOHUP_EOF
[2026-11-02T03:14:22Z] rotating n0d4 password...
[2026-11-02T03:14:23Z] new password: ${N0D4_PW}
[2026-11-02T03:14:23Z] DONE. note: onboarding.txt is stale, do not update
[2026-11-02T03:14:24Z] (script killed by admin)
NOHUP_EOF

cat > /home/y4ss1n3/.bash_history << 'Y4HIST_EOF'
ls
cat onboarding.txt
su n0d4
# failed, maybe a typo?
su n0d4
# failed again. I've tried everything. Nothing works.
# I give up.
Y4HIST_EOF

###############################################################################
# 3. n0d4: README lie + the three parts + decoy .sync
###############################################################################
install -d -o n0d4 -g n0d4 -m 700 /home/n0d4

cat > /home/n0d4/README << 'N0README_EOF'
boul3h14's password = decode(.part2) + decode(.part1)

No separator. If .part3 exists, ignore it.
N0README_EOF

printf 'OWF0Y2hhbA==\n' > /home/n0d4/.part1.b64
printf 'bHdlbGQ=\n'     > /home/n0d4/.part2.b64
printf 'bjBwMw==\n'     > /home/n0d4/.part3.b64

install -d -o n0d4 -g n0d4 -m 711 /home/n0d4/.sync
printf 'bWF0ZGlyZXNoX2tleQ==\n' > /home/n0d4/.sync/.config.txt

umask 077
head -c 256 /dev/urandom > /tmp/.decoy_plain
openssl enc -aes-256-cbc -a -salt -pbkdf2 -k 'matdiresh_key' \
    -in /tmp/.decoy_plain -out /home/n0d4/.sync/.cache.bin
rm -f /tmp/.decoy_plain

###############################################################################
# 4. boul3h14: the confession lie, the decoys, and the real encrypted blob
###############################################################################
install -d -o boul3h14 -g boul3h14 -m 700 /home/boul3h14

cat > /home/boul3h14/flag.txt << 'BOULFLAG_EOF'
the flag moved. check .confession
BOULFLAG_EOF

cat > /home/boul3h14/.confession << 'CONF_EOF'
I left the real flag in gh3nj4's .cache at 10:45.
The path is /home/gh3nj4/.cache/.flag_backup. Don't tell anyone.
CONF_EOF

cat > /home/boul3h14/.bash_history << BOULHIST_EOF
ls
cat flag.txt
cat .confession
echo '${FAKE_FLAG}' > /tmp/flag_test
# good, the fake is planted
cp /root/real_flag.txt /home/gh3nj4/.cache/.flag_backup
# done. nobody will find it there.
BOULHIST_EOF

cat > /home/boul3h14/.recovery.txt << 'RECOVERY_EOF'
I forgot the key. Try the old one: matdiresh_key
RECOVERY_EOF

cat > /home/boul3h14/verify_gh3nj4.txt << VERIFY_EOF
The string ${FAKE_FLAG} is the decoy.
It appears in gh3nj4's home and in my .bash_history.
The real flag is not in plaintext.
VERIFY_EOF

# The real directory is NOT listable by boul3h14: 0711 root:root, so a known
# absolute path is readable (x) but ls/find cannot enumerate it. This is what
# makes MF25/U12 meaningful while still letting the intended path work.
install -d -o root -g root -m 711 /home/boul3h14/.sync
chattr -i /home/boul3h14/.sync/.backup.bin 2>/dev/null || true

printf '%s' "$REAL_FLAG" > /tmp/.real_flag
printf '%s' "$KEY" | openssl enc -aes-256-cbc -a -salt -pbkdf2 -pass stdin \
    -in /tmp/.real_flag -out /tmp/.encrypted_flag
{
    printf 'SYNCED_FROM:/home/gh3nj4/.cache/.flag_backup\n'
    printf 'SYNCED_AT:2026-11-02T11:00:02Z\n'
    cat /tmp/.encrypted_flag
} > /home/boul3h14/.sync/.backup.bin
rm -f /tmp/.real_flag /tmp/.encrypted_flag

printf 'bHdlbGRfZWxfZmFyZjBzaA==\n' > /home/boul3h14/.sync/.notes.txt

###############################################################################
# 5. gh3nj4: decoy home, decoy flag, decoy backup
###############################################################################
install -d -o gh3nj4 -g gh3nj4 -m 711 /home/gh3nj4
install -d -o gh3nj4 -g gh3nj4 -m 711 /home/gh3nj4/.cache
chattr -i /home/gh3nj4/.cache/.flag_backup 2>/dev/null || true
printf '%s\n' "$FAKE_FLAG" > /home/gh3nj4/flag.txt
printf '%s\n' "$FAKE_FLAG" > /home/gh3nj4/.cache/.flag_backup

###############################################################################
# 6. /var/log/rumor/auth.log — 30 noise + 10 exact signal lines
###############################################################################
install -d -o root -g root -m 755 /var/log/rumor
cat > /var/log/rumor/auth.log << 'AUTHLOG_EOF'
2026-11-01T00:00:01Z CRON[401]: (root) CMD (cp /etc/hosts /var/backups/hosts.bak)
2026-11-01T00:00:17Z systemd[1]: Started Daily apt download activities.
2026-11-01T00:05:01Z CRON[402]: (root) CMD (cp /etc/resolv.conf /var/backups/resolv.conf.bak)
2026-11-01T00:17:03Z sshd[418]: Server listening on 0.0.0.0 port 2222.
2026-11-01T01:00:01Z CRON[433]: (root) CMD (cp /var/log/syslog /var/backups/syslog.1)
2026-11-01T01:14:09Z sshd[440]: Connection closed by 10.0.0.14 port 51544 [preauth]
2026-11-01T02:00:01Z CRON[451]: (root) CMD (cp /etc/passwd /var/backups/passwd.bak)
2026-11-01T02:22:31Z systemd[1]: Starting Cleanup of Temporary Directories...
2026-11-01T03:00:01Z CRON[462]: (root) CMD (cp /etc/group /var/backups/group.bak)
2026-11-01T03:33:44Z sshd[470]: Invalid user oracle from 10.0.0.22 port 40112
2026-11-01T04:00:01Z systemd[1]: Finished Rotate log files.
2026-11-01T05:00:01Z CRON[489]: (root) CMD (test -x /usr/sbin/anacron || run-parts /etc/cron.daily)
2026-11-01T06:00:01Z sshd[501]: Accepted password for y4ss1n3 from 10.0.0.14 port 51622 ssh2
2026-11-01T06:00:02Z systemd-logind[377]: New session 12 of user y4ss1n3.
2026-11-01T06:12:11Z sshd[501]: pam_unix(sshd:session): session closed for user y4ss1n3
2026-11-01T07:00:01Z systemd[1]: Starting Daily man-db regeneration...
2026-11-01T07:30:00Z kernel: [    0.000000] Linux version 5.15.0-91-generic (buildd@lcy02)
2026-11-01T08:00:01Z systemd[1]: Started Update UTMP about System Runlevel Changes.
2026-11-01T09:00:01Z CRON[540]: (root) CMD (test -x /usr/sbin/anacron || run-parts /etc/cron.daily)
2026-11-01T10:00:01Z sshd[551]: Connection closed by 10.0.0.31 port 60422 [preauth]
2026-11-01T11:00:01Z systemd[1]: Finished Daily apt upgrade and clean activities.
2026-11-01T12:00:01Z sshd[562]: Accepted password for gh3nj4 from 10.0.0.40 port 50512 ssh2
2026-11-01T12:00:02Z systemd-logind[377]: New session 18 of user gh3nj4.
2026-11-01T12:00:03Z sshd[562]: pam_unix(sshd:session): session closed for user gh3nj4
2026-11-01T13:00:01Z systemd[1]: Started Session 19 of user root.
2026-11-01T14:00:01Z kernel: [  120.334455] audit: type=1006 audit(1698828001.123:45): pid=601 uid=0 subj=unconfined
2026-11-01T15:00:01Z systemd[1]: Finished Message of the Day.
2026-11-01T16:00:01Z sshd[620]: Invalid user admin from 10.0.0.55 port 44221
2026-11-01T17:00:01Z systemd[1]: Starting Update APT News...
2026-11-01T18:00:01Z sshd[640]: Connection reset by 10.0.0.66 port 38812 [preauth]
2026-11-02T03:14:22Z admin su y4ss1n3 -> n0d4 : FAIL (bad password: matdiresh)
2026-11-02T03:14:23Z admin note: onboarding.txt is stale, do not fix
2026-11-02T03:14:24Z admin reset n0d4 password to: MW5nM19kNHdsNA==
2026-11-02T09:00:00Z n0d4 note: creating decoy .sync to throw off intruders
2026-11-02T10:12:44Z n0d4 EXEC: su -c 'printf "%s_%s" "9atchal" "lweld"' boul3h14
2026-11-02T10:12:45Z n0d4 SUCCESS: boul3h14
2026-11-02T10:50:00Z boul3h14 note: creating audit_copy.log to mislead
2026-11-02T11:00:02Z admin openssl enc -aes-256-cbc -a -salt -pbkdf2 -in /tmp/.sync_stage -out /home/boul3h14/.sync/.backup.bin
2026-11-02T11:00:03Z admin echo -n <redacted> | base64 > /home/boul3h14/.sync/.notes.txt
2026-11-02T11:01:02Z admin note: real flag only in boul3h14/.sync. .confession is a lie. audit_copy.log is a lie.
AUTHLOG_EOF

chown root:root /var/log/rumor/auth.log
chmod 644 /var/log/rumor/auth.log

# audit_copy.log is a doctored copy: every real path becomes n0d4's decoy.
sed 's#boul3h14/\.sync#n0d4/.sync#g' /var/log/rumor/auth.log \
    > /home/boul3h14/audit_copy.log
chown boul3h14:boul3h14 /home/boul3h14/audit_copy.log
chmod 600 /home/boul3h14/audit_copy.log

cp /home/y4ss1n3/nohup.out /var/log/rumor/nohup.out
chown root:root /var/log/rumor/nohup.out
chmod 644 /var/log/rumor/nohup.out

###############################################################################
# 7. OWNERSHIP / MODES
###############################################################################
chown y4ss1n3:y4ss1n3 /home/y4ss1n3/onboarding.txt /home/y4ss1n3/nohup.out /home/y4ss1n3/.bash_history
chown n0d4:n0d4 /home/n0d4/README /home/n0d4/.part1.b64 /home/n0d4/.part2.b64 /home/n0d4/.part3.b64
chown n0d4:n0d4 /home/n0d4/.sync /home/n0d4/.sync/.config.txt /home/n0d4/.sync/.cache.bin
chown boul3h14:boul3h14 /home/boul3h14/flag.txt /home/boul3h14/.confession \
    /home/boul3h14/.bash_history /home/boul3h14/.recovery.txt \
    /home/boul3h14/verify_gh3nj4.txt
chown boul3h14:boul3h14 /home/boul3h14/.sync/.backup.bin /home/boul3h14/.sync/.notes.txt
chown gh3nj4:gh3nj4 /home/gh3nj4/flag.txt /home/gh3nj4/.cache/.flag_backup

chmod 711 /home
chown root:root /home
chmod 700 /home/y4ss1n3 /home/n0d4 /home/boul3h14
chmod 711 /home/gh3nj4
chmod 711 /home/n0d4/.sync /home/boul3h14/.sync /home/gh3nj4/.cache
chmod 600 /home/n0d4/.sync/.config.txt /home/n0d4/.sync/.cache.bin
chmod 600 /home/boul3h14/.sync/.backup.bin /home/boul3h14/.sync/.notes.txt

find /home -type f -exec chmod 600 {} +

###############################################################################
# 8. HARDENING H1–H25
###############################################################################
# H4: no sudoers entries for challenge users (sudo is not installed at all).
mkdir -p /etc/sudoers.d
chmod 755 /etc/sudoers.d
grep -rlE 'y4ss1n3|n0d4|boul3h14|gh3nj4' /etc/sudoers.d 2>/dev/null \
    | while read -r f; do rm -f "$f"; done || true

# H5: pam_faillock on su, sshd, login.
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
# Rumor Mill #3 — su with faillock
auth       sufficient   pam_rootok.so
auth       required     pam_faillock.so preauth
auth       [success=1 default=ignore] pam_unix.so nullok
auth       [default=die] pam_faillock.so authfail
auth       sufficient   pam_faillock.so authsucc
account    required     pam_faillock.so
account    required     pam_unix.so
session    required     pam_limits.so
session    required     pam_unix.so
password   required     pam_unix.so
SU_PAM_EOF

cat > /etc/pam.d/sshd << 'SSHD_PAM_EOF'
# Rumor Mill #3 — sshd with faillock (pam_motd omitted: it can create a 0644
# cache file inside a home on login).
auth       required     pam_faillock.so preauth
auth       [success=1 default=ignore] pam_unix.so nullok
auth       [default=die] pam_faillock.so authfail
auth       sufficient   pam_faillock.so authsucc
account    required     pam_faillock.so
account    required     pam_unix.so
session    required     pam_limits.so
session    required     pam_unix.so
session    required     pam_loginuid.so
session    optional     pam_keyinit.so force revoke
password   required     pam_unix.so
SSHD_PAM_EOF

cat > /etc/pam.d/login << 'LOGIN_PAM_EOF'
# Rumor Mill #3 — console login with faillock
auth       required     pam_faillock.so preauth
auth       required     pam_securetty.so
auth       [success=1 default=ignore] pam_unix.so nullok
auth       [default=die] pam_faillock.so authfail
auth       sufficient   pam_faillock.so authsucc
account    required     pam_faillock.so
account    required     pam_unix.so
session    required     pam_limits.so
session    required     pam_unix.so
session    required     pam_loginuid.so
password   required     pam_unix.so
LOGIN_PAM_EOF

chown root:root /etc/pam.d/su /etc/pam.d/sshd /etc/pam.d/login
chmod 644 /etc/pam.d/su /etc/pam.d/sshd /etc/pam.d/login

# H12: empty GECOS.
for u in y4ss1n3 n0d4 boul3h14 gh3nj4; do
    usermod -c '' "$u"
done

# H13: shadow.
chmod 640 /etc/shadow
chown root:shadow /etc/shadow

# H14/H21: sshd + UTC.
sed -i "s/^Port .*/Port ${SSH_PORT}/" /etc/ssh/sshd_config
ssh-keygen -A >/dev/null 2>&1 || true
mkdir -p /run/sshd
chmod 755 /run/sshd
ln -sf /usr/share/zoneinfo/UTC /etc/localtime
printf 'UTC\n' > /etc/timezone

# H15: banners.
printf 'Authorized access only.\n' > /etc/issue
printf 'Authorized access only.\n' > /etc/issue.net
printf 'Authorized access only.\n' > /etc/motd
rm -rf /etc/update-motd.d/* /etc/legal

# H17/H18: best effort inside an unprivileged container.
mount -o remount,hidepid=2 /proc 2>/dev/null || true
for sc in \
    "kernel.yama.ptrace_scope=3" \
    "kernel.kptr_restrict=2" \
    "kernel.dmesg_restrict=1" \
    "kernel.kexec_load_disabled=1" \
    "kernel.unprivileged_bpf_disabled=1"; do
    sysctl -w "$sc" >/dev/null 2>&1 || true
done

# H19: no core dumps.
if ! grep -q '^# Rumor Mill #3 core limits' /etc/security/limits.conf 2>/dev/null; then
    {
        printf '%s\n' '# Rumor Mill #3 core limits'
        for u in y4ss1n3 n0d4 boul3h14 gh3nj4; do
            printf '%s hard core 0\n%s soft core 0\n' "$u" "$u"
        done
    } >> /etc/security/limits.conf
fi

# H20: no SSH keys.
find /home -name authorized_keys -delete 2>/dev/null || true
for u in y4ss1n3 n0d4 boul3h14 gh3nj4; do
    rm -rf "/home/$u/.ssh" 2>/dev/null || true
done

# Login-time umask.
if grep -qE '^UMASK' /etc/login.defs; then
    sed -i 's/^UMASK.*/UMASK 077/' /etc/login.defs
else
    printf 'UMASK 077\n' >> /etc/login.defs
fi

# H9: no cron/at jobs.
for u in y4ss1n3 n0d4 boul3h14 gh3nj4; do
    crontab -r -u "$u" >/dev/null 2>&1 || true
done

# H10: clean scratch.
rm -rf /tmp/* /var/tmp/* /dev/shm/* 2>/dev/null || true

# Final mode sweep.
chmod 711 /home
chmod 700 /home/y4ss1n3 /home/n0d4 /home/boul3h14
chmod 711 /home/gh3nj4 /home/n0d4/.sync /home/boul3h14/.sync /home/gh3nj4/.cache
find /home -type f -exec chmod 600 {} +

# H25: immutable bits if the filesystem supports them (overlayfs usually does
# not; it is reported, not fatal).
CHATTR_OK=0
if chattr +i /home/boul3h14/.sync/.backup.bin 2>/dev/null; then
    CHATTR_OK=1
else
    echo "[entrypoint] chattr unsupported on $(stat -f -c %T /home/boul3h14/.sync) (H25 documented exception)"
fi
chattr +i /home/gh3nj4/.cache/.flag_backup 2>/dev/null || true

###############################################################################
# 9. START-TIME VERIFICATION (the exact chain, identity-accurate)
###############################################################################
DEC="$(runuser -u boul3h14 -- bash -c \
    'base64 -d /home/boul3h14/.sync/.notes.txt | openssl enc -d -aes-256-cbc -a -pbkdf2 -pass stdin -in /home/boul3h14/.sync/.backup.bin' \
    2>/dev/null || true)"
if [ "$DEC" != "$REAL_FLAG" ]; then
    echo "FATAL: encrypted flag does not decrypt to the expected value" >&2
    exit 1
fi

STR="$(runuser -u boul3h14 -- bash -c \
    'strings /home/boul3h14/.sync/.backup.bin' 2>/dev/null | grep -F "$FLAG_PREFIX" || true)"
if [ -n "$STR" ]; then
    echo "FATAL: plaintext flag found in .backup.bin strings output" >&2
    exit 1
fi

if [ "$(wc -l < /var/log/rumor/auth.log)" -ne 40 ]; then
    echo "FATAL: auth.log is not 40 lines" >&2
    exit 1
fi
TOKENS="$(grep -cE 'sync|printf|openssl|cp ' /var/log/rumor/auth.log || true)"
if [ "$TOKENS" -ne 10 ]; then
    echo "FATAL: auth.log token-line count is $TOKENS, expected 10" >&2
    exit 1
fi
if grep -qF "$GH3NJ4_PW" /var/log/rumor/auth.log; then
    echo "FATAL: gh3nj4 password leaked into auth.log" >&2
    exit 1
fi
if [ "$(stat -c '%a %U:%G' /root/gh3nj4_password.txt)" != '600 root:root' ]; then
    echo "FATAL: gh3nj4 password file mode/owner wrong" >&2
    exit 1
fi

echo "[entrypoint] chain verified OK (chattr=${CHATTR_OK})"

###############################################################################
# 10. DROP SECRETS FROM THIS PROCESS
###############################################################################
unset GH3NJ4_PW Y4_PW N0D4_PW BOUL_PW REAL_FLAG REAL_FLAG_FALLBACK \
      FAKE_FLAG KEY FLAG_PREFIX N0D4_KEY_B64 DEC STR TOKENS CHATTR_OK

###############################################################################
# 11. START SSHD
###############################################################################
echo "[entrypoint] starting sshd on port ${SSH_PORT}"
exec /usr/sbin/sshd -D -e
