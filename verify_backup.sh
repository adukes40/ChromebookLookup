#!/bin/bash
# Verify most recent backup integrity

BACKUP_DIR="/opt/chromebook-dashboard/backups"
LATEST_BACKUP=$(ls -t ${BACKUP_DIR}/chromebook_dashboard_*.sql.gz 2>/dev/null | head -1)

if [ -z "${LATEST_BACKUP}" ]; then
    echo "❌ ERROR: No backups found!"
    exit 1
fi

echo "Testing backup: ${LATEST_BACKUP}"

# Test gunzip
if gunzip -t ${LATEST_BACKUP} 2>/dev/null; then
    echo "✅ Backup file integrity: OK"
else
    echo "❌ Backup file corrupted!"
    exit 1
fi

# Check age
BACKUP_AGE=$(find ${LATEST_BACKUP} -mtime +1)
if [ -z "${BACKUP_AGE}" ]; then
    echo "✅ Backup freshness: OK (< 24 hours)"
else
    echo "⚠️  WARNING: Backup is older than 24 hours!"
fi

# Check size
SIZE=$(du -h ${LATEST_BACKUP} | cut -f1)
echo "Backup size: ${SIZE}"

echo "✅ Backup verification complete"
