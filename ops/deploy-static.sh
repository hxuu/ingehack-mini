#!/usr/bin/env bash
# Deploy a STATIC (non-instanced) challenge as a container behind the
# docker-instancer's Traefik on the challs VM, reachable at
# <name>.<INSTANCES_HOST>:<public http port>.
#
# Triggered by CI (.github/workflows/challenges.yml, deploy job) for any merged
# challenge whose chall.yaml has instanced: false. Authors never see this.
#
# Env: HOST_SSH (root@ssh.alpha.openscaler.net), HOST_SSH_PORT (mapped ssh port)
#      INTERNAL_HOST (e.g. hello.challs.ingeniums.club), IMAGE (ghcr public),
#      TRAEFIK_NETWORK (the instancer network the traefik joins).
set -euo pipefail

IMAGE=${IMAGE:?}; INTERNAL_HOST=${INTERNAL_HOST:?}; NAME=${NAME:?}
TRAEFIK_NETWORK=${TRAEFIK_NETWORK:-docker-instancer_tiny-network}
PORT=8080   # containerPort for static web challs (fixed convention)
DECLARED_FLAG=${DECLARED_FLAG:?}
[[ "$DECLARED_FLAG" == ingehack{* ]] || { echo "FAIL: static flag must match the ingehack{...} format" >&2; exit 1; }

printf 'Deploy %s\n  image: %s\n  host: %s\n' "$NAME" "$IMAGE" "$INTERNAL_HOST"
ssh -o StrictHostKeyChecking=accept-new -p "${HOST_SSH_PORT:?}" "${HOST_SSH:?}" \
  "set -e
   docker rm -f 'static-$NAME' 2>/dev/null || true
   docker run -d --name 'static-$NAME' \
     --network '$TRAEFIK_NETWORK' \
     --restart unless-stopped \
     -e 'FLAG=$DECLARED_FLAG' \
     -l 'traefik.enable=true' \
     -l 'traefik.http.routers.$NAME.rule=Host(\`$INTERNAL_HOST\`)' \
     -l 'traefik.http.routers.$NAME.entryPoints=web' \
     -l 'traefik.http.services.$NAME-$PORT.loadbalancer.server.port=$PORT' \
     '$IMAGE'
   docker inspect 'static-$NAME' --format '{{.State.Status}}'"
printf 'deployed %s at %s (traefik labels, entrypoint web)\n' "$NAME" "$INTERNAL_HOST"
