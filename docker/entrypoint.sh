#!/bin/sh
# Fightarr entrypoint — supervisord runs as root so it can manage processes
# and write log pipes. The actual uvicorn process runs as PUID:PGID via the
# supervisord 'user=' directive so all files it writes are owned correctly.
set -e

PUID=${PUID:-99}
PGID=${PGID:-100}
UMASK=${UMASK:-002}

umask "$UMASK"

# Ensure the config and log dirs are writable by the target user.
# /downloads and /plex are host bind-mounts already owned by the host user.
chown -R "${PUID}:${PGID}" /config /var/log/supervisor 2>/dev/null || true

echo "Starting Fightarr (uvicorn will run as UID=${PUID} GID=${PGID}, UMASK=${UMASK})"
exec "$@"
