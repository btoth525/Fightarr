#!/bin/sh
# Fightarr entrypoint — honour PUID/PGID/UMASK so files written to /config,
# /downloads, and /plex are owned by the Unraid user, not root.
set -e

PUID=${PUID:-99}
PGID=${PGID:-100}
UMASK=${UMASK:-002}

umask "$UMASK"

# Create the fightarr group/user if they don't exist at the requested IDs.
if ! getent group fightarr > /dev/null 2>&1; then
    addgroup -g "$PGID" fightarr 2>/dev/null || addgroup --gid "$PGID" fightarr
fi
if ! getent passwd fightarr > /dev/null 2>&1; then
    adduser -u "$PUID" -G fightarr -H -D fightarr 2>/dev/null || \
    adduser --uid "$PUID" --gid "$PGID" --home /app --no-create-home --disabled-password --gecos "" fightarr
fi

# Ensure data dirs are accessible by our user
chown -R "$PUID:$PGID" /config /var/log/supervisor 2>/dev/null || true

exec gosu "$PUID:$PGID" "$@"
