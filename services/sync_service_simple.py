"""
Simplified sync service for chromebooks only (to start)
"""
from datetime import datetime
from typing import Dict, Any
from sqlalchemy.orm import Session

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import Chromebook, SyncLog, Asset
from database.connection import db
from cache.redis_manager import cache, CacheKeys


class SimpleSyncService:
    """Simplified service to sync chromebooks from your APIs"""
    
    def __init__(self, google_api, iiq_api, meraki_api):
        self.google = google_api
        self.iiq = iiq_api
        self.meraki = meraki_api
    
    def sync_chromebooks(self) -> Dict[str, Any]:
        """Sync all assets from IIQ, then enhance chromebooks with Google Admin data"""
        start_time = datetime.now()
        assets_processed = 0
        assets_created = 0
        assets_updated = 0
        chromebooks_processed = 0
        chromebooks_created = 0
        chromebooks_updated = 0

        # Create sync log
        with db.get_session() as session:
            sync_log = SyncLog(
                sync_type='iiq_first_sync',
                status='started',
                started_at=start_time
            )
            session.add(sync_log)
            session.commit()
            log_id = sync_log.id

        try:
            # STEP 1: Fetch ALL assets from IncidentIQ (chromebooks, iPads, laptops, etc.)
            print("STEP 1: Fetching all assets from IncidentIQ...")
            iiq_raw_assets = self.iiq.search_assets("", limit=100000)
            print(f"  Found {len(iiq_raw_assets)} total assets in IIQ")

            # Extract and categorize by device type
            all_assets = []
            chromebook_serials = []

            for raw_asset in iiq_raw_assets:
                asset_info = self.iiq.extract_asset_info(raw_asset)
                all_assets.append(asset_info)

                if asset_info.get('isChromebook'):
                    serial = asset_info.get('serialNumber', '')
                    if serial and serial != 'N/A':
                        chromebook_serials.append(serial)

            print(f"  Categorized: {len(chromebook_serials)} chromebooks, {len(all_assets) - len(chromebook_serials)} other assets")

            # STEP 2: Store all IIQ assets in assets table
            print("STEP 2: Storing all IIQ assets in database...")
            with db.get_session() as session:
                for asset in all_assets:
                    assets_processed += 1

                    asset_id = asset.get('assetId', '')
                    if not asset_id:
                        continue

                    # Check if asset exists
                    existing = session.query(Asset).filter(
                        Asset.asset_id == asset_id
                    ).first()

                    if existing:
                        # Update
                        existing.asset_tag = asset.get('assetTag', 'N/A')
                        existing.serial_number = asset.get('serialNumber', 'N/A')
                        existing.device_type = asset.get('deviceType', 'Unknown')
                        existing.model = asset.get('model', 'N/A')
                        existing.status = asset.get('status', 'N/A')
                        existing.owner_email = asset.get('assignedUserEmail', '')
                        existing.owner_name = asset.get('assignedUser', 'Not assigned')
                        existing.location = asset.get('location', 'N/A')
                        existing.room = asset.get('room', 'N/A')
                        existing.last_synced = datetime.now()
                        assets_updated += 1
                    else:
                        # Create
                        new_asset = Asset(
                            asset_id=asset_id,
                            asset_tag=asset.get('assetTag', 'N/A'),
                            serial_number=asset.get('serialNumber', 'N/A'),
                            device_type=asset.get('deviceType', 'Unknown'),
                            model=asset.get('model', 'N/A'),
                            status=asset.get('status', 'N/A'),
                            owner_email=asset.get('assignedUserEmail', ''),
                            owner_name=asset.get('assignedUser', 'Not assigned'),
                            location=asset.get('location', 'N/A'),
                            room=asset.get('room', 'N/A'),
                            last_synced=datetime.now()
                        )
                        session.add(new_asset)
                        assets_created += 1

                    if assets_processed % 100 == 0:
                        session.commit()
                        print(f"  Processed {assets_processed} assets...")

                session.commit()

            print(f"  Assets: {assets_processed} processed, {assets_created} created, {assets_updated} updated")

            # STEP 3: For chromebooks only, fetch Google Admin data
            print("STEP 3: Fetching Google Admin data for chromebooks...")
            google_devices = self.google.get_chromebooks(max_results=50000)
            print(f"  Found {len(google_devices)} devices in Google Admin")
            
            # STEP 4: Create lookup by serial number for IIQ data
            iiq_lookup = {}
            for asset in iiq_raw_assets:
                serial = asset.get('SerialNumber', '').upper()
                if serial:
                    iiq_lookup[serial] = asset

            # STEP 5: Store/update Google Admin data for chromebooks in chromebooks table
            print("STEP 4: Storing Google Admin data for chromebooks...")
            with db.get_session() as session:
                for device in google_devices:
                    chromebooks_processed += 1
                    
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
                        # Update
                        existing.serial_number = serial
                        
                        # Format MAC address
                        mac_raw = device.get("macAddress", "").replace(":", "").lower()
                        if mac_raw and len(mac_raw) == 12:
                            existing.mac_address = ":".join(mac_raw[i:i+2] for i in range(0, 12, 2))
                        else:
                            existing.mac_address = device.get("macAddress")
                        
                        existing.ethernet_mac = device.get("ethernetMacAddress")
                        
                        # Get IP addresses
                        if device.get("lastKnownNetwork") and len(device["lastKnownNetwork"]) > 0:
                            existing.ip_address = device["lastKnownNetwork"][0].get("ipAddress")
                            existing.wan_ip_address = device["lastKnownNetwork"][0].get("wanIpAddress")
                        
                        existing.os_version = device.get("osVersion")
                        existing.platform_version = device.get("platformVersion")
                        existing.firmware_version = device.get("firmwareVersion")
                        existing.asset_tag = device.get('annotatedAssetId') or iiq_data.get('AssetTag')
                        existing.model = device.get('model')
                        existing.status = device.get('status')
                        existing.annotated_user = device.get('annotatedUser')
                        existing.annotated_location = device.get('annotatedLocation')
                        existing.org_unit_path = device.get('orgUnitPath')
                        existing.last_sync_status = device.get('lastSync')
                        existing.recent_users = device.get('recentUsers', [])
                        
                        if iiq_data:
                            existing.iiq_asset_id = iiq_data.get('AssetID')
                            existing.iiq_location = iiq_data.get('LocationName')
                            existing.iiq_room = iiq_data.get('RoomName')

                            # Extract owner information
                            owner = iiq_data.get('Owner', {})
                            if isinstance(owner, dict):
                                existing.iiq_owner_email = owner.get('Email')
                                existing.iiq_owner_name = owner.get('FullName')

                            # Extract status
                            status = iiq_data.get('Status', {})
                            if isinstance(status, dict):
                                existing.iiq_status = status.get('Name')
                        else:
                            # Fallback: Query assets table for IIQ data if not in lookup
                            asset = session.query(Asset).filter(Asset.serial_number == serial).first()
                            if asset:
                                existing.iiq_asset_id = asset.asset_id
                                existing.iiq_location = asset.location
                                existing.iiq_room = asset.room
                                existing.iiq_status = asset.status
                                existing.iiq_owner_email = asset.owner_email
                                existing.iiq_owner_name = asset.owner_name

                        chromebooks_updated += 1
                    else:
                        # Create new
                        # Create new
                        # Format MAC address
                        mac_raw = device.get("macAddress", "").replace(":", "").lower()
                        if mac_raw and len(mac_raw) == 12:
                            formatted_mac = ":".join(mac_raw[i:i+2] for i in range(0, 12, 2))
                        else:
                            formatted_mac = device.get("macAddress")
                        
                        # Get WAN IP
                        wan_ip = None
                        lan_ip = None
                        if device.get("lastKnownNetwork") and len(device["lastKnownNetwork"]) > 0:
                            lan_ip = device["lastKnownNetwork"][0].get("ipAddress")
                            wan_ip = device["lastKnownNetwork"][0].get("wanIpAddress")
                        
                        # Extract IIQ owner and status
                        iiq_owner_email = None
                        iiq_owner_name = None
                        iiq_status = None
                        iiq_asset_id = None
                        iiq_location = None
                        iiq_room = None
                        iiq_asset_tag = None

                        if iiq_data:
                            owner = iiq_data.get('Owner', {})
                            if isinstance(owner, dict):
                                iiq_owner_email = owner.get('Email')
                                iiq_owner_name = owner.get('FullName')
                            status_obj = iiq_data.get('Status', {})
                            if isinstance(status_obj, dict):
                                iiq_status = status_obj.get('Name')
                            iiq_asset_id = iiq_data.get('AssetID')
                            iiq_location = iiq_data.get('LocationName')
                            iiq_room = iiq_data.get('RoomName')
                            iiq_asset_tag = iiq_data.get('AssetTag')
                        else:
                            # Fallback: Query assets table for IIQ data if not in lookup
                            asset = session.query(Asset).filter(Asset.serial_number == serial).first()
                            if asset:
                                iiq_asset_id = asset.asset_id
                                iiq_location = asset.location
                                iiq_room = asset.room
                                iiq_status = asset.status
                                iiq_owner_email = asset.owner_email
                                iiq_owner_name = asset.owner_name
                                iiq_asset_tag = asset.asset_tag

                        new_device = Chromebook(
                            device_id=device_id,
                            mac_address=formatted_mac,
                            ethernet_mac=device.get("ethernetMacAddress"),
                            ip_address=lan_ip,
                            wan_ip_address=wan_ip,
                            firmware_version=device.get("firmwareVersion"),
                            serial_number=serial,
                            asset_tag=device.get('annotatedAssetId') or iiq_asset_tag,
                            model=device.get('model'),
                            status=device.get('status'),
                            annotated_user=device.get('annotatedUser'),
                            annotated_location=device.get('annotatedLocation'),
                            org_unit_path=device.get('orgUnitPath'),
                            last_sync_status=device.get('lastSync'),
                            recent_users=device.get('recentUsers', []),
                            iiq_asset_id=iiq_asset_id,
                            iiq_location=iiq_location,
                            iiq_room=iiq_room,
                            iiq_owner_email=iiq_owner_email,
                            iiq_owner_name=iiq_owner_name,
                            iiq_status=iiq_status,
                            data_source='merged'
                        )
                        session.add(new_device)
                        chromebooks_created += 1

                    if chromebooks_processed % 100 == 0:
                        session.commit()
                        print(f"  Processed {chromebooks_processed} chromebooks...")
                
                session.commit()
            
            # Update sync log
            with db.get_session() as session:
                sync_log = session.query(SyncLog).filter(SyncLog.id == log_id).first()
                sync_log.status = 'completed'
                sync_log.completed_at = datetime.now()
                sync_log.duration_seconds = int((datetime.now() - start_time).total_seconds())
                sync_log.records_processed = assets_processed + chromebooks_processed
                sync_log.records_created = assets_created + chromebooks_created
                sync_log.records_updated = assets_updated + chromebooks_updated
                session.commit()

            # Clear cache
            cache.delete_pattern('chromebook:*')
            cache.delete_pattern('search:*')
            cache.delete_pattern('asset:*')

            # Update sync status
            sync_status = {
                'last_sync': datetime.now().isoformat(),
                'assets': {'processed': assets_processed, 'created': assets_created, 'updated': assets_updated},
                'chromebooks': {'processed': chromebooks_processed, 'created': chromebooks_created, 'updated': chromebooks_updated},
                'duration_seconds': int((datetime.now() - start_time).total_seconds())
            }
            cache.set(CacheKeys.sync_status(), sync_status, ttl=86400)

            print(f"\n✓ Sync complete:")
            print(f"  Assets: {assets_processed} processed, {assets_created} created, {assets_updated} updated")
            print(f"  Chromebooks: {chromebooks_processed} processed, {chromebooks_created} created, {chromebooks_updated} updated")

            return {
                'success': True,
                'assets_processed': assets_processed,
                'assets_created': assets_created,
                'assets_updated': assets_updated,
                'chromebooks_processed': chromebooks_processed,
                'chromebooks_created': chromebooks_created,
                'chromebooks_updated': chromebooks_updated,
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
            
            print(f"\n✗ Sync failed: {e}")
            raise
