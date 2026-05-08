#!/bin/sh
# Fightarr entrypoint
# supervisord runs as root (it must, to manage processes and write pipes).
# The uvicorn program inside supervisord drops to PUID:PGID via user= directive,
# but supervisord needs the UID to exist in /etc/passwd first.
set -e

PUID=${PUID:-99}
PGID=${PGID:-100}
UMASK=${UMASK:-002}

umask "$UMASK"

# Create group for PGID if it doesn't already exist
if ! getent group "$PGID" > /dev/null 2>&1; then
    groupadd --gid "$PGID" fightarr
fi

# Create user for PUID if it doesn't already exist
# (supervisord user= requires the UID to be in /etc/passwd)
if ! getent passwd "$PUID" > /dev/null 2>&1; then
    useradd --uid "$PUID" --gid "$PGID" \
            --home-dir /config --no-create-home \
            --shell /sbin/nologin \
            fightarr
fi

# Fix ownership of config and log dirs
chown -R "${PUID}:${PGID}" /config /var/log/supervisor 2>/dev/null || true

echo "Starting Fightarr as UID=${PUID} GID=${PGID} UMASK=${UMASK}"
exec "$@"
