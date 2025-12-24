# Chromebook Dashboard - Database Schema Documentation

**Generated:** 2025-12-24
**Database:** PostgreSQL (chromebook_dashboard)
**ORM:** SQLAlchemy
**Cache:** Redis

---

## Table of Contents

1. [Overview](#overview)
2. [Database Tables](#database-tables)
3. [Indexes & Performance](#indexes--performance)
4. [Data Flow & Sync Process](#data-flow--sync-process)
5. [Query Patterns](#query-patterns)
6. [Optimization Recommendations](#optimization-recommendations)
7. [Maintenance Tasks](#maintenance-tasks)

---

## Overview

The Chromebook Dashboard uses a PostgreSQL database to cache data from three primary sources:
- **Google Workspace Admin API** - Chromebook device data
- **IncidentIQ API** - Asset tracking and location data
- **Meraki API** - Network location and connectivity data

### Database Statistics
- **Total Records:** 26,310 chromebooks (as reported)
- **Connection Pool:** QueuePool (10 base connections, 20 overflow)
- **Sync Frequency:** Daily at 2 AM (cron job)
- **Cache Layer:** Redis (15-minute TTL for most queries)

### Database Credentials
```
Host: localhost
Port: 5432
Database: chromebook_dashboard
User: chromebook_user
Password: [from .env file]
```

---

## Database Tables

### 1. chromebooks

**Purpose:** Primary table storing all Chromebook device information merged from Google Admin and IncidentIQ.

**Table Name:** `chromebooks`
**Primary Key:** `device_id` (Google device ID)

#### Columns

| Column | Type | Nullable | Index | Description |
|--------|------|----------|-------|-------------|
| **device_id** | VARCHAR(255) | NO | PK | Google Admin device ID (primary key) |
| **serial_number** | VARCHAR(100) | YES | UNIQUE, INDEX | Device serial number |
| **mac_address** | VARCHAR(255) | YES | NO | WiFi MAC address |
| **ethernet_mac** | VARCHAR(255) | YES | NO | Ethernet MAC address |
| **ip_address** | VARCHAR(100) | YES | NO | Last known IP address |
| **wan_ip_address** | VARCHAR(100) | YES | NO | WAN IP address |
| **aue_date** | VARCHAR(20) | YES | NO | Auto Update Expiration date (YYYY-MM) |
| **aue_timestamp** | BIGINT | YES | NO | AUE date as Unix timestamp |
| **battery_health** | INTEGER | YES | NO | Battery health percentage (0-100) |
| **battery_cycle_count** | INTEGER | YES | NO | Number of battery charge cycles |
| **battery_full_charge_capacity** | INTEGER | YES | NO | Current full charge capacity (mAh) |
| **battery_design_capacity** | INTEGER | YES | NO | Original design capacity (mAh) |
| **battery_manufacturer** | VARCHAR(100) | YES | NO | Battery manufacturer |
| **battery_report_time** | BIGINT | YES | NO | Timestamp of battery report |
| **os_version** | VARCHAR(100) | YES | NO | Chrome OS version |
| **platform_version** | VARCHAR(255) | YES | NO | Platform version |
| **firmware_version** | VARCHAR(255) | YES | NO | Firmware version |
| **last_used_date** | TIMESTAMP | YES | NO | Last time device was used |
| **asset_tag** | VARCHAR(100) | YES | UNIQUE, INDEX | Physical asset tag (from IIQ or Google) |
| **model** | VARCHAR(255) | YES | NO | Device model name |
| **status** | VARCHAR(50) | YES | INDEX | ACTIVE, DEPROVISIONED, DISABLED, PROVISIONED |
| **annotated_user** | VARCHAR(255) | YES | INDEX | Email of assigned user |
| **annotated_location** | VARCHAR(255) | YES | NO | Location annotation from Google |
| **annotated_asset_id** | VARCHAR(100) | YES | NO | Asset ID annotation from Google |
| **org_unit_path** | VARCHAR(500) | YES | INDEX | Google Workspace OU path |
| **last_sync_status** | VARCHAR(50) | YES | NO | Last sync status from Google |
| **last_policy_sync_time** | TIMESTAMP | YES | NO | Last policy sync timestamp |
| **recent_users** | JSON | YES | NO | Array of recent user objects |
| **iiq_asset_id** | VARCHAR(100) | YES | INDEX | IncidentIQ asset ID |
| **iiq_location** | VARCHAR(255) | YES | NO | Location from IncidentIQ |
| **iiq_room** | VARCHAR(100) | YES | NO | Room from IncidentIQ |
| **iiq_notes** | TEXT | YES | NO | Notes from IncidentIQ |
| **last_seen_meraki** | TIMESTAMP | YES | NO | Last seen on Meraki network |
| **meraki_ap_name** | VARCHAR(255) | YES | NO | Meraki access point name |
| **meraki_network** | VARCHAR(255) | YES | NO | Meraki network name |
| **created_at** | TIMESTAMP | NO | NO | Record creation timestamp |
| **updated_at** | TIMESTAMP | NO | NO | Last update timestamp |
| **data_source** | VARCHAR(50) | YES | NO | google_admin, incidentiq, or merged |

#### Key Indexes
```sql
-- Primary key index
PRIMARY KEY (device_id)

-- Unique constraints with indexes
UNIQUE (serial_number)
UNIQUE (asset_tag)

-- Performance indexes
CREATE INDEX idx_chromebooks_serial ON chromebooks(serial_number);
CREATE INDEX idx_chromebooks_asset_tag ON chromebooks(asset_tag);
CREATE INDEX idx_chromebooks_user ON chromebooks(annotated_user);
CREATE INDEX idx_chromebooks_iiq_asset ON chromebooks(iiq_asset_id);
CREATE INDEX idx_chromebooks_user_lower ON chromebooks(LOWER(annotated_user));
CREATE INDEX idx_chromebooks_status_orgunit ON chromebooks(status, org_unit_path);
```

#### Common Query Patterns
```sql
-- Search by serial number (most common)
SELECT * FROM chromebooks WHERE serial_number = 'ABC123';

-- Search by asset tag
SELECT * FROM chromebooks WHERE asset_tag = '12345';

-- Find devices by user
SELECT * FROM chromebooks WHERE LOWER(annotated_user) = LOWER('user@example.com');

-- Get active devices in an OU
SELECT * FROM chromebooks WHERE status = 'ACTIVE' AND org_unit_path LIKE '/Students/Grade 6%';

-- Find unassigned devices
SELECT * FROM chromebooks WHERE annotated_user IS NULL AND status = 'ACTIVE';
```

---

### 2. users

**Purpose:** Cache Google Workspace user data and track device assignments.

**Table Name:** `users`
**Primary Key:** `user_id` (Google user ID)

#### Columns

| Column | Type | Nullable | Index | Description |
|--------|------|----------|-------|-------------|
| **user_id** | VARCHAR(255) | NO | PK | Google user ID (primary key) |
| **email** | VARCHAR(255) | NO | UNIQUE, INDEX | User email address |
| **full_name** | VARCHAR(255) | YES | NO | Full name |
| **first_name** | VARCHAR(100) | YES | NO | First name |
| **last_name** | VARCHAR(100) | YES | NO | Last name |
| **org_unit_path** | VARCHAR(500) | YES | NO | Google Workspace OU path |
| **is_admin** | BOOLEAN | YES | NO | Whether user is a domain admin |
| **is_suspended** | BOOLEAN | YES | NO | Whether user is suspended |
| **assigned_devices** | JSON | YES | NO | Array of device_id values |
| **device_count** | INTEGER | YES | NO | Number of assigned devices |
| **created_at** | TIMESTAMP | NO | NO | Record creation timestamp |
| **updated_at** | TIMESTAMP | NO | NO | Last update timestamp |
| **last_login** | TIMESTAMP | YES | NO | Last login timestamp from Google |

#### Key Indexes
```sql
-- Primary key
PRIMARY KEY (user_id)

-- Unique email with index
UNIQUE (email)

-- Performance indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_email_lower ON users(LOWER(email));
```

#### Common Query Patterns
```sql
-- Find user by email
SELECT * FROM users WHERE LOWER(email) = LOWER('student@example.com');

-- Get users with devices
SELECT * FROM users WHERE device_count > 0;

-- Find users in an OU
SELECT * FROM users WHERE org_unit_path LIKE '/Staff%';

-- Get user's assigned devices (JOIN)
SELECT c.* FROM chromebooks c
JOIN users u ON u.email = c.annotated_user
WHERE u.email = 'student@example.com';
```

---

### 3. meraki_clients

**Purpose:** Store Meraki network client data for location tracking.

**Table Name:** `meraki_clients`
**Primary Key:** `mac_address`

#### Columns

| Column | Type | Nullable | Index | Description |
|--------|------|----------|-------|-------------|
| **mac_address** | VARCHAR(17) | NO | PK | Client MAC address (primary key) |
| **serial_number** | VARCHAR(100) | YES | INDEX | Chromebook serial (if matched) |
| **network_id** | VARCHAR(100) | YES | NO | Meraki network ID |
| **network_name** | VARCHAR(255) | YES | NO | Meraki network name |
| **ap_name** | VARCHAR(255) | YES | NO | Access point name |
| **ap_mac** | VARCHAR(17) | YES | NO | Access point MAC address |
| **ip_address** | VARCHAR(45) | YES | NO | Client IP address (IPv4 or IPv6) |
| **vlan** | INTEGER | YES | NO | VLAN ID |
| **description** | VARCHAR(255) | YES | NO | Client description |
| **first_seen** | TIMESTAMP | YES | NO | First seen timestamp |
| **last_seen** | TIMESTAMP | YES | INDEX | Last seen timestamp |
| **created_at** | TIMESTAMP | NO | NO | Record creation timestamp |
| **updated_at** | TIMESTAMP | NO | NO | Last update timestamp |

#### Key Indexes
```sql
-- Primary key
PRIMARY KEY (mac_address)

-- Performance indexes
CREATE INDEX idx_meraki_serial ON meraki_clients(serial_number);
CREATE INDEX idx_meraki_last_seen ON meraki_clients(last_seen);
```

#### Common Query Patterns
```sql
-- Find Meraki client by MAC
SELECT * FROM meraki_clients WHERE mac_address = '00:11:22:33:44:55';

-- Get recent Meraki clients (last 24 hours)
SELECT * FROM meraki_clients WHERE last_seen > NOW() - INTERVAL '24 hours';

-- Link Meraki data to chromebook
SELECT c.*, m.ap_name, m.network_name, m.last_seen
FROM chromebooks c
LEFT JOIN meraki_clients m ON c.mac_address = m.mac_address
WHERE c.serial_number = 'ABC123';
```

---

### 4. sync_logs

**Purpose:** Track sync operations for monitoring and debugging.

**Table Name:** `sync_logs`
**Primary Key:** `id` (auto-increment)

#### Columns

| Column | Type | Nullable | Index | Description |
|--------|------|----------|-------|-------------|
| **id** | INTEGER | NO | PK | Auto-increment primary key |
| **sync_type** | VARCHAR(50) | YES | INDEX | chromebooks, users, meraki, full |
| **status** | VARCHAR(20) | YES | INDEX | started, completed, failed |
| **records_processed** | INTEGER | YES | NO | Total records processed |
| **records_created** | INTEGER | YES | NO | New records created |
| **records_updated** | INTEGER | YES | NO | Existing records updated |
| **duration_seconds** | INTEGER | YES | NO | Sync duration in seconds |
| **error_message** | TEXT | YES | NO | Error details if failed |
| **started_at** | TIMESTAMP | NO | NO | Sync start timestamp |
| **completed_at** | TIMESTAMP | YES | INDEX | Sync completion timestamp |

#### Key Indexes
```sql
-- Primary key
PRIMARY KEY (id)

-- Performance indexes
CREATE INDEX idx_sync_logs_type ON sync_logs(sync_type);
CREATE INDEX idx_sync_logs_status ON sync_logs(status);
CREATE INDEX idx_sync_logs_type_status ON sync_logs(sync_type, status, completed_at DESC);
```

#### Common Query Patterns
```sql
-- Get last successful sync
SELECT * FROM sync_logs
WHERE status = 'completed'
ORDER BY completed_at DESC
LIMIT 1;

-- Get sync history (last 10)
SELECT sync_type, status, completed_at, duration_seconds, records_processed
FROM sync_logs
ORDER BY started_at DESC
LIMIT 10;

-- Find failed syncs
SELECT * FROM sync_logs
WHERE status = 'failed'
ORDER BY started_at DESC;

-- Get sync statistics by type
SELECT sync_type,
       COUNT(*) as total_syncs,
       AVG(duration_seconds) as avg_duration,
       SUM(records_processed) as total_processed
FROM sync_logs
WHERE status = 'completed'
GROUP BY sync_type;
```

---

## Indexes & Performance

### Existing Indexes

#### chromebooks table
1. **PK:** `device_id` (primary key - clustered index)
2. **UNIQUE:** `serial_number` (unique constraint with index)
3. **UNIQUE:** `asset_tag` (unique constraint with index)
4. **INDEX:** `annotated_user` (user assignment lookups)
5. **INDEX:** `iiq_asset_id` (IncidentIQ joins)
6. **COMPOSITE:** `LOWER(annotated_user)` (case-insensitive user search)
7. **COMPOSITE:** `(status, org_unit_path)` (filtered OU queries)

#### users table
1. **PK:** `user_id` (primary key)
2. **UNIQUE:** `email` (unique constraint with index)
3. **INDEX:** `LOWER(email)` (case-insensitive email search)

#### meraki_clients table
1. **PK:** `mac_address` (primary key)
2. **INDEX:** `serial_number` (chromebook joins)
3. **INDEX:** `last_seen` (time-based queries)

#### sync_logs table
1. **PK:** `id` (primary key)
2. **INDEX:** `sync_type`
3. **INDEX:** `status`
4. **COMPOSITE:** `(sync_type, status, completed_at DESC)` (sync history queries)

### Missing Indexes (Recommendations)

Based on query patterns in `/opt/chromebook-dashboard/main.py` and `/opt/chromebook-dashboard/routes/optimized_routes.py`:

```sql
-- For model-based filtering (if frequently used)
CREATE INDEX idx_chromebooks_model ON chromebooks(model);

-- For location-based queries
CREATE INDEX idx_chromebooks_iiq_location ON chromebooks(iiq_location);

-- For AUE tracking (if reports are added)
CREATE INDEX idx_chromebooks_aue_date ON chromebooks(aue_date);

-- For battery health reporting
CREATE INDEX idx_chromebooks_battery_health ON chromebooks(battery_health) WHERE battery_health IS NOT NULL;

-- For org unit filtering
CREATE INDEX idx_chromebooks_org_unit ON chromebooks USING gin(org_unit_path gin_trgm_ops);
-- Requires: CREATE EXTENSION pg_trgm;

-- For status filtering
CREATE INDEX idx_chromebooks_status ON chromebooks(status);

-- For user org unit queries
CREATE INDEX idx_users_org_unit ON users(org_unit_path);

-- For device count filtering
CREATE INDEX idx_users_device_count ON users(device_count) WHERE device_count > 0;
```

---

## Data Flow & Sync Process

### Sync Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Google Admin   │     │  IncidentIQ     │     │     Meraki      │
│      API        │     │      API        │     │      API        │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         │ Fetch Devices         │ Fetch Assets          │ Fetch Clients
         │ (projection=FULL)     │ (50,000 limit)        │ (all networks)
         │                       │                       │
         └───────────────────────┴───────────────────────┘
                                 │
                                 ▼
                     ┌───────────────────────┐
                     │   Sync Service        │
                     │   (sync_service.py)   │
                     │                       │
                     │ - Merge data by       │
                     │   serial number       │
                     │ - Create/Update       │
                     │   records             │
                     │ - Batch commits       │
                     │   (every 100 items)   │
                     └───────────┬───────────┘
                                 │
                                 ▼
                     ┌───────────────────────┐
                     │   PostgreSQL DB       │
                     │                       │
                     │ - chromebooks         │
                     │ - users               │
                     │ - meraki_clients      │
                     │ - sync_logs           │
                     └───────────┬───────────┘
                                 │
                                 ▼
                     ┌───────────────────────┐
                     │   Redis Cache         │
                     │                       │
                     │ - Search results      │
                     │   (TTL: 15 min)       │
                     │ - Sync status         │
                     │   (TTL: 24 hours)     │
                     └───────────────────────┘
```

### Sync Process Details

#### 1. Full Sync (`sync_all()`)
**Location:** `/opt/chromebook-dashboard/services/sync_service.py`
**Frequency:** Daily at 2 AM (cron job)
**Duration:** 2-5 minutes (for 26,310 records)

**Steps:**
1. Create sync log entry (status: 'started')
2. Run parallel syncs:
   - `sync_chromebooks()` - Google Admin + IncidentIQ merge
   - `sync_users()` - Google Admin users
   - `sync_meraki()` - Meraki network clients
3. Update sync log (status: 'completed')
4. Clear Redis cache patterns: `chromebook:*`, `user:*`, `search:*`
5. Update sync status in Redis (TTL: 24 hours)

#### 2. Chromebook Sync (`sync_chromebooks()`)
```python
# Fetch from Google Admin
google_devices = await google.list_chromebooks()  # All devices, FULL projection

# Fetch from IncidentIQ
iiq_assets = await iiq.list_chromebook_assets()   # All chromebook assets

# Create lookup by serial number
iiq_lookup = {asset['serialNumber'].upper(): asset for asset in iiq_assets}

# Process each device
for device in google_devices:
    serial = device.get('serialNumber', '').upper()
    iiq_data = iiq_lookup.get(serial, {})

    # Merge Google + IIQ data
    merged_data = {
        # Google data
        'device_id': device.get('deviceId'),
        'serial_number': serial,
        'model': device.get('model'),
        'status': device.get('status'),
        'annotated_user': device.get('annotatedUser'),
        # ... more Google fields

        # IncidentIQ data
        'iiq_asset_id': iiq_data.get('id'),
        'iiq_location': iiq_data.get('location'),
        'asset_tag': device.get('annotatedAssetId') or iiq_data.get('assetTag'),
        # ... more IIQ fields
    }

    # Upsert to database
    existing = session.query(Chromebook).filter(device_id=device_id).first()
    if existing:
        update_fields(existing, merged_data)
    else:
        session.add(Chromebook(**merged_data))

    # Commit every 100 devices
    if count % 100 == 0:
        session.commit()
```

#### 3. User Sync (`sync_users()`)
```python
# Fetch users from Google
google_users = await google.list_users()

for user in google_users:
    # Get assigned chromebooks from database
    chromebooks = session.query(Chromebook).filter(
        Chromebook.annotated_user == user['email']
    ).all()

    user_data = {
        'user_id': user['id'],
        'email': user['primaryEmail'],
        'full_name': user['name']['fullName'],
        'assigned_devices': [cb.device_id for cb in chromebooks],
        'device_count': len(chromebooks)
    }

    # Upsert
    session.merge(User(**user_data))
```

#### 4. Meraki Sync (`sync_meraki()`)
```python
# Fetch Meraki clients
meraki_clients = await meraki.list_clients()

for client in meraki_clients:
    mac = client['mac'].upper()

    meraki_data = {
        'mac_address': mac,
        'network_name': client['networkName'],
        'ap_name': client['apName'],
        'ip_address': client['ip'],
        'last_seen': client['lastSeen']
    }

    # Upsert
    session.merge(MerakiClient(**meraki_data))

# Link Meraki data to chromebooks by MAC address
# (Currently not implemented - see optimization recommendations)
```

### Sync Performance Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| Total sync duration | 2-5 minutes | For 26,310 chromebooks |
| Google API calls | ~132 | 200 devices per page |
| IncidentIQ API calls | 1-10 | Depends on pagination |
| Meraki API calls | Varies | Per network |
| Database commits | ~263 | Every 100 records |
| Records processed | 26,310+ | Chromebooks + users + Meraki clients |

---

## Query Patterns

### Fast Queries (< 100ms) - Database with Indexes

#### 1. Search by Serial Number
```sql
-- Query used by: /api/combined/search, /search/device
SELECT * FROM chromebooks WHERE LOWER(serial_number) = LOWER('abc123');
```
**Performance:** < 10ms (indexed)

#### 2. Search by Asset Tag
```sql
-- Query used by: /api/combined/search, /search/device
SELECT * FROM chromebooks WHERE LOWER(asset_tag) = LOWER('12345');
```
**Performance:** < 10ms (indexed)

#### 3. Search by User Email
```sql
-- Query used by: /api/combined/search, /api/user/search
SELECT * FROM chromebooks
WHERE LOWER(annotated_user) = LOWER('student@example.com');
```
**Performance:** < 50ms (indexed with LOWER)

#### 4. Dashboard Statistics
```sql
-- Query used by: /api/dashboard/stats
SELECT
    COUNT(*) as total_devices,
    COUNT(CASE WHEN status = 'ACTIVE' THEN 1 END) as active,
    COUNT(CASE WHEN status = 'DISABLED' THEN 1 END) as disabled,
    COUNT(CASE WHEN status = 'PROVISIONED' THEN 1 END) as provisioned,
    COUNT(CASE WHEN status = 'DEPROVISIONED' THEN 1 END) as deprovisioned,
    MAX(updated_at) as last_sync
FROM chromebooks;
```
**Performance:** < 100ms (sequential scan on 26K rows)
**Optimization:** Cache in Redis for 5 minutes

#### 5. User Device Lookup
```sql
-- Query used by: /api/user/search
SELECT
    c.asset_tag,
    c.serial_number,
    c.model,
    c.status,
    c.iiq_location
FROM chromebooks c
WHERE LOWER(c.annotated_user) = LOWER('student@example.com')
LIMIT 10;
```
**Performance:** < 50ms (indexed)

### Complex Queries (100-500ms)

#### 6. Multi-field Search
```sql
-- Query used by: /api/combined/search
SELECT * FROM chromebooks
WHERE
    LOWER(serial_number) LIKE LOWER('%abc%') OR
    LOWER(asset_tag) LIKE LOWER('%abc%') OR
    LOWER(annotated_user) LIKE LOWER('%abc%')
LIMIT 50;
```
**Performance:** 100-300ms (partial index scans)
**Optimization:** Use full-text search with `pg_trgm` extension

#### 7. Filtered Pagination
```sql
-- Query used by: /devices endpoint
SELECT * FROM chromebooks
WHERE status = 'ACTIVE' AND org_unit_path LIKE '/Students/Grade 6%'
ORDER BY updated_at DESC
LIMIT 100 OFFSET 0;
```
**Performance:** 100-200ms
**Optimization:** Add composite index on (status, org_unit_path)

### Redis Cache Patterns

#### Cache Keys
```python
# From /opt/chromebook-dashboard/cache/redis_manager.py

# Device lookups
chromebook:serial:ABC123           # TTL: 15 min
chromebook:asset:12345              # TTL: 15 min

# User lookups
user:email:student@example.com     # TTL: 15 min
user:devices:student@example.com   # TTL: 15 min

# Search results
search:abc123                       # TTL: 15 min
search:student@example.com         # TTL: 15 min

# System status
sync:status                         # TTL: 24 hours
sync:lock:full                      # TTL: 1 hour (during sync)

# Dashboard stats
dashboard:stats                     # TTL: 5 min

# Reports (future)
report:summary                      # TTL: varies
report:battery_health:30           # TTL: varies
report:aue_status                  # TTL: varies
```

#### Cache Hit Rate
- **Target:** > 80% for search queries
- **Measured:** Check with `cache.get_stats()`

---

## Optimization Recommendations

### High Priority

#### 1. Add Missing Indexes
```sql
-- For status filtering (used in dashboard)
CREATE INDEX idx_chromebooks_status ON chromebooks(status);

-- For model filtering (if model reports are added)
CREATE INDEX idx_chromebooks_model ON chromebooks(model);

-- For location filtering
CREATE INDEX idx_chromebooks_iiq_location ON chromebooks(iiq_location);

-- For org unit filtering
CREATE INDEX idx_users_org_unit ON users(org_unit_path);
```

#### 2. Implement Full-Text Search
```sql
-- Install pg_trgm extension
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Create GIN index for fuzzy search
CREATE INDEX idx_chromebooks_search_trgm ON chromebooks
USING gin((
    COALESCE(serial_number, '') || ' ' ||
    COALESCE(asset_tag, '') || ' ' ||
    COALESCE(annotated_user, '') || ' ' ||
    COALESCE(model, '')
) gin_trgm_ops);

-- Query with fuzzy matching
SELECT * FROM chromebooks
WHERE (
    COALESCE(serial_number, '') || ' ' ||
    COALESCE(asset_tag, '') || ' ' ||
    COALESCE(annotated_user, '') || ' ' ||
    COALESCE(model, '')
) ILIKE '%search_term%'
LIMIT 50;
```

#### 3. Link Meraki Data to Chromebooks
Currently, Meraki data is stored but not linked. Implement MAC address matching:

```python
# In sync_service.py - _link_meraki_to_chromebooks()
def _link_meraki_to_chromebooks(self, session: Session):
    """Link Meraki client data to chromebooks by MAC address"""

    # Update chromebooks with Meraki data
    session.execute(text("""
        UPDATE chromebooks cb
        SET
            last_seen_meraki = mc.last_seen,
            meraki_ap_name = mc.ap_name,
            meraki_network = mc.network_name
        FROM meraki_clients mc
        WHERE cb.mac_address = mc.mac_address
            AND mc.last_seen > NOW() - INTERVAL '7 days'
    """))

    session.commit()
```

#### 4. Partition Large Tables (Future)
If chromebook count exceeds 100K, consider partitioning by status or year:

```sql
-- Partition by status
CREATE TABLE chromebooks_active PARTITION OF chromebooks FOR VALUES IN ('ACTIVE');
CREATE TABLE chromebooks_deprovisioned PARTITION OF chromebooks FOR VALUES IN ('DEPROVISIONED');
```

### Medium Priority

#### 5. Add Materialized Views for Reports
```sql
-- Device statistics by OU
CREATE MATERIALIZED VIEW mv_devices_by_ou AS
SELECT
    org_unit_path,
    COUNT(*) as total_devices,
    COUNT(CASE WHEN status = 'ACTIVE' THEN 1 END) as active,
    COUNT(CASE WHEN annotated_user IS NOT NULL THEN 1 END) as assigned,
    AVG(battery_health) as avg_battery_health
FROM chromebooks
GROUP BY org_unit_path;

CREATE UNIQUE INDEX ON mv_devices_by_ou(org_unit_path);

-- Refresh daily after sync
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_devices_by_ou;
```

#### 6. Add Database Constraints
```sql
-- Ensure valid status values
ALTER TABLE chromebooks ADD CONSTRAINT check_status
CHECK (status IN ('ACTIVE', 'DISABLED', 'PROVISIONED', 'DEPROVISIONED'));

-- Ensure valid battery health
ALTER TABLE chromebooks ADD CONSTRAINT check_battery_health
CHECK (battery_health IS NULL OR (battery_health >= 0 AND battery_health <= 100));

-- Ensure device count matches assigned_devices
ALTER TABLE users ADD CONSTRAINT check_device_count
CHECK (device_count = jsonb_array_length(assigned_devices::jsonb));
```

#### 7. Optimize Sync Batch Size
Current: 100 records per commit
Recommended: Test with 500-1000 records for better performance

```python
# In sync_service.py
BATCH_SIZE = 500  # Tune based on testing

if processed % BATCH_SIZE == 0:
    session.commit()
```

### Low Priority

#### 8. Add Audit Trail
```sql
CREATE TABLE chromebook_history (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(255) NOT NULL,
    field_name VARCHAR(50) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_by VARCHAR(255),
    changed_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_history_device ON chromebook_history(device_id, changed_at DESC);
```

#### 9. Implement Soft Deletes
Instead of deleting deprovisioned devices, keep them with a flag:

```sql
ALTER TABLE chromebooks ADD COLUMN deleted_at TIMESTAMP NULL;
ALTER TABLE chromebooks ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE;

CREATE INDEX idx_chromebooks_deleted ON chromebooks(is_deleted, deleted_at);
```

---

## Maintenance Tasks

### Daily Tasks (Automated)

#### 1. Sync Data (2 AM)
```bash
# Cron job: /opt/chromebook-dashboard/sync_cron.sh
0 2 * * * /opt/chromebook-dashboard/venv/bin/python3 /opt/chromebook-dashboard/sync_script.py
```

#### 2. Clear Old Sync Logs (Weekly)
```sql
-- Keep last 90 days only
DELETE FROM sync_logs WHERE started_at < NOW() - INTERVAL '90 days';
```

### Weekly Tasks (Manual)

#### 3. Vacuum and Analyze
```bash
# SSH to database server
sudo -u postgres psql chromebook_dashboard

# Analyze tables
ANALYZE chromebooks;
ANALYZE users;
ANALYZE meraki_clients;
ANALYZE sync_logs;

# Vacuum (reclaim space)
VACUUM ANALYZE chromebooks;
```

#### 4. Check Index Usage
```sql
-- Find unused indexes
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan as scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan ASC, tablename;

-- Indexes with 0 scans might be candidates for removal
```

#### 5. Monitor Table Bloat
```sql
-- Check for dead tuples (needs vacuum)
SELECT
    schemaname,
    relname,
    n_live_tup as live_tuples,
    n_dead_tup as dead_tuples,
    ROUND(n_dead_tup * 100.0 / NULLIF(n_live_tup + n_dead_tup, 0), 2) as dead_pct,
    last_autovacuum,
    last_vacuum
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY dead_pct DESC;

-- If dead_pct > 10%, run VACUUM
```

### Monthly Tasks

#### 6. Backup Database
```bash
# Full backup
sudo -u postgres pg_dump chromebook_dashboard > backup_$(date +%Y%m%d).sql

# Compressed backup
sudo -u postgres pg_dump chromebook_dashboard | gzip > backup_$(date +%Y%m%d).sql.gz

# Restore if needed
sudo -u postgres psql chromebook_dashboard < backup_20251224.sql
```

#### 7. Review Query Performance
```sql
-- Enable pg_stat_statements extension (if not already)
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Find slow queries
SELECT
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    max_exec_time
FROM pg_stat_statements
WHERE query NOT LIKE '%pg_stat%'
ORDER BY mean_exec_time DESC
LIMIT 20;
```

#### 8. Update Statistics
```sql
-- Re-analyze all tables to update planner statistics
ANALYZE VERBOSE;
```

### Quarterly Tasks

#### 9. Review and Archive Old Data
```sql
-- Archive deprovisioned devices older than 1 year
CREATE TABLE chromebooks_archive AS
SELECT * FROM chromebooks
WHERE status = 'DEPROVISIONED'
    AND updated_at < NOW() - INTERVAL '1 year';

-- Delete archived records
DELETE FROM chromebooks
WHERE status = 'DEPROVISIONED'
    AND updated_at < NOW() - INTERVAL '1 year';
```

#### 10. Re-index Tables
```sql
-- Rebuild indexes to reduce bloat
REINDEX TABLE chromebooks;
REINDEX TABLE users;
REINDEX TABLE meraki_clients;
```

---

## Database Schema Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        chromebooks                               │
├─────────────────────────────────────────────────────────────────┤
│ PK  device_id          VARCHAR(255)                             │
│ UQ  serial_number      VARCHAR(100)   ──┐                       │
│ UQ  asset_tag          VARCHAR(100)     │                       │
│     mac_address        VARCHAR(255)     │                       │
│ IDX annotated_user     VARCHAR(255)     │                       │
│     org_unit_path      VARCHAR(500)     │                       │
│     status             VARCHAR(50)      │                       │
│     model              VARCHAR(255)     │                       │
│ IDX iiq_asset_id       VARCHAR(100)     │                       │
│     iiq_location       VARCHAR(255)     │                       │
│     battery_health     INTEGER          │                       │
│     os_version         VARCHAR(100)     │                       │
│     recent_users       JSON             │                       │
│     created_at         TIMESTAMP        │                       │
│     updated_at         TIMESTAMP        │                       │
└─────────────────────────────────────────┼───────────────────────┘
                                          │
                        ┌─────────────────┘
                        │
                        │ Linked by annotated_user (email)
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                          users                                   │
├─────────────────────────────────────────────────────────────────┤
│ PK  user_id            VARCHAR(255)                             │
│ UQ  email              VARCHAR(255)                             │
│     full_name          VARCHAR(255)                             │
│     org_unit_path      VARCHAR(500)                             │
│     is_suspended       BOOLEAN                                  │
│     assigned_devices   JSON (array of device_ids)              │
│     device_count       INTEGER                                  │
│     last_login         TIMESTAMP                                │
│     created_at         TIMESTAMP                                │
│     updated_at         TIMESTAMP                                │
└─────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────┐
│                      meraki_clients                              │
├─────────────────────────────────────────────────────────────────┤
│ PK  mac_address        VARCHAR(17)                              │
│ IDX serial_number      VARCHAR(100)   ──┐                       │
│     network_name       VARCHAR(255)     │                       │
│     ap_name            VARCHAR(255)     │                       │
│     ip_address         VARCHAR(45)      │                       │
│ IDX last_seen          TIMESTAMP        │                       │
│     created_at         TIMESTAMP        │                       │
│     updated_at         TIMESTAMP        │                       │
└─────────────────────────────────────────┼───────────────────────┘
                                          │
                        ┌─────────────────┘
                        │
                        │ Linked by serial_number (future)
                        │ or mac_address
                        │
                        ▼
              (Back to chromebooks table)


┌─────────────────────────────────────────────────────────────────┐
│                        sync_logs                                 │
├─────────────────────────────────────────────────────────────────┤
│ PK  id                 SERIAL                                   │
│ IDX sync_type          VARCHAR(50)                              │
│ IDX status             VARCHAR(20)                              │
│     records_processed  INTEGER                                  │
│     records_created    INTEGER                                  │
│     records_updated    INTEGER                                  │
│     duration_seconds   INTEGER                                  │
│     error_message      TEXT                                     │
│     started_at         TIMESTAMP                                │
│ IDX completed_at       TIMESTAMP                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Connection Pooling Configuration

**File:** `/opt/chromebook-dashboard/database/connection.py`

```python
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,           # Max 10 persistent connections
    max_overflow=20,        # Allow 20 additional connections under load
    pool_pre_ping=True,     # Verify connections before using
    pool_recycle=3600,      # Recycle connections after 1 hour
    echo=False              # Set to True for SQL debugging
)
```

### Pool Monitoring
```python
# Check pool status
from database.connection import db

pool_status = db.engine.pool.status()
print(pool_status)
# Example output: "Pool size: 10  Connections in pool: 5  Current Overflow: 2"
```

---

## SQLAlchemy ORM Usage

### Session Management

```python
# Context manager (recommended)
from database.connection import db

with db.get_session() as session:
    chromebook = session.query(Chromebook).filter(
        Chromebook.serial_number == 'ABC123'
    ).first()
    print(chromebook.to_dict())
# Session automatically commits and closes

# FastAPI dependency
from fastapi import Depends
from database.connection import get_db

@app.get("/devices")
async def get_devices(db: Session = Depends(get_db)):
    devices = db.query(Chromebook).limit(10).all()
    return [d.to_dict() for d in devices]
```

### Common ORM Patterns

```python
# Create
new_device = Chromebook(
    device_id='abc-123',
    serial_number='ABC123',
    model='HP Chromebook 11 G9'
)
session.add(new_device)
session.commit()

# Read
device = session.query(Chromebook).filter(
    Chromebook.serial_number == 'ABC123'
).first()

# Update
device.status = 'DEPROVISIONED'
session.commit()

# Delete
session.delete(device)
session.commit()

# Upsert (merge)
session.merge(device)
session.commit()

# Bulk update
session.query(Chromebook).filter(
    Chromebook.status == 'ACTIVE'
).update({
    'updated_at': datetime.now()
})
session.commit()

# Raw SQL
from sqlalchemy import text

result = session.execute(text("""
    SELECT COUNT(*) FROM chromebooks WHERE status = :status
"""), {'status': 'ACTIVE'})
count = result.scalar()
```

---

## Troubleshooting

### Common Issues

#### 1. Connection Pool Exhausted
**Symptom:** `QueuePool limit of size 10 overflow 20 reached`

**Solution:**
```python
# Increase pool size in connection.py
pool_size=20,
max_overflow=40
```

#### 2. Slow Queries
**Symptom:** Queries taking > 1 second

**Diagnosis:**
```sql
-- Enable query logging
ALTER SYSTEM SET log_min_duration_statement = 1000;  -- Log queries > 1s
SELECT pg_reload_conf();

-- Check slow query log
tail -f /var/log/postgresql/postgresql-*.log | grep "duration:"
```

**Solution:** Add missing indexes, optimize queries

#### 3. Database Locks
**Symptom:** Sync hangs or fails

**Diagnosis:**
```sql
-- Check for locks
SELECT
    pg_stat_activity.pid,
    pg_stat_activity.query,
    pg_locks.mode,
    pg_locks.granted
FROM pg_stat_activity
JOIN pg_locks ON pg_stat_activity.pid = pg_locks.pid
WHERE NOT pg_locks.granted;

-- Kill blocking query
SELECT pg_terminate_backend(pid);
```

#### 4. Out of Disk Space
**Symptom:** `ERROR: could not extend file`

**Check disk usage:**
```bash
# Database directory
df -h /var/lib/postgresql

# Database size
sudo -u postgres psql -c "SELECT pg_size_pretty(pg_database_size('chromebook_dashboard'));"

# Table sizes
sudo -u postgres psql chromebook_dashboard -c "SELECT tablename, pg_size_pretty(pg_total_relation_size(tablename::regclass)) FROM pg_tables WHERE schemaname = 'public';"
```

**Solution:** Clean up old data, vacuum, archive

---

## Security Considerations

### 1. Database Credentials
- **Storage:** `.env` file (not in git)
- **Permissions:** `chmod 600 .env`
- **User privileges:** Grant only necessary permissions

```sql
-- Create restricted user
CREATE USER chromebook_user WITH PASSWORD 'secure_password';

-- Grant only SELECT, INSERT, UPDATE on specific tables
GRANT SELECT, INSERT, UPDATE ON chromebooks TO chromebook_user;
GRANT SELECT, INSERT, UPDATE ON users TO chromebook_user;
GRANT SELECT, INSERT, UPDATE ON meraki_clients TO chromebook_user;
GRANT SELECT, INSERT, UPDATE ON sync_logs TO chromebook_user;

-- No DELETE or DROP permissions
```

### 2. Connection Security
```python
# Use SSL for remote connections
DATABASE_URL = "postgresql://user:pass@host:5432/db?sslmode=require"
```

### 3. SQL Injection Prevention
- **Always use parameterized queries** (SQLAlchemy does this automatically)
- **Never concatenate user input into SQL**

```python
# GOOD - Parameterized
session.execute(text("SELECT * FROM chromebooks WHERE serial = :serial"),
                {'serial': user_input})

# BAD - SQL Injection vulnerable
session.execute(text(f"SELECT * FROM chromebooks WHERE serial = '{user_input}'"))
```

---

## Performance Benchmarks

### Query Performance (26,310 chromebooks)

| Query Type | Time | Caching |
|------------|------|---------|
| Serial number lookup (exact) | < 10ms | Redis: < 5ms |
| Asset tag lookup (exact) | < 10ms | Redis: < 5ms |
| User email lookup | < 50ms | Redis: < 5ms |
| Dashboard stats | < 100ms | Redis: < 5ms (5-min TTL) |
| Multi-field search (LIKE) | 100-300ms | Redis: < 5ms (15-min TTL) |
| Paginated list (100 items) | < 100ms | Not cached |
| Full table scan | 1-2s | Avoid! |

### Sync Performance

| Operation | Time | Records |
|-----------|------|---------|
| Google API fetch | 60-90s | 26,310 devices |
| IncidentIQ API fetch | 30-60s | ~25,000 assets |
| Meraki API fetch | 20-40s | Varies |
| Database upserts | 60-120s | 26,310 chromebooks |
| **Total sync time** | **2-5 minutes** | **Full sync** |

---

## Future Enhancements

### Planned Features

1. **Foreign Key Relationships**
   - Add FK: `chromebooks.annotated_user` → `users.email`
   - Add FK: `meraki_clients.serial_number` → `chromebooks.serial_number`

2. **Full-Text Search**
   - Implement `pg_trgm` for fuzzy search
   - Add search vectors for multi-field search

3. **Reporting Tables**
   - Materialized views for dashboard stats
   - Pre-aggregated reports (by OU, by model, by AUE date)

4. **Time-Series Data**
   - Track historical battery health
   - Track device location history (Meraki)
   - Track user assignment changes

5. **API Rate Limiting**
   - Track API calls in database
   - Implement rate limiting based on sync logs

---

## References

- **PostgreSQL Docs:** https://www.postgresql.org/docs/
- **SQLAlchemy Docs:** https://docs.sqlalchemy.org/
- **Project Files:**
  - `/opt/chromebook-dashboard/database/models.py` - ORM models
  - `/opt/chromebook-dashboard/database/connection.py` - Database connection
  - `/opt/chromebook-dashboard/services/sync_service.py` - Sync logic
  - `/opt/chromebook-dashboard/cache/redis_manager.py` - Cache manager
  - `/opt/chromebook-dashboard/scripts/init_database.py` - Database setup

---

**Document Version:** 1.0
**Last Updated:** 2025-12-24
**Maintained By:** Backend Database Agent
