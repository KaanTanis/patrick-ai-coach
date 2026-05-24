#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$ROOT/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
DEST="$BACKUP_DIR/$TIMESTAMP"

mkdir -p "$DEST"

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

DB_URL="${DATABASE_URL:-postgresql+asyncpg://tbot:tbot@localhost:5432/tbot}"
PG_URL="${DB_URL/postgresql+asyncpg/postgresql}"
PG_URL="${PG_URL/@localhost/@127.0.0.1@}"

echo "Backing up database..."
pg_dump "$PG_URL" > "$DEST/database.sql"

if [[ -d "$ROOT/data/photos" ]]; then
  echo "Backing up photos..."
  tar -czf "$DEST/photos.tar.gz" -C "$ROOT/data" photos
fi

echo "Backup saved to $DEST"

find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d -mtime +"$RETENTION_DAYS" -exec rm -rf {} +
