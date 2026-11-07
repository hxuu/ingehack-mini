#!/usr/bin/env bash
# ROLE=entry — just sshd. The interesting caps come from the service
# (cap_add: NET_ADMIN on top of the Docker default set) so `capsh --print`
# shows the decoy the players are meant to chase.
exec /usr/sbin/sshd -D -e
