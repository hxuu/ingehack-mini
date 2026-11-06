#!/usr/bin/env bash
# escape — container role entrypoint
set -euo pipefail

ROLE="${ROLE:-entry}"
case "$ROLE" in
    entry) exec /opt/escape/entry-start.sh ;;
    db)    exec /opt/escape/db-start.sh ;;
    *) echo "entrypoint: unknown ROLE '${ROLE}' (want entry|db)" >&2; exit 1 ;;
esac
