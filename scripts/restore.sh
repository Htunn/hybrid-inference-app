#!/usr/bin/env bash
# ==============================================================================
# Restore Script — Restore PostgreSQL database from backup
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_ROOT/backups"

if [[ $# -eq 0 ]]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    echo ""
    echo "Available backups:"
    ls -lht "$BACKUP_DIR"/postgres_*.sql.gz 2>/dev/null | head -10 || echo "  No backups found"
    exit 1
fi

BACKUP_FILE="$1"

if [[ ! -f "$BACKUP_FILE" ]]; then
    echo "Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "🔄 Restoring database from: $(basename "$BACKUP_FILE")"
echo ""
read -p "This will overwrite the current database. Continue? (y/N) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Restore cancelled"
    exit 0
fi

# Ensure postgres is running
if ! docker compose ps postgres | grep -q "Up"; then
    echo "Starting PostgreSQL..."
    docker compose up -d postgres
    sleep 5
fi

# Restore
echo "Restoring..."
gunzip -c "$BACKUP_FILE" | docker compose exec -T postgres psql -U rag -d rag_db

echo "✓  Restore complete"
