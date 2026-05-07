# ── Stage 1: Build React frontend ────────────────────────────────────
FROM node:20-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --prefer-offline
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Install Python dependencies ─────────────────────────────
FROM python:3.12-slim AS backend-deps
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libxml2-dev libxslt-dev \
    && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# ── Stage 3: Final image ─────────────────────────────────────────────
FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/btoth525/Fightarr"
LABEL org.opencontainers.image.description="UFC event manager for Usenet and Plex"
LABEL org.opencontainers.image.licenses="GPL-3.0"

RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx supervisor libxml2 libxslt1.1 gosu \
    && rm -rf /var/lib/apt/lists/* \
    && rm -f /etc/nginx/sites-enabled/default

WORKDIR /app

# Python packages from deps stage
COPY --from=backend-deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=backend-deps /usr/local/bin/uvicorn /usr/local/bin/uvicorn

# Backend application code
COPY backend/app ./app

# Built frontend static files
COPY --from=frontend /build/dist ./static

# nginx + supervisor config
COPY docker/nginx.conf /etc/nginx/conf.d/fightarr.conf
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Persistent data directories + nginx writable tmp dirs
RUN mkdir -p /config /downloads /plex /var/log/supervisor \
    /var/lib/nginx/body /var/lib/nginx/fastcgi /var/lib/nginx/proxy \
    /var/lib/nginx/scgi /var/lib/nginx/uwsgi /var/log/nginx \
    && chmod -R 777 /var/lib/nginx /var/log/nginx /var/log/supervisor \
    && ln -sf /dev/stdout /var/log/nginx/access.log \
    && ln -sf /dev/stderr /var/log/nginx/error.log

VOLUME ["/config", "/downloads", "/plex"]

EXPOSE 7878

ENV FIGHTARR_DB_PATH=/config/fightarr.db \
    FIGHTARR_MEDIA_ROOT=/plex \
    FIGHTARR_LOG_LEVEL=INFO \
    FIGHTARR_CORS_ORIGINS=* \
    PUID=99 \
    PGID=100 \
    UMASK=002

# PUID/PGID entrypoint — run as the specified user so written files are owned
# by the correct Unraid user rather than root.
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
