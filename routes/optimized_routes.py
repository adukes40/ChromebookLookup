"""
Optimized FastAPI routes using Redis cache + PostgreSQL database
FAST search: < 100ms for cached results, < 500ms for database lookups
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
import threading
from sqlalchemy import text
from sqlalchemy import or_, and_
from typing import Optional, List, Dict, Any
from datetime import datetime

from database.models import Chromebook, User
from database.connection import get_db
from database.connection import db
from cache.redis_manager import cache, CacheKeys


router = APIRouter()


# Fix for search_device
@router.get("/search/device")
async def search_device(q: str = Query(..., min_length=1)) -> Dict[str, Any]:
    query = q.strip().upper()
    cache_key = CacheKeys.search_results(query)
    cached_result = cache.get(cache_key)
    
    if cached_result:
        cached_result['source'] = 'cache'
        cached_result['response_time_ms'] = '< 10ms'
        return cached_result
    
    start_time = datetime.now()
    
    # Try database first
    with db.get_session() as session:
        device = session.query(Chromebook).filter(
            or_(
                Chromebook.serial_number == query,
                Chromebook.asset_tag == query
            )
        ).first()
        
        if not device:
            device = session.query(Chromebook).filter(
                Chromebook.annotated_user.ilike(f'%{query}%')
            ).first()
        
        if not device:
            device = session.query(Chromebook).filter(
                or_(
                    Chromebook.serial_number.contains(query),
                    Chromebook.asset_tag.contains(query)
                )
            ).first()
        
        # If found in database, return it
        if device:
            response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            result = {
                'success': True,
                'device': device.to_dict(),
                'source': 'database',
                'response_time_ms': response_time_ms,
                'cache_updated': True
            }
            
            cache.set(cache_key, result, ttl=900)
            if device.serial_number:
                cache.set(CacheKeys.chromebook_by_serial(device.serial_number), device.to_dict(), ttl=900)
            if device.asset_tag:
                cache.set(CacheKeys.chromebook_by_asset(device.asset_tag), device.to_dict(), ttl=900)
            
            return result
    
    # Not in database - try IIQ API
    try:
        from integrations.incidentiq import IncidentIQClient
        import os
        
        iiq = IncidentIQClient(
            os.getenv('IIQ_SITE_ID'), 
            os.getenv('IIQ_API_TOKEN'),
            os.getenv('INCIDENTIQ_PRODUCT_ID')
        )
        
        # Search IIQ by serial or asset tag
        iiq_results = iiq.search_assets(query, limit=5)
        
        if iiq_results:
            # Found in IIQ - format the response
            asset = iiq_results[0]  # Take first match
            
            response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            result = {
                'success': True,
                'device': {
                    'device_id': asset.get('AssetId'),
                    'serial_number': asset.get('SerialNumber', 'N/A'),
                    'asset_tag': asset.get('AssetTag', 'N/A'),
                    'model': asset.get('Model', {}).get('Name', 'N/A') if asset.get('Model') else 'N/A',
                    'status': asset.get('Status', {}).get('Name', 'N/A') if asset.get('Status') else 'N/A',
                    'user': asset.get('Owner', {}).get('Email', 'N/A') if asset.get('Owner') else 'N/A',
                    'location': asset.get('Location', {}).get('Name', 'N/A') if asset.get('Location') else 'N/A',
                    'org_unit_path': 'N/A',
                    'last_sync': asset.get('ModifiedDate', 'N/A'),
                    'mac_address': 'N/A',
                    'ip_address': 'N/A',
                    'os_version': 'N/A',
                    'platform_version': 'N/A',
                    'firmware_version': 'N/A',
                    'recent_users': [],
                    'iiq_asset_id': asset.get('AssetId'),
                    'iiq_location': asset.get('Location', {}).get('Name') if asset.get('Location') else None,
                    'iiq_room': None,
                    'notes': asset.get('Notes'),
                    'meraki': None
                },
                'source': 'incidentiq',
                'response_time_ms': response_time_ms
            }
            
            # Cache for 15 minutes
            cache.set(cache_key, result, ttl=900)
            
            return result
    
    except Exception as e:
        print(f"IIQ API error: {e}")
    
    # Not found anywhere
    result = {'success': False, 'error': 'Device not found in database or IIQ', 'query': q}
    cache.set(cache_key, result, ttl=300)
    return result


@router.get("/search/user")
async def search_user(
    q: str = Query(..., min_length=1, description="User email or name"),
    db_session: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Search for a user and their assigned devices
    
    Performance:
    - Cache hit: < 10ms
    - Database hit: < 100ms
    """
    query = q.strip().lower()
    
    # Try Redis cache first
    cache_key = CacheKeys.user_by_email(query)
    cached_result = cache.get(cache_key)
    
    if cached_result:
        cached_result['source'] = 'cache'
        cached_result['response_time_ms'] = '< 10ms'
        return cached_result
    
    # Search database
    start_time = datetime.now()
    
    # Try exact email match first
    user = db_session.query(User).filter(User.email == query).first()
    
    # If no exact match, try name search
    if not user:
        user = db_session.query(User).filter(
            or_(
                User.full_name.ilike(f'%{query}%'),
                User.email.ilike(f'%{query}%')
            )
        ).first()
    
    if not user:
        result = {
            'success': False,
            'error': 'User not found',
            'query': q
        }
        cache.set(cache_key, result, ttl=300)  # Cache 5 minutes
        return result
    
    # Get user's assigned devices
    devices = []
    if user.assigned_devices:
        devices = db_session.query(Chromebook).filter(
            Chromebook.device_id.in_(user.assigned_devices)
        ).all()
        devices = [d.to_dict() for d in devices]
    
    response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
    
    result = {
        'success': True,
        'user': user.to_dict(),
        'devices': devices,
        'device_count': len(devices),
        'source': 'database',
        'response_time_ms': response_time_ms
    }
    
    # Cache for 15 minutes
    cache.set(cache_key, result, ttl=900)
    
    return result


