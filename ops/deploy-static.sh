#!/usr/bin/env bash
# Deploy a STATIC (non-instanced) challenge as a container behind the
# docker-instancer's Traefik on the challs VM, reachable at
# <name>.<INSTANCES_HOST>.
#
# Two shapes:
#   - HTTP (default): web + websecure entrypoints → container port 8080.
#   - Raw TCP (manifest `tcpPort:`): a Traefik TCP router on the `tcp`
#     entrypoint (:1337, published as the mapped tcp-ssl port) matching
#     HostSNI(<INTERNAL_HOST>), forwarding to the declared container port.
#     Traefik terminates TLS with the wildcard cert, so the player wraps the
#     client, e.g.
#       ssh -o ProxyCommand='openssl s_client -quiet -servername %h -connect %h:%p' ...
#
# Triggered by CI (.github/workflows/challenges.yml, deploy job) for any merged
# challenge whose chall.yaml has instanced: false. Authors never see this.
#
# Env: HOST_SSH (root@ssh.alpha.openscaler.net), HOST_SSH_PORT (mapped ssh port)
#      INTERNAL_HOST (e.g. hello.challs.ingeniums.club), IMAGE,
#      TRAEFIK_NETWORK (the instancer network the traefik joins),
#      TCP_PORT (container port for raw-TCP challenges; empty for HTTP).
set -euo pipefail

IMAGE=${IMAGE:?}; INTERNAL_HOST=${INTERNAL_HOST:?}; NAME=${NAME:?}
TRAEFIK_NETWORK=${TRAEFIK_NETWORK:-docker-instancer_tiny-network}
PORT=8080   # containerPort for static web challs (fixed convention)
TCP_PORT=${TCP_PORT:-}
DECLARED_FLAG=${DECLARED_FLAG:?}
[[ "$DECLARED_FLAG" == ingehack{* ]] || { echo "FAIL: static flag must match the ingehack{...} format" >&2; exit 1; }

if [[ -n "$TCP_PORT" ]]; then
  printf 'Deploy %s (raw TCP %s)\n  image: %s\n  host: %s\n' "$NAME" "$TCP_PORT" "$IMAGE" "$INTERNAL_HOST"
  ssh -o StrictHostKeyChecking=accept-new -p "${HOST_SSH_PORT:?}" "${HOST_SSH:?}" \
    "set -e
     docker rm -f 'static-$NAME' 2>/dev/null || true
     docker run -d --name 'static-$NAME' \
       --network '$TRAEFIK_NETWORK' \
       --restart unless-stopped \
       -e 'FLAG=$DECLARED_FLAG' \
       -l 'traefik.enable=true' \
       -l 'traefik.tcp.routers.$NAME-tcp.rule=HostSNI(\`$INTERNAL_HOST\`)' \
       -l 'traefik.tcp.routers.$NAME-tcp.entryPoints=tcp' \
       -l 'traefik.tcp.routers.$NAME-tcp.tls=true' \
       -l 'traefik.tcp.routers.$NAME-tcp.service=$NAME-tcp' \
       -l 'traefik.tcp.services.$NAME-tcp.loadbalancer.server.port=$TCP_PORT' \
       '$IMAGE'
     docker inspect 'static-$NAME' --format '{{.State.Status}}'"
  printf 'deployed %s at %s (traefik labels: tcp-ssl)\n' "$NAME" "$INTERNAL_HOST"
  exit 0
fi

printf 'Deploy %s\n  image: %s\n  host: %s\n' "$NAME" "$IMAGE" "$INTERNAL_HOST"
ssh -o StrictHostKeyChecking=accept-new -p "${HOST_SSH_PORT:?}" "${HOST_SSH:?}" \
  "set -e
   docker rm -f 'static-$NAME' 2>/dev/null || true
   docker run -d --name 'static-$NAME' \
     --network '$TRAEFIK_NETWORK' \
     --restart unless-stopped \
     -e 'FLAG=$DECLARED_FLAG' \
     -l 'traefik.enable=true' \
     -l 'traefik.http.routers.$NAME-web.rule=Host(\`$INTERNAL_HOST\`)' \
     -l 'traefik.http.routers.$NAME-web.entryPoints=web' \
     -l 'traefik.http.routers.$NAME-web.service=$NAME-$PORT' \
     -l 'traefik.http.routers.$NAME-https.rule=Host(\`$INTERNAL_HOST\`)' \
     -l 'traefik.http.routers.$NAME-https.entryPoints=websecure' \
     -l 'traefik.http.routers.$NAME-https.service=$NAME-$PORT' \
     -l 'traefik.http.routers.$NAME-https.tls=true' \
     -l 'traefik.http.services.$NAME-$PORT.loadbalancer.server.port=$PORT' \
     '$IMAGE'
   docker inspect 'static-$NAME' --format '{{.State.Status}}'"
printf 'deployed %s at %s (traefik labels: web + websecure/tls)\n' "$NAME" "$INTERNAL_HOST"
