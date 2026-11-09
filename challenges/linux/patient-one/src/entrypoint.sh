#!/bin/bash
set -e

echo "[*] Initializing ESI-SBA Linux Domain Workstation..."

# 1. Create Groups & Users
getent group sba-faculty >/dev/null 2>&1 || groupadd -g 10001 sba-faculty
id -u a.amrane >/dev/null 2>&1 || useradd -u 10001 -g sba-faculty -m -s /bin/bash a.amrane
usermod -p "$(openssl passwd -6 'Amrane#SBA2026')" a.amrane

getent group svc_ad_sync >/dev/null 2>&1 || groupadd -g 10002 svc_ad_sync
id -u svc_ad_sync >/dev/null 2>&1 || useradd -u 10002 -g svc_ad_sync -m -s /bin/bash svc_ad_sync
passwd -l svc_ad_sync || true

# 2. Permissions for Directories & Scripts
mkdir -p /opt/esi-sba/hooks
rm -rf /opt/esi-sba/hooks/*

# Seed realistic backup pre-synchronization routine hooks
cat << 'EOF' > /opt/esi-sba/hooks/01-storage-check.sh
#!/bin/bash
# ESI-SBA Backup Subsystem: Volume Health & Storage Check
MOUNT_POINT="/"
THRESHOLD=90
CURRENT_USAGE=$(df -P "$MOUNT_POINT" 2>/dev/null | tail -1 | awk '{print $5}' | tr -d '%')
if [ -n "$CURRENT_USAGE" ] && [ "$CURRENT_USAGE" -gt "$THRESHOLD" ]; then
    echo "[!] WARNING: Storage utilization exceeds threshold ($CURRENT_USAGE% on $MOUNT_POINT)."
fi
EOF

cat << 'EOF' > /opt/esi-sba/hooks/02-lock-sync.sh
#!/bin/bash
# ESI-SBA Backup Subsystem: Lock & Session Concurrency State
LOCK_DIR="/run/sba-backup"
mkdir -p "$LOCK_DIR" 2>/dev/null || true
touch "$LOCK_DIR/sync.lock" 2>/dev/null || true
EOF

chmod 0755 /opt/esi-sba/hooks/*.sh
chown -R svc_ad_sync:svc_ad_sync /opt/esi-sba
chmod 0775 /opt/esi-sba/hooks

cp /etc/sudoers_esi /etc/sudoers.d/esi_sba
chmod 0440 /etc/sudoers.d/esi_sba

cp /usr/local/bin/sba-backup.src /usr/local/bin/sba-backup
chmod 0755 /usr/local/bin/sba-backup

# 3. Configure Kerberos KDC
mkdir -p /var/lib/krb5kdc /etc/krb5kdc
cp /configs/kdc.conf /etc/krb5kdc/kdc.conf
cp /configs/krb5.conf /etc/krb5.conf

# Initialize KDC database if not already present
if [ ! -f /var/lib/krb5kdc/principal ]; then
    echo "[*] Generating Kerberos KDC Database for ESI-SBA.DZ..."
    kdb5_util create -s -P MasterKey#Sba2026!
fi

# Add Principals
kadmin.local -q "addprinc -randkey host/localhost@ESI-SBA.DZ" || true
kadmin.local -q "addprinc -randkey host/127.0.0.1@ESI-SBA.DZ" || true
kadmin.local -q "addprinc -randkey svc_ad_sync@ESI-SBA.DZ" || true

# Export host keytab for OpenSSH GSSAPI
kadmin.local -q "ktadd -k /etc/krb5.keytab host/localhost@ESI-SBA.DZ"
kadmin.local -q "ktadd -k /etc/krb5.keytab host/127.0.0.1@ESI-SBA.DZ"
chmod 0644 /etc/krb5.keytab

# Export service account keytab temporarily to embed into SSSD cache
mkdir -p /tmp/setup
kadmin.local -q "ktadd -k /tmp/setup/svc.keytab svc_ad_sync@ESI-SBA.DZ"

# 4. Create SSSD LDB Cache Database (/var/lib/sss/db/cache_ESI-SBA.DZ.ldb)
mkdir -p /var/lib/sss/db
B64_KEYTAB=$(base64 -w 0 /tmp/setup/svc.keytab)

cat <<EOF > /tmp/setup/cache.ldif
dn: @INDEXLIST
@IDXATTR: sAMAccountName
@IDXATTR: name
@IDXATTR: objectSID

dn: cn=svc_ad_sync,cn=users,cn=ESI-SBA.DZ,cn=sysdb
objectClass: user
name: svc_ad_sync
sAMAccountName: svc_ad_sync
userPrincipalName: svc_ad_sync@ESI-SBA.DZ
uidNumber: 10002
gidNumber: 10002
gecos: ESI-SBA Directory Sync Service
homeDirectory: /home/svc_ad_sync
loginShell: /bin/bash
userKeytab:: ${B64_KEYTAB}

dn: cn=a.amrane,cn=users,cn=ESI-SBA.DZ,cn=sysdb
objectClass: user
name: a.amrane
sAMAccountName: a.amrane
userPrincipalName: a.amrane@ESI-SBA.DZ
uidNumber: 10001
gidNumber: 10001
gecos: Prof. A. AMRANE
homeDirectory: /home/a.amrane
loginShell: /bin/bash
EOF

# Initialize LDB file
rm -f /var/lib/sss/db/cache_ESI-SBA.DZ.ldb
ldbadd -H /var/lib/sss/db/cache_ESI-SBA.DZ.ldb /tmp/setup/cache.ldif

# Set realistic permissions on SSSD database (accessible and readable by sba-faculty)
chown -R root:sba-faculty /var/lib/sss/db
chmod 0750 /var/lib/sss/db
chmod 0660 /var/lib/sss/db/cache_ESI-SBA.DZ.ldb

# Scrub temporary keytab file from disk
rm -rf /tmp/setup

# 5. Plant Flag in /flag
# Do NOT write this as "${RCTF_FLAG:-ingehack{...}: the first `}` in the
# default ends the expansion, so an injected RCTF_FLAG comes out with an
# extra trailing `}` and never matches the submitted flag.
FLAG_VALUE="${RCTF_FLAG:-}"
if [ -z "$FLAG_VALUE" ]; then
    FLAG_VALUE='ingehack{K3rb3r0s_SSSD_LDB_GSS4P1_R0ut1n3_1nj3ct10n_h0w_3duc4t1v3_w4s_th4t_!}'
fi
echo "$FLAG_VALUE" > /flag
chmod 0400 /flag
chown root:root /flag
ln -sf /flag /flag.txt
ln -sf /flag /root/flag.txt

# 6. SSSD Configuration & Crontab
mkdir -p /etc/sssd
cat <<'EOF' > /etc/sssd/sssd.conf
[sssd]
services = nss, pam
config_file_version = 2
domains = ESI-SBA.DZ

[domain/ESI-SBA.DZ]
id_provider = ad
auth_provider = krb5
chpass_provider = krb5
access_provider = ad
krb5_realm = ESI-SBA.DZ
krb5_server = 127.0.0.1
cache_credentials = true
entry_cache_timeout = 86400
EOF
chmod 0600 /etc/sssd/sssd.conf

# Crontab schedule for faculty backup service
echo "0 * * * * svc_ad_sync /usr/local/bin/sba-backup --run" > /etc/cron.d/esi_sba_backup
chmod 0644 /etc/cron.d/esi_sba_backup

# 7. Self-destruct temporary setup files and entrypoint
rm -rf /tmp/* /tmp/.* 2>/dev/null || true
rm -rf /configs /entrypoint.sh
chmod 0700 /root

# 8. Start Services
echo "[*] Starting Kerberos KDC daemon..."
krb5kdc

echo "[*] Starting OpenSSH server daemon..."
mkdir -p /run/sshd
exec /usr/sbin/sshd -D -e
