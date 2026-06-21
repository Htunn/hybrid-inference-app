#!/usr/bin/env bash
# ==============================================================================
# Backup Script — Backup PostgreSQL database and volumes
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_ROOT/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

echo "🗄️  Creating backup: $TIMESTAMP"

# Backup PostgreSQL database
if docker compose ps postgres | grep -q "Up"; then
    echo "├─ Backing up PostgreSQL database..."
    docker compose exec -T postgres pg_dump -U rag -d rag_db > "$BACKUP_DIR/postgres_${TIMESTAMP}.sql"
    gzip "$BACKUP_DIR/postgres_${TIMESTAMP}.sql"
    echo "✓  Database backup: postgres_${TIMESTAMP}.sql.gz"
else
    echo "⚠  PostgreSQL not running, skipping database backup"
fi

# Backup docker volumes
echo "├─ Backing up Docker volumes..."
docker run --rm -v hybrid-inference-app_pgdata:/data -v "$BACKUP_DIR":/backup alpine tar czf "/backup/pgdata_${TIMESTAMP}.tar.gz" -C /data . 2>/dev/null || true

echo "✓  Backup complete"
echo ""
echo "Backups saved to: $BACKUP_DIR"
ls -lh "$BACKUP_DIR"/*"$TIMESTAMP"* 2>/dev/null || true
