#!/bin/bash
###############################################################################
# verify_solution.sh — Automated solver for Rumor Mill #2
# Runs as root inside the container, simulates y4ss1n3's solve path.
# Prints the real flag and exits 0 on success.
###############################################################################
set -euo pipefail

echo "=== Rumor Mill #2 — Automated Solver ==="
echo ""

# Step 1: Read onboarding.txt as y4ss1n3
echo "[Step 1] Reading onboarding.txt as y4ss1n3..."
ONBOARD=$(su -s /bin/bash -c 'cat /home/y4ss1n3/onboarding.txt' y4ss1n3)
echo "$ONBOARD" | head -5

# Step 2: Decode the base64 from onboarding → K4r4k0_1962
echo ""
echo "[Step 2] Decoding base64 from onboarding..."
OLD_PW=$(echo 'SzRyNGswXzE5NjI=' | base64 -d)
echo "Decoded: $OLD_PW"

# Step 3: Try su n0d4 with old password — should FAIL
echo ""
echo "[Step 3] Trying su n0d4 with old password (expect failure)..."
if echo "$OLD_PW" | su -s /bin/bash -c 'id' n0d4 2>&1 | grep -q 'uid='; then
    echo "ERROR: Old password worked — this should not happen!"
    exit 1
else
    echo "Correctly failed: old password is stale."
fi

# Step 4: Read .bash_history → points to .env
echo ""
echo "[Step 4] Reading .bash_history..."
su -s /bin/bash -c 'cat /home/y4ss1n3/.bash_history' y4ss1n3

# Step 5: Read .env → get rotated password
echo ""
echo "[Step 5] Reading .env..."
ENV_CONTENT=$(su -s /bin/bash -c 'cat /home/y4ss1n3/.env' y4ss1n3)
echo "$ENV_CONTENT"
N0D4_B64=$(echo "$ENV_CONTENT" | grep 'N0D4_B64=' | cut -d= -f2)
echo "Extracted base64: $N0D4_B64"

# Step 6: Decode → K4r4k0_1962_v2
N0D4_PW=$(echo "$N0D4_B64" | base64 -d)
echo "Decoded password: $N0D4_PW"

# Step 7: su n0d4 — should succeed
echo ""
echo "[Step 7] su n0d4 with correct password..."
N0D4_ID=$(echo "$N0D4_PW" | su -s /bin/bash -c 'id' n0d4 2>&1)
echo "$N0D4_ID"
if ! echo "$N0D4_ID" | grep -q 'uid='; then
    echo "ERROR: Cannot su to n0d4!"
    exit 1
fi

# Step 8: Read n0d4's README
echo ""
echo "[Step 8] Reading n0d4's README..."
echo "$N0D4_PW" | su -s /bin/bash -c 'cat /home/n0d4/README' n0d4

# Step 9: Read .part_order and decode
echo ""
echo "[Step 9] Reading .part_order..."
PART_ORDER_B64=$(echo "$N0D4_PW" | su -s /bin/bash -c 'cat /home/n0d4/.part_order' n0d4)
echo "Raw: $PART_ORDER_B64"
PART_ORDER=$(echo "$PART_ORDER_B64" | base64 -d)
echo "Decoded order: $PART_ORDER"

# Step 10: Read parts in order (2,3,1)
echo ""
echo "[Step 10] Reading parts in order: $PART_ORDER"
PART2_B64=$(echo "$N0D4_PW" | su -s /bin/bash -c 'cat /home/n0d4/.part2.b64' n0d4)
PART3_B64=$(echo "$N0D4_PW" | su -s /bin/bash -c 'cat /home/n0d4/.part3.b64' n0d4)
PART1_B64=$(echo "$N0D4_PW" | su -s /bin/bash -c 'cat /home/n0d4/.part1.b64' n0d4)

PART2=$(echo "$PART2_B64" | base64 -d)
PART3=$(echo "$PART3_B64" | base64 -d)
PART1=$(echo "$PART1_B64" | base64 -d)

echo ".part2 → $PART2"
echo ".part3 → $PART3"
echo ".part1 → $PART1"

# Step 11: Join in order 2,3,1 with underscores
BOUL_PW="${PART2}_${PART3}_${PART1}"
echo ""
echo "[Step 11] boul3h14 password: $BOUL_PW"

# Step 12: su boul3h14
echo ""
echo "[Step 12] su boul3h14..."
BOUL_ID=$(echo "$BOUL_PW" | su -s /bin/bash -c 'id' boul3h14 2>&1)
echo "$BOUL_ID"
if ! echo "$BOUL_ID" | grep -q 'uid='; then
    echo "ERROR: Cannot su to boul3h14!"
    exit 1
fi

# Step 13: Read encrypted flag and README
echo ""
echo "[Step 13] Reading boul3h14's files..."
echo "$BOUL_PW" | su -s /bin/bash -c 'cat /home/boul3h14/README' boul3h14
echo ""

# Step 14: Read .key.b64 and decode
KEY_B64=$(echo "$BOUL_PW" | su -s /bin/bash -c 'cat /home/boul3h14/.key.b64' boul3h14)
echo "Key (base64): $KEY_B64"
KEY=$(echo "$KEY_B64" | base64 -d)
echo "Key (decoded): $KEY"

# Step 15: Decrypt the flag
echo ""
echo "[Step 15] Decrypting flag..."
FLAG=$(echo "$BOUL_PW" | su -s /bin/bash -c "cd /home/boul3h14 && openssl enc -d -aes-256-cbc -a -pbkdf2 -in flag.txt -k '$KEY'" boul3h14 2>&1)

echo ""
echo "========================================="
echo "FLAG: $FLAG"
echo "========================================="

if [ "$FLAG" = 'ingehack{rum0rs_4r3_b4s364_4ll_th3_w4y_d0wn}' ]; then
    echo "SUCCESS: Real flag recovered!"
    exit 0
else
    echo "FAILURE: Flag mismatch!"
    echo "Expected: ingehack{rum0rs_4r3_b4s364_4ll_th3_w4y_d0wn}"
    echo "Got:      $FLAG"
    exit 1
fi
