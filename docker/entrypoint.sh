#!/bin/sh
# Fightarr entrypoint — honour PUID/PGID/UMASK so files written to /config,
# /downloads, and /plex are owned by the Unraid user (nobody:users = 99:100),
# not root.
#
# gosu accepts raw numeric UID:GID — no adduser/addgroup calls needed, which
# avoids the "GID already in use" crash on systems where GID 100 (users) is
# already in the container's /etc/group.
set -e

PUID=${PUID:-99}
PGID=${PGID:-100}
UMASK=${UMASK:-002}

umask "$UMASK"

# Fix ownership of config + log dirs so the process can write to them.
# /downloads and /plex are bind-mounts owned by the host user already.
chown -R "${PUID}:${PGID}" /config /var/log/supervisor 2>/dev/null || true

echo "Starting Fightarr as UID=${PUID} GID=${PGID} UMASK=${UMASK}"
exec gosu "${PUID}:${PGID}" "$@"
