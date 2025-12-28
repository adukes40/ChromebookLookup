#!/bin/bash
# Chromebook Dashboard - Database Backup Script
# Run daily at 3:00 AM via cron

set -e

# Configuration
DB_NAME="chromebook_dashboard"
BACKUP_DIR="/opt/chromebook-dashboard/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/chromebook_dashboard_${DATE}.sql.gz"
RETENTION_DAYS=30
LOG_FILE="/var/log/chromebook_backup.log"

# Log function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a ${LOG_FILE}
}

log "Starting database backup..."

# Create backup (run as postgres user, no -U needed)
if pg_dump ${DB_NAME} | gzip > ${BACKUP_FILE}; then
    SIZE=$(du -h ${BACKUP_FILE} | cut -f1)
    log "✅ Backup completed: ${BACKUP_FILE} (${SIZE})"
else
    log "❌ ERROR: Backup failed!"
    exit 1
fi

# Verify backup file integrity
if gunzip -t ${BACKUP_FILE} 2>/dev/null; then
    log "✅ Backup file integrity verified"
else
    log "❌ ERROR: Backup file is corrupted!"
    exit 1
fi

# Clean up old backups
log "Cleaning up backups older than ${RETENTION_DAYS} days..."
DELETED=$(find ${BACKUP_DIR} -name "chromebook_dashboard_*.sql.gz" -mtime +${RETENTION_DAYS} -delete -print | wc -l)
log "Deleted ${DELETED} old backup(s)"

# Count remaining backups
COUNT=$(find ${BACKUP_DIR} -name "chromebook_dashboard_*.sql.gz" | wc -l)
log "Total backups available: ${COUNT}"

log "Backup completed successfully"