@router.get("/devices")
async def list_devices(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    status: Optional[str] = None,
    org_unit: Optional[str] = None,
    db_session: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    List all devices with pagination and filtering
    
    Performance: < 200ms for typical queries
    """
    query = db_session.query(Chromebook)
    
    # Apply filters
    if status:
        query = query.filter(Chromebook.status == status.upper())
    
    if org_unit:
        query = query.filter(Chromebook.org_unit_path.ilike(f'%{org_unit}%'))
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    devices = query.offset(offset).limit(limit).all()
    
    return {
        'success': True,
        'devices': [d.to_dict() for d in devices],
        'total': total,
        'limit': limit,
        'offset': offset,
        'has_more': (offset + limit) < total
    }


@router.get("/users")
async def list_users(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    org_unit: Optional[str] = None,
    has_devices: Optional[bool] = None,
    db_session: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    List all users with pagination and filtering
    
    Performance: < 200ms for typical queries
    """
    query = db_session.query(User)
    
    # Apply filters
    if org_unit:
        query = query.filter(User.org_unit_path.ilike(f'%{org_unit}%'))
    
    if has_devices is not None:
        if has_devices:
            query = query.filter(User.device_count > 0)
        else:
            query = query.filter(User.device_count == 0)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    users = query.offset(offset).limit(limit).all()
    
    return {
        'success': True,
        'users': [u.to_dict() for u in users],
        'total': total,
        'limit': limit,
        'offset': offset,
        'has_more': (offset + limit) < total
    }


def update_sync_progress(log_entries, status='running', **extra):
    """Update sync status in Redis with log entries"""
    data = {
        'status': status,
        'log': log_entries,
        **extra
    }
    cache.set(CacheKeys.sync_status(), data, ttl=86400)


def run_sync_background():
    """Run sync in background thread and update status with progress"""
    import os
    import sys
    sys.path.insert(0, '/opt/chromebook-dashboard')

    log_entries = []
    start_time = datetime.now()

    def add_log(message, log_type='info'):
        log_entries.append({'message': message, 'type': log_type})
        update_sync_progress(log_entries, status='running')

    try:
        from services.sync_service_simple import SimpleSyncService
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from integrations.incidentiq import IncidentIQClient
        from integrations.meraki import MerakiClient

        add_log('Initializing API connections...', 'info')

        # Google Wrapper class with progress reporting
        class GoogleWrapper:
            def __init__(self, service, progress_callback):
                self.service = service
                self.customer_id = os.getenv('GOOGLE_CUSTOMER_ID', 'my_customer')
                self.progress_callback = progress_callback

            def get_chromebooks(self, max_results=50000):
                devices = []
                self.progress_callback('Fetching devices from Google Admin...', 'info')
                request = self.service.chromeosdevices().list(
                    customerId=self.customer_id,
                    maxResults=200,
                    projection='FULL'
                )
                while request is not None:
                    response = request.execute()
                    batch = response.get('chromeosdevices', [])
                    devices.extend(batch)
                    if len(devices) % 1000 == 0 or len(devices) < 1000:
                        self.progress_callback(f'Google Admin: Retrieved {len(devices)} devices...', 'info')
                    request = self.service.chromeosdevices().list_next(request, response)
                self.progress_callback(f'Google Admin: Complete - {len(devices)} devices retrieved', 'success')
                return devices

        # Initialize Google service
        add_log('Connecting to Google Admin API...', 'info')
        SCOPES = ['https://www.googleapis.com/auth/admin.directory.device.chromeos.readonly']
        creds_path = os.getenv('GOOGLE_CREDENTIALS_PATH', '/opt/chromebook-dashboard/credentials.json')
        admin_email = os.getenv('GOOGLE_ADMIN_EMAIL', 'gsync@cr.k12.de.us')

        credentials = service_account.Credentials.from_service_account_file(
            creds_path, scopes=SCOPES
        )
        credentials = credentials.with_subject(admin_email)
        google_raw = build('admin', 'directory_v1', credentials=credentials)
        google = GoogleWrapper(google_raw, add_log)
        add_log('Google Admin API connected', 'success')

        # Initialize IIQ
        add_log('Connecting to IncidentIQ API...', 'info')
        iiq_site = os.getenv('INCIDENTIQ_SITE_ID', '')
        iiq_token = os.getenv('INCIDENTIQ_API_TOKEN', '')
        iiq_product = os.getenv('INCIDENTIQ_PRODUCT_ID', '88df910c-91aa-e711-80c2-0004ffa00050')
        iiq = IncidentIQClient(iiq_site, iiq_token, iiq_product)
        add_log('IncidentIQ API connected', 'success')

        # Initialize Meraki (optional)
        meraki_key = os.getenv('MERAKI_API_KEY', '')
        meraki_org = os.getenv('MERAKI_ORG_ID', '')
        meraki = None
        if meraki_key:
            add_log('Connecting to Meraki API...', 'info')
            meraki = MerakiClient(meraki_key, meraki_org)
            add_log('Meraki API connected', 'success')

        # Create custom sync service with progress
        add_log('Starting data synchronization...', 'info')

        # Fetch Google devices
        google_devices = google.get_chromebooks()

        # Fetch IIQ assets
        add_log('Fetching assets from IncidentIQ...', 'info')
        iiq_assets = iiq.search_assets("", limit=50000)
        add_log(f'IncidentIQ: Retrieved {len(iiq_assets)} assets', 'success')

        # Process and sync to database
        add_log('Processing and updating database...', 'info')

        # Create lookup by serial
        iiq_lookup = {}
        for asset in iiq_assets:
            serial = asset.get('SerialNumber', '').upper()
            if serial:
                iiq_lookup[serial] = asset

        # Import database models
        from database.models import Chromebook, SyncLog
        from database.connection import db

        processed = 0
        created = 0
        updated = 0

        with db.get_session() as session:
            for device in google_devices:
                processed += 1
                device_id = device.get('deviceId')
                serial = device.get('serialNumber', '').upper()

                if not device_id or not serial:
                    continue

                iiq_data = iiq_lookup.get(serial, {})

                existing = session.query(Chromebook).filter(
                    Chromebook.device_id == device_id
                ).first()

                # Extract battery health from Google API response
                battery_health = None
                battery_cycles = None
                battery_reports = device.get('batteryStatusReports', [])
                if battery_reports:
                    latest_report = battery_reports[0]
                    # Calculate health percentage from capacity if available
                    full_charge = latest_report.get('fullChargeCapacity')
                    design_capacity = latest_report.get('designCapacity')
                    if full_charge and design_capacity and design_capacity > 0:
                        battery_health = int((full_charge / design_capacity) * 100)
                        if battery_health > 100:
                            battery_health = 100
                    battery_cycles = latest_report.get('cycleCount')

                if existing:
                    # Update existing
                    existing.serial_number = serial
                    mac_raw = device.get("macAddress", "").replace(":", "").lower()
                    if mac_raw and len(mac_raw) == 12:
                        existing.mac_address = ":".join(mac_raw[i:i+2] for i in range(0, 12, 2))
                    existing.os_version = device.get("osVersion")
                    existing.model = device.get("model")
                    existing.status = device.get("status")
                    existing.org_unit_path = device.get("orgUnitPath")
                    existing.user = device.get("annotatedUser")
                    if iiq_data:
                        existing.asset_tag = iiq_data.get("AssetTag")
                        existing.location = iiq_data.get("LocationName")
                    existing.last_sync = device.get("lastSync")
                    # Update battery data
                    if battery_health is not None:
                        existing.battery_health = battery_health
                    if battery_cycles is not None:
                        existing.battery_cycle_count = battery_cycles
                    updated += 1
                else:
                    # Create new
                    mac_raw = device.get("macAddress", "").replace(":", "").lower()
                    mac_formatted = ":".join(mac_raw[i:i+2] for i in range(0, 12, 2)) if mac_raw and len(mac_raw) == 12 else None
                    new_device = Chromebook(
                        device_id=device_id,
                        serial_number=serial,
                        mac_address=mac_formatted,
                        os_version=device.get("osVersion"),
                        model=device.get("model"),
                        status=device.get("status"),
                        org_unit_path=device.get("orgUnitPath"),
                        user=device.get("annotatedUser"),
                        asset_tag=iiq_data.get("AssetTag") if iiq_data else None,
                        location=iiq_data.get("LocationName") if iiq_data else None,
                        last_sync=device.get("lastSync"),
                        battery_health=battery_health,
                        battery_cycle_count=battery_cycles
                    )
                    session.add(new_device)
                    created += 1

                if processed % 500 == 0:
                    session.commit()
                    add_log(f'Database: Processed {processed} of {len(google_devices)} devices...', 'info')

            session.commit()

        add_log(f'Database: Complete - {processed} processed, {created} created, {updated} updated', 'success')

        # Clear cache
        add_log('Clearing search cache...', 'info')
        cache.delete_pattern('chromebook:*')
        cache.delete_pattern('search:*')
        add_log('Cache cleared', 'success')

        # Calculate duration
        duration = (datetime.now() - start_time).total_seconds()

        # Update final status
        update_sync_progress(log_entries, status='completed',
            last_sync=datetime.now().isoformat(),
            records_processed=processed,
            records_created=created,
            records_updated=updated,
            duration_seconds=int(duration)
        )

    except Exception as e:
        add_log(f'Error: {str(e)}', 'error')
        update_sync_progress(log_entries, status='failed',
            error=str(e),
            failed_at=datetime.now().isoformat()
        )
    finally:
        cache.delete(CacheKeys.sync_lock('full'))


@router.post("/sync/all")
async def trigger_full_sync(
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Trigger a full sync of all data sources

    This should be restricted to admin users only
    Runs in background to avoid timeout
    """
    # Check if sync is already running
    if cache.exists(CacheKeys.sync_lock('full')):
        return {
            'success': False,
            'error': 'Sync already in progress'
        }

    # Set lock for 1 hour
    cache.set(CacheKeys.sync_lock('full'), {'started': datetime.now().isoformat()}, ttl=3600)

    # Update status to show sync is starting
    cache.set(CacheKeys.sync_status(), {
        'status': 'started',
        'started_at': datetime.now().isoformat()
    }, ttl=86400)

    # Run sync in background thread
    sync_thread = threading.Thread(target=run_sync_background)
    sync_thread.start()

    return {
        'success': True,
        'message': 'Full sync started',
        'note': 'This will take 2-5 minutes. Check /sync/status for progress.'
    }


@router.get("/sync/status")
async def get_sync_status(db_session: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get current sync status and last sync information
    
    Performance: < 10ms (from Redis cache)
    """
    # Try Redis cache first
    status = cache.get(CacheKeys.sync_status())
    
    if status:
        return {
            'success': True,
            'status': status,
            'source': 'cache'
        }
    
    # Fall back to database
    from database.models import SyncLog
    
    last_sync = db_session.query(SyncLog).filter(
        SyncLog.status == 'completed'
    ).order_by(SyncLog.completed_at.desc()).first()
    
    if last_sync:
        return {
            'success': True,
            'status': {
                'last_sync': last_sync.completed_at.isoformat(),
                'duration_seconds': last_sync.duration_seconds,
                'records_processed': last_sync.records_processed
            },
            'source': 'database'
        }
    
    return {
        'success': False,
        'error': 'No sync history found'
    }


@router.get("/stats")
async def get_stats(db_session: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get dashboard statistics
    
    Performance: < 100ms
    """
    # Check cache first
    stats_cache = cache.get('dashboard:stats')
    if stats_cache:
        stats_cache['source'] = 'cache'
        return stats_cache
    
    # Calculate from database
    total_chromebooks = db_session.query(Chromebook).count()
    active_chromebooks = db_session.query(Chromebook).filter(Chromebook.status == 'ACTIVE').count()
    total_users = db_session.query(User).count()
    users_with_devices = db_session.query(User).filter(User.device_count > 0).count()
    
    stats = {
        'total_chromebooks': total_chromebooks,
        'active_chromebooks': active_chromebooks,
        'deprovisioned_chromebooks': total_chromebooks - active_chromebooks,
        'total_users': total_users,
        'users_with_devices': users_with_devices,
        'users_without_devices': total_users - users_with_devices,
        'updated_at': datetime.now().isoformat(),
        'source': 'database'
    }
    
    # Cache for 5 minutes
    cache.set('dashboard:stats', stats, ttl=300)
    
    return stats


@router.get("/health")
@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint"""
    health = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'checks': {}
    }
    
    # Check database
    try:
        with db.get_session() as session:
            session.execute(text('SELECT 1'))
        health['checks']['database'] = 'ok'
    except Exception as e:
        health['checks']['database'] = f'error: {str(e)}'
        health['status'] = 'unhealthy'
    
    # Check Redis
    try:
        cache.client.ping()
        redis_stats = cache.get_stats()
        health['checks']['redis'] = {
            'status': 'ok',
            'keys': redis_stats.get('total_keys'),
            'memory': redis_stats.get('used_memory_human')
        }
    except Exception as e:
        health['checks']['redis'] = f'error: {str(e)}'
        health['status'] = 'unhealthy'
    
    # Check last sync
    sync_status = cache.get(CacheKeys.sync_status())
    if sync_status:
        last_sync = datetime.fromisoformat(sync_status['last_sync'])
        hours_since_sync = (datetime.now() - last_sync).total_seconds() / 3600
        
        if hours_since_sync > 24:
            health['checks']['sync'] = f'warning: last sync {int(hours_since_sync)} hours ago'
            health['status'] = 'degraded'
        else:
            health['checks']['sync'] = f'ok: synced {int(hours_since_sync)} hours ago'
    else:
        health['checks']['sync'] = 'warning: no sync data'
        health['status'] = 'degraded'
    
    return health

@router.get("/search/device/live")
async def search_device_live(q: str = Query(..., min_length=1)) -> Dict[str, Any]:
    """
    Live search - bypasses cache and database, hits APIs directly
    USE SPARINGLY - takes 5-8 seconds
    """
    from integrations.google import GoogleWorkspaceClient
    from integrations.incidentiq import IncidentIQClient
    import os
    
    query = q.strip().upper()
    start_time = datetime.now()
    
    try:
        # Initialize API clients
        google = GoogleWorkspaceClient('/opt/chromebook-dashboard/credentials.json', os.getenv('GOOGLE_ADMIN_EMAIL'))
        iiq = IncidentIQClient(os.getenv('IIQ_SITE_ID'), os.getenv('IIQ_API_TOKEN'))
        
        # Search Google by serial
        devices = google.search_chromebooks(serial=query)
        
        if not devices:
            return {'success': False, 'error': 'Device not found in Google Admin', 'query': q}
        
        device = devices[0]
        
        # Get IIQ data
        iiq_data = {}
        if device.get('serialNumber'):
            iiq_assets = iiq.search_assets(device['serialNumber'], limit=1)
            if iiq_assets:
                iiq_data = iiq_assets[0]
        
        # Build response in same format as cached
        response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        result = {
            'success': True,
            'device': {
                'device_id': device.get('deviceId'),
                'serial_number': device.get('serialNumber'),
                'asset_tag': device.get('annotatedAssetId') or iiq_data.get('AssetTag'),
                'model': device.get('model'),
                'status': device.get('status'),
                'user': device.get('annotatedUser'),
                'location': device.get('annotatedLocation'),
                'org_unit_path': device.get('orgUnitPath'),
                'last_sync': device.get('lastSync'),
                'mac_address': device.get('macAddress'),
                'ip_address': device['lastKnownNetwork'][0].get('ipAddress') if device.get('lastKnownNetwork') else None,
                'os_version': device.get('osVersion'),
                'platform_version': device.get('platformVersion'),
                'firmware_version': device.get('firmwareVersion'),
                'recent_users': device.get('recentUsers', []),
                'iiq_asset_id': iiq_data.get('AssetID'),
                'iiq_location': iiq_data.get('LocationName'),
                'iiq_room': iiq_data.get('RoomName'),
                'meraki': None
            },
            'source': 'live_api',
            'response_time_ms': response_time_ms,
            'warning': 'Live data - not cached'
        }
        
        return result
        
    except Exception as e:
        return {
            'success': False,
            'error': f'Live API error: {str(e)}',
            'query': q
        }
