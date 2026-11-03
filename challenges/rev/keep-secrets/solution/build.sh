#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [ -z "${JAVA_HOME:-}" ]; then
  export JAVA_HOME=/usr/lib/jvm/java-17-openjdk
fi
export ANDROID_HOME="${ANDROID_HOME:-$HOME/Android/Sdk}"
export ANDROID_SDK_ROOT="$ANDROID_HOME"

if [ ! -d "$ANDROID_HOME" ]; then
  echo "Android SDK not found at $ANDROID_HOME" >&2
  exit 1
fi

python3 gen_secrets.py

cd app
printf 'sdk.dir=%s\n' "$ANDROID_HOME" > local.properties
./gradlew --no-daemon :app:assembleRelease

BUILD_TOOLS="$(find "$ANDROID_HOME/build-tools" -maxdepth 1 -mindepth 1 -type d | sort -V | tail -1)"
UNSIGNED="app/build/outputs/apk/release/app-release-unsigned.apk"
ALIGNED="app/build/outputs/apk/release/app-release-aligned.apk"
OUT="../../files/keep-secrets.apk"
KEYSTORE="keystore.jks"

if [ ! -f "$KEYSTORE" ]; then
  "$JAVA_HOME/bin/keytool" -genkeypair \
    -keystore "$KEYSTORE" \
    -alias keepsecrets \
    -keyalg RSA \
    -keysize 2048 \
    -validity 10000 \
    -storepass keepsecrets \
    -keypass keepsecrets \
    -dname "CN=Ingehack, OU=CTF, O=Ingehack, L=Tunis, C=TN"
fi

mkdir -p ../../files
"$BUILD_TOOLS/zipalign" -f -p 4 "$UNSIGNED" "$ALIGNED"
"$BUILD_TOOLS/apksigner" sign \
  --ks "$KEYSTORE" \
  --ks-key-alias keepsecrets \
  --ks-pass pass:keepsecrets \
  --key-pass pass:keepsecrets \
  --v4-signing-enabled false \
  --out "$OUT" \
  "$ALIGNED"
"$BUILD_TOOLS/apksigner" verify --verbose --print-certs "$OUT"
"$BUILD_TOOLS/zipalign" -c -v 4 "$OUT"
"$BUILD_TOOLS/aapt2" dump badging "$OUT" | sed -n '1,6p'

echo
echo "Signed APK: $(cd ../.. && pwd)/files/keep-secrets.apk"
