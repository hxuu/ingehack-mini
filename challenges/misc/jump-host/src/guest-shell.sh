#!/bin/sh
# sshd runs this as the guest login shell. Set the restricted PATH first,
# then hand over to bash in restricted mode.
export PATH=/home/guest/bin
exec /bin/bash -r "$@"
