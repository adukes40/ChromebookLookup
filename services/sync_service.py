"""
Sync service to populate PostgreSQL database from Google Admin, IncidentIQ, and Meraki APIs
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from database.models import Chromebook, User, MerakiClient, SyncLog
from database.connection import db
from cache.redis_manager import cache, CacheKeys


class SyncService:
    """Service to sync data from APIs to PostgreSQL database"""
    
    def __init__(self, google_service, iiq_service, meraki_service):
        """
        Initialize sync service with API clients
        
        Args:
            google_service: Google Workspace API client
            iiq_service: IncidentIQ API client
            meraki_service: Meraki API client
        """
        self.google = google_service
        self.iiq = iiq_service
        self.meraki = meraki_service
    
    async def sync_all(self) -> Dict[str, Any]:
        """
        Full sync of all data sources
        
        Returns:
            Dictionary with sync results
        """
        start_time = datetime.now()
        
        # Create sync log
        with db.get_session() as session:
            sync_log = SyncLog(
                sync_type='full',
                status='started',
                started_at=start_time
            )
            session.add(sync_log)
            session.commit()
            log_id = sync_log.id
        
        try:
            # Sync in parallel where possible
            chromebook_result = await self.sync_chromebooks()
            user_result = await self.sync_users()
            meraki_result = await self.sync_meraki()
            
            # Update sync log
            with db.get_session() as session:
                sync_log = session.query(SyncLog).filter(SyncLog.id == log_id).first()
                sync_log.status = 'completed'
                sync_log.completed_at = datetime.now()
                sync_log.duration_seconds = int((datetime.now() - start_time).total_seconds())
                sync_log.records_processed = (
                    chromebook_result['processed'] +
                    user_result['processed'] +
                    meraki_result['processed']
                )
                sync_log.records_created = (
                    chromebook_result['created'] +
                    user_result['created'] +
                    meraki_result['created']
                )
                sync_log.records_updated = (
                    chromebook_result['updated'] +
                    user_result['updated'] +
                    meraki_result['updated']
                )
                session.commit()
            
            # Clear Redis cache after successful sync
            cache.delete_pattern('chromebook:*')
            cache.delete_pattern('user:*')
            cache.delete_pattern('search:*')
            
            # Update sync status in Redis
            sync_status = {
                'last_sync': datetime.now().isoformat(),
                'chromebooks': chromebook_result,
                'users': user_result,
                'meraki': meraki_result,
                'duration_seconds': int((datetime.now() - start_time).total_seconds())
            }
            cache.set(CacheKeys.sync_status(), sync_status, ttl=86400)  # 24 hours
            
            return {
                'success': True,
                'sync_id': log_id,
                'duration_seconds': int((datetime.now() - start_time).total_seconds()),
                'results': {
                    'chromebooks': chromebook_result,
                    'users': user_result,
                    'meraki': meraki_result
                }
            }
        
        except Exception as e:
            # Update sync log with error
            with db.get_session() as session:
                sync_log = session.query(SyncLog).filter(SyncLog.id == log_id).first()
                sync_log.status = 'failed'
                sync_log.completed_at = datetime.now()
                sync_log.duration_seconds = int((datetime.now() - start_time).total_seconds())
                sync_log.error_message = str(e)
                session.commit()
            
            return {
                'success': False,
                'sync_id': log_id,
                'error': str(e)
            }
    
    async def sync_chromebooks(self) -> Dict[str, int]:
        """
        Sync chromebooks from Google Admin + IncidentIQ
        
        Returns:
            Dictionary with sync statistics
        """
        start_time = datetime.now()
        processed = 0
        created = 0
        updated = 0
        
        # Create sync log
        with db.get_session() as session:
            sync_log = SyncLog(
                sync_type='chromebooks',
                status='started',
                started_at=start_time
            )
            session.add(sync_log)
            session.commit()
            log_id = sync_log.id
        
        try:
            # Fetch chromebooks from Google Admin
            print("Fetching chromebooks from Google Admin...")
            google_devices = await self.google.list_chromebooks()  # Your existing method
            
            # Fetch assets from IncidentIQ
            print("Fetching assets from IncidentIQ...")
            iiq_assets = await self.iiq.list_chromebook_assets()  # Your existing method
            
            # Create lookup dictionary for IIQ data by serial number
            iiq_lookup = {asset['serialNumber'].upper(): asset for asset in iiq_assets if asset.get('serialNumber')}
            
            # Process each device
            with db.get_session() as session:
                for device in google_devices:
                    processed += 1
                    
                    # Extract data from Google
                    device_id = device.get('deviceId')
                    serial = device.get('serialNumber', '').upper()
                    
                    if not device_id or not serial:
                        continue
                    
                    # Find matching IIQ data
                    iiq_data = iiq_lookup.get(serial, {})
                    
                    # Check if device exists
                    existing = session.query(Chromebook).filter(
                        Chromebook.device_id == device_id
                    ).first()
                    
                    if existing:
                        # Update existing device
                        existing.serial_number = serial
                        existing.asset_tag = device.get('annotatedAssetId') or iiq_data.get('assetTag')
                        existing.model = device.get('model')
                        existing.status = device.get('status')
                        existing.annotated_user = device.get('annotatedUser')
                        existing.annotated_location = device.get('annotatedLocation')
                        existing.annotated_asset_id = device.get('annotatedAssetId')
                        existing.org_unit_path = device.get('orgUnitPath')
                        existing.last_sync_status = device.get('lastSync')
                        existing.last_policy_sync_time = self._parse_datetime(device.get('lastPolicySync'))
                        existing.recent_users = device.get('recentUsers', [])
                        
                        # Update IIQ data
                        if iiq_data:
                            existing.iiq_asset_id = iiq_data.get('id')
                            existing.iiq_location = iiq_data.get('location')
                            existing.iiq_room = iiq_data.get('room')
                            existing.iiq_notes = iiq_data.get('notes')
                        
                        existing.updated_at = datetime.now()
                        existing.data_source = 'merged'
                        updated += 1
                    else:
                        # Create new device
                        new_device = Chromebook(
                            device_id=device_id,
                            serial_number=serial,
                            asset_tag=device.get('annotatedAssetId') or iiq_data.get('assetTag'),
                            model=device.get('model'),
                            status=device.get('status'),
                            annotated_user=device.get('annotatedUser'),
                            annotated_location=device.get('annotatedLocation'),
                            annotated_asset_id=device.get('annotatedAssetId'),
                            org_unit_path=device.get('orgUnitPath'),
                            last_sync_status=device.get('lastSync'),
                            last_policy_sync_time=self._parse_datetime(device.get('lastPolicySync')),
                            recent_users=device.get('recentUsers', []),
                            iiq_asset_id=iiq_data.get('id'),
                            iiq_location=iiq_data.get('location'),
                            iiq_room=iiq_data.get('room'),
                            iiq_notes=iiq_data.get('notes'),
                            data_source='merged'
                        )
                        session.add(new_device)
                        created += 1
                    
                    # Commit every 100 devices
                    if processed % 100 == 0:
                        session.commit()
                        print(f"Processed {processed} chromebooks...")
                
                # Final commit
                session.commit()
            
            # Update sync log
            with db.get_session() as session:
                sync_log = session.query(SyncLog).filter(SyncLog.id == log_id).first()
                sync_log.status = 'completed'
                sync_log.completed_at = datetime.now()
                sync_log.duration_seconds = int((datetime.now() - start_time).total_seconds())
                sync_log.records_processed = processed
                sync_log.records_created = created
                sync_log.records_updated = updated
                session.commit()
            
            print(f"✓ Chromebook sync complete: {processed} processed, {created} created, {updated} updated")
            
            return {
                'processed': processed,
                'created': created,
                'updated': updated,
                'duration_seconds': int((datetime.now() - start_time).total_seconds())
            }
        
        except Exception as e:
            # Update sync log with error
            with db.get_session() as session:
                sync_log = session.query(SyncLog).filter(SyncLog.id == log_id).first()
                sync_log.status = 'failed'
                sync_log.completed_at = datetime.now()
                sync_log.error_message = str(e)
                session.commit()
            
            print(f"✗ Chromebook sync failed: {e}")
            raise
    
    async def sync_users(self) -> Dict[str, int]:
        """
        Sync users from Google Admin
        
        Returns:
            Dictionary with sync statistics
        """
        start_time = datetime.now()
        processed = 0
        created = 0
        updated = 0
        
        try:
            # Fetch users from Google Admin
            print("Fetching users from Google Admin...")
            google_users = await self.google.list_users()  # Your existing method
            
            # Process each user
            with db.get_session() as session:
                for user in google_users:
                    processed += 1
                    
                    user_id = user.get('id')
                    email = user.get('primaryEmail', '').lower()
                    
                    if not user_id or not email:
                        continue
                    
                    # Get assigned chromebooks
                    assigned_devices = []
                    device_count = 0
                    
                    # Query chromebooks assigned to this user
                    chromebooks = session.query(Chromebook).filter(
                        Chromebook.annotated_user == email
                    ).all()
                    
                    if chromebooks:
                        assigned_devices = [cb.device_id for cb in chromebooks]
                        device_count = len(assigned_devices)
                    
                    # Check if user exists
                    existing = session.query(User).filter(
                        User.user_id == user_id
                    ).first()
                    
                    if existing:
                        # Update existing user
                        existing.email = email
                        existing.full_name = user.get('name', {}).get('fullName')
                        existing.first_name = user.get('name', {}).get('givenName')
                        existing.last_name = user.get('name', {}).get('familyName')
                        existing.org_unit_path = user.get('orgUnitPath')
                        existing.is_admin = user.get('isAdmin', False)
                        existing.is_suspended = user.get('suspended', False)
                        existing.assigned_devices = assigned_devices
                        existing.device_count = device_count
                        existing.last_login = self._parse_datetime(user.get('lastLoginTime'))
                        existing.updated_at = datetime.now()
                        updated += 1
                    else:
                        # Create new user
                        new_user = User(
                            user_id=user_id,
                            email=email,
                            full_name=user.get('name', {}).get('fullName'),
                            first_name=user.get('name', {}).get('givenName'),
                            last_name=user.get('name', {}).get('familyName'),
                            org_unit_path=user.get('orgUnitPath'),
                            is_admin=user.get('isAdmin', False),
                            is_suspended=user.get('suspended', False),
                            assigned_devices=assigned_devices,
                            device_count=device_count,
                            last_login=self._parse_datetime(user.get('lastLoginTime'))
                        )
                        session.add(new_user)
                        created += 1
                    
                    # Commit every 100 users
                    if processed % 100 == 0:
                        session.commit()
                        print(f"Processed {processed} users...")
                
                # Final commit
                session.commit()
            
            print(f"✓ User sync complete: {processed} processed, {created} created, {updated} updated")
            
            return {
                'processed': processed,
                'created': created,
                'updated': updated,
                'duration_seconds': int((datetime.now() - start_time).total_seconds())
            }
        
        except Exception as e:
            print(f"✗ User sync failed: {e}")
            raise
    
    async def sync_meraki(self) -> Dict[str, int]:
        """
        Sync Meraki client location data
        
        Returns:
            Dictionary with sync statistics
        """
        start_time = datetime.now()
        processed = 0
        created = 0
        updated = 0
        
        try:
            # Fetch Meraki clients
            print("Fetching Meraki client data...")
            meraki_clients = await self.meraki.list_clients()  # Your existing method
            
            # Process each client
            with db.get_session() as session:
                for client in meraki_clients:
                    processed += 1
                    
                    mac = client.get('mac', '').upper()
                    if not mac:
                        continue
                    
                    # Check if client exists
                    existing = session.query(MerakiClient).filter(
                        MerakiClient.mac_address == mac
                    ).first()
                    
                    if existing:
                        # Update existing client
                        existing.network_id = client.get('networkId')
                        existing.network_name = client.get('networkName')
                        existing.ap_name = client.get('apName')
                        existing.ap_mac = client.get('apMac')
                        existing.ip_address = client.get('ip')
                        existing.vlan = client.get('vlan')
                        existing.description = client.get('description')
                        existing.first_seen = self._parse_datetime(client.get('firstSeen'))
                        existing.last_seen = self._parse_datetime(client.get('lastSeen'))
                        existing.updated_at = datetime.now()
                        updated += 1
                    else:
                        # Create new client
                        new_client = MerakiClient(
                            mac_address=mac,
                            network_id=client.get('networkId'),
                            network_name=client.get('networkName'),
                            ap_name=client.get('apName'),
                            ap_mac=client.get('apMac'),
                            ip_address=client.get('ip'),
                            vlan=client.get('vlan'),
                            description=client.get('description'),
                            first_seen=self._parse_datetime(client.get('firstSeen')),
                            last_seen=self._parse_datetime(client.get('lastSeen'))
                        )
                        session.add(new_client)
                        created += 1
                    
                    # Commit every 100 clients
                    if processed % 100 == 0:
                        session.commit()
                        print(f"Processed {processed} Meraki clients...")
                
                # Final commit
                session.commit()
                
                # Update chromebooks with Meraki data
                print("Linking Meraki data to chromebooks...")
                self._link_meraki_to_chromebooks(session)
            
            print(f"✓ Meraki sync complete: {processed} processed, {created} created, {updated} updated")
            
            return {
                'processed': processed,
                'created': created,
                'updated': updated,
                'duration_seconds': int((datetime.now() - start_time).total_seconds())
            }
        
        except Exception as e:
            print(f"✗ Meraki sync failed: {e}")
            raise
    
    def _link_meraki_to_chromebooks(self, session: Session):
        """Link Meraki client data to chromebooks (best effort by MAC matching)"""
        # This is simplified - you may need more sophisticated matching logic
        # For now, we'll just update chromebooks with recent Meraki data
        
        # Get all chromebooks
        chromebooks = session.query(Chromebook).all()
        
        for chromebook in chromebooks:
            # Try to find Meraki client data
            # Note: You'll need to add MAC address field to Chromebook model
            # or use another matching strategy
            pass  # Implement your matching logic here
    
    def _parse_datetime(self, dt_string: Optional[str]) -> Optional[datetime]:
        """Parse datetime string to datetime object"""
        if not dt_string:
            return None
        
        try:
            # Try ISO format first
            return datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        except:
            try:
                # Try other common formats
                return datetime.strptime(dt_string, '%Y-%m-%dT%H:%M:%S.%fZ')
            except:
                return None
    
    def get_sync_status(self) -> Dict[str, Any]:
        """
        Get last sync status
        
        Returns:
            Dictionary with sync status information
        """
        # Try Redis first
        status = cache.get(CacheKeys.sync_status())
        if status:
            return status
        
        # Fall back to database
        with db.get_session() as session:
            last_sync = session.query(SyncLog).filter(
                SyncLog.status == 'completed'
            ).order_by(SyncLog.completed_at.desc()).first()
            
            if last_sync:
                return {
                    'last_sync': last_sync.completed_at.isoformat(),
                    'duration_seconds': last_sync.duration_seconds,
                    'records_processed': last_sync.records_processed
                }
            
            return {'last_sync': None}
    
    def get_sync_history(self, limit: int = 10) -> List[Dict]:
        """
        Get recent sync history
        
        Args:
            limit: Number of recent syncs to return
        
        Returns:
            List of sync log dictionaries
        """
        with db.get_session() as session:
            logs = session.query(SyncLog).order_by(
                SyncLog.started_at.desc()
            ).limit(limit).all()
            
            return [log.to_dict() for log in logs]
