"""
Simplified sync service for chromebooks only (to start)
"""
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.orm import Session
import gc  # Garbage collection for memory optimization
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import psutil  # Memory monitoring
import time

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import Chromebook, SyncLog, Asset, User
from database.connection import db
from cache.redis_manager import cache, CacheKeys
from integrations.google_telemetry import ChromeTelemetryClient
from decimal import Decimal


class SimpleSyncService:
    """Simplified service to sync chromebooks from your APIs"""

    def __init__(self, google_api, iiq_api, meraki_api, telemetry_api=None):
        self.google = google_api
        self.iiq = iiq_api
        self.meraki = meraki_api
        self.telemetry = telemetry_api

    @staticmethod
    def get_memory_percent():
        """Get current system memory usage as percentage (0-100)"""
        return psutil.virtual_memory().percent

    def wait_for_memory(self, max_percent: float = 75.0, check_interval: float = 5.0, max_wait: float = 300.0):
        """
        Wait until memory usage drops below max_percent.

        Args:
            max_percent: Maximum allowed memory usage (default 75%)
            check_interval: How often to check (seconds)
            max_wait: Maximum time to wait (seconds), then proceed anyway

        Returns:
            True if memory is below limit, False if timed out
        """
        start_time = time.time()
        current_mem = self.get_memory_percent()

        if current_mem < max_percent:
            return True

        print(f"  ⚠ Memory at {current_mem:.1f}% (limit: {max_percent}%) - waiting for cleanup...")

        while time.time() - start_time < max_wait:
            time.sleep(check_interval)
            gc.collect()
            current_mem = self.get_memory_percent()

            if current_mem < max_percent:
                print(f"  ✓ Memory down to {current_mem:.1f}% - resuming")
                return True

            elapsed = int(time.time() - start_time)
            print(f"    [{elapsed}s] Memory still at {current_mem:.1f}%...")

        print(f"  ⚠ Timeout waiting for memory (waited {max_wait}s) - proceeding anyway")
        return False
    
    def sync_chromebooks(self) -> Dict[str, Any]:
        """Sync all assets from IIQ, then enhance chromebooks with Google Admin data"""
        start_time = datetime.now()
        assets_processed = 0
        assets_created = 0
        assets_updated = 0
        chromebooks_processed = 0
        chromebooks_created = 0
        chromebooks_updated = 0
        users_processed = 0
        users_created = 0
        users_updated = 0

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
                        existing.owner_student_id = asset.get('assignedUserStudentId', '')
                        existing.owner_student_grade = asset.get('assignedUserGrade', '')
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
                            owner_student_id=asset.get('assignedUserStudentId', ''),
                            owner_student_grade=asset.get('assignedUserGrade', ''),
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

            # STEP 3.5: Fetch battery telemetry data if available
            battery_lookup = {}
            if self.telemetry:
                print("STEP 3.5: Fetching battery telemetry data...")
                try:
                    telemetry_devices = self.telemetry.list_device_telemetry(page_size=100, max_results=50000)
                    print(f"  Found {len(telemetry_devices)} devices with telemetry")

                    # Create lookup by device_id
                    for telemetry in telemetry_devices:
                        device_id = telemetry.get('deviceId')
                        if device_id:
                            battery_info = self.telemetry.extract_battery_info(telemetry)
                            battery_lookup[device_id] = battery_info

                    print(f"  Extracted battery info for {len(battery_lookup)} devices")
                except Exception as e:
                    print(f"  Warning: Failed to fetch battery telemetry: {e}")
                    logger.error(f"Battery telemetry fetch failed: {e}")

            # STEP 4: Create lookup by serial number for IIQ data
            iiq_lookup = {}
            for asset in iiq_raw_assets:
                serial = asset.get('SerialNumber', '').upper()
                if serial:
                    iiq_lookup[serial] = asset

            # STEP 5: Store/update Google Admin data for chromebooks in chromebooks table
            print("STEP 5: Storing Google Admin data for chromebooks...")
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

                        # NEW FIELDS: Quick Wins Phase 2 - Device lifecycle & extended fields
                        existing.auto_update_expiration = device.get('autoUpdateThrough')  # Use autoUpdateThrough (YYYY-MM-DD format)
                        existing.support_end_date = device.get('supportEndDate')
                        existing.boot_mode = device.get('bootMode', 'Verified')
                        existing.device_license_type = device.get('deviceLicenseType')
                        existing.extended_support_enabled = device.get('extendedSupportEnabled', False)
                        existing.extended_support_eligible = device.get('extendedSupportEligible', False)
                        existing.manufacture_date = device.get('manufactureDate')
                        existing.first_enrollment_time = device.get('firstEnrollmentTime')
                        existing.deprovision_reason = device.get('deprovisionReason')

                        # Network information
                        if device.get("lastKnownNetwork") and len(device["lastKnownNetwork"]) > 0:
                            network = device["lastKnownNetwork"][0]
                            existing.last_known_network_name = network.get('name')
                            existing.last_known_network_ssid = network.get('ssid')

                        # OS update status
                        os_update = device.get('osUpdateStatus', {})
                        if isinstance(os_update, dict):
                            existing.os_update_state = os_update.get('state')
                            existing.os_target_version = os_update.get('targetOsVersion')
                        
                        if iiq_data:
                            existing.iiq_asset_id = iiq_data.get('AssetId')  # Fixed: was AssetID, should be AssetId

                            # Extract location from Location object
                            location = iiq_data.get('Location', {})
                            if isinstance(location, dict):
                                existing.iiq_location = location.get('Name')

                            existing.iiq_room = iiq_data.get('LocationRoomId')

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

                        # Update battery data if available
                        if device_id in battery_lookup:
                            battery = battery_lookup[device_id]
                            existing.battery_health = battery.get('battery_health')
                            existing.battery_cycle_count = battery.get('battery_cycle_count')
                            existing.battery_full_charge_capacity = battery.get('battery_full_charge_capacity')
                            existing.battery_design_capacity = battery.get('battery_design_capacity')
                            existing.battery_manufacturer = battery.get('battery_manufacturer')
                            # Convert ISO timestamp string to epoch if available
                            report_time_str = battery.get('battery_report_time')
                            if report_time_str:
                                try:
                                    dt = datetime.fromisoformat(report_time_str.replace('Z', '+00:00'))
                                    existing.battery_report_time = int(dt.timestamp())
                                except:
                                    pass

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
                            iiq_asset_id = iiq_data.get('AssetId')  # Fixed: was AssetID, should be AssetId
                            # Extract location from Location object
                            location_obj = iiq_data.get('Location', {})
                            if isinstance(location_obj, dict):
                                iiq_location = location_obj.get('Name')
                            iiq_room = iiq_data.get('LocationRoomId')
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

                        # Extract network info and OS update status
                        network = device.get("lastKnownNetwork", [{}])[0] if device.get("lastKnownNetwork") else {}
                        os_update = device.get('osUpdateStatus', {})

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
                            # NEW FIELDS: Quick Wins Phase 2
                            auto_update_expiration=device.get('autoUpdateThrough'),  # Use autoUpdateThrough (YYYY-MM-DD format)
                            support_end_date=device.get('supportEndDate'),
                            boot_mode=device.get('bootMode', 'Verified'),
                            device_license_type=device.get('deviceLicenseType'),
                            extended_support_enabled=device.get('extendedSupportEnabled', False),
                            extended_support_eligible=device.get('extendedSupportEligible', False),
                            manufacture_date=device.get('manufactureDate'),
                            first_enrollment_time=device.get('firstEnrollmentTime'),
                            last_known_network_name=network.get('name'),
                            last_known_network_ssid=network.get('ssid'),
                            os_update_state=os_update.get('state') if isinstance(os_update, dict) else None,
                            os_target_version=os_update.get('targetOsVersion') if isinstance(os_update, dict) else None,
                            deprovision_reason=device.get('deprovisionReason'),
                            data_source='merged'
                        )
                        session.add(new_device)
                        chromebooks_created += 1

                    if chromebooks_processed % 100 == 0:
                        session.commit()
                        print(f"  Processed {chromebooks_processed} chromebooks...")

                session.commit()

            # STEP 6: Sync Google Workspace users
            print("STEP 6: Fetching Google Workspace users...")
            try:
                google_users = self.google.list_all_users()
                print(f"  Found {len(google_users)} users in Google Workspace")

                with db.get_session() as session:
                    for user_data in google_users:
                        users_processed += 1

                        user_id = user_data.get('id')
                        email = user_data.get('primaryEmail')

                        if not user_id or not email:
                            continue

                        # Get name components
                        name_obj = user_data.get('name', {})
                        full_name = name_obj.get('fullName', '')
                        first_name = name_obj.get('givenName', '')
                        last_name = name_obj.get('familyName', '')

                        # Check if user exists
                        existing = session.query(User).filter(
                            User.user_id == user_id
                        ).first()

                        if existing:
                            # Update
                            existing.email = email
                            existing.full_name = full_name
                            existing.first_name = first_name
                            existing.last_name = last_name
                            existing.org_unit_path = user_data.get('orgUnitPath')
                            existing.is_admin = user_data.get('isAdmin', False)
                            existing.is_suspended = user_data.get('suspended', False)
                            existing.last_login = user_data.get('lastLoginTime')

                            # NEW FIELDS: Quick Wins Phase 2 - User extended fields
                            existing.is_enrolled_in_2fa = user_data.get('isEnrolledIn2Sv', False)
                            existing.last_login_time = user_data.get('lastLoginTime')
                            existing.creation_time = user_data.get('creationTime')
                            existing.deletion_time = user_data.get('deletionTime')
                            existing.recovery_email = user_data.get('recoveryEmail')
                            existing.recovery_phone = user_data.get('recoveryPhone')
                            existing.in_global_directory = user_data.get('includeInGlobalAddressList', True)

                            # Phone number (first in list)
                            phones = user_data.get('phones', [])
                            if phones and len(phones) > 0:
                                existing.phone_number = phones[0].get('value')

                            # Organizational data (first in list)
                            orgs = user_data.get('organizations', [])
                            if orgs and len(orgs) > 0:
                                existing.job_title = orgs[0].get('title')
                                existing.department = orgs[0].get('department')
                                existing.physical_location = orgs[0].get('location')

                            # Custom schemas (student data)
                            custom_schemas = user_data.get('customSchemas', {})
                            student_data = custom_schemas.get('Student_Data', {})
                            if student_data:
                                existing.student_grade = student_data.get('Grade')
                                existing.student_id = student_data.get('Student_ID')

                            existing.updated_at = datetime.now()
                            users_updated += 1
                        else:
                            # Extract optional fields
                            phones = user_data.get('phones', [])
                            phone_number = phones[0].get('value') if phones and len(phones) > 0 else None

                            orgs = user_data.get('organizations', [])
                            job_title = orgs[0].get('title') if orgs and len(orgs) > 0 else None
                            department = orgs[0].get('department') if orgs and len(orgs) > 0 else None
                            physical_location = orgs[0].get('location') if orgs and len(orgs) > 0 else None

                            custom_schemas = user_data.get('customSchemas', {})
                            student_data = custom_schemas.get('Student_Data', {})
                            student_grade = student_data.get('Grade') if student_data else None
                            student_id = student_data.get('Student_ID') if student_data else None

                            # Create new
                            new_user = User(
                                user_id=user_id,
                                email=email,
                                full_name=full_name,
                                first_name=first_name,
                                last_name=last_name,
                                org_unit_path=user_data.get('orgUnitPath'),
                                is_admin=user_data.get('isAdmin', False),
                                is_suspended=user_data.get('suspended', False),
                                last_login=user_data.get('lastLoginTime'),
                                # NEW FIELDS: Quick Wins Phase 2
                                is_enrolled_in_2fa=user_data.get('isEnrolledIn2Sv', False),
                                last_login_time=user_data.get('lastLoginTime'),
                                creation_time=user_data.get('creationTime'),
                                deletion_time=user_data.get('deletionTime'),
                                phone_number=phone_number,
                                recovery_email=user_data.get('recoveryEmail'),
                                recovery_phone=user_data.get('recoveryPhone'),
                                in_global_directory=user_data.get('includeInGlobalAddressList', True),
                                job_title=job_title,
                                department=department,
                                physical_location=physical_location,
                                student_grade=student_grade,
                                student_id=student_id,
                                created_at=datetime.now(),
                                updated_at=datetime.now()
                            )
                            session.add(new_user)
                            users_created += 1

                        if users_processed % 100 == 0:
                            session.commit()
                            print(f"  Processed {users_processed} users...")

                    session.commit()

                print(f"  Users: {users_processed} processed, {users_created} created, {users_updated} updated")
            except Exception as e:
                print(f"  Warning: Failed to sync users: {e}")

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
            print(f"  Users: {users_processed} processed, {users_created} created, {users_updated} updated")

            return {
                'success': True,
                'assets_processed': assets_processed,
                'assets_created': assets_created,
                'assets_updated': assets_updated,
                'chromebooks_processed': chromebooks_processed,
                'chromebooks_created': chromebooks_created,
                'chromebooks_updated': chromebooks_updated,
                'users_processed': users_processed,
                'users_created': users_created,
                'users_updated': users_updated,
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

    def sync_unified_users(self) -> Dict[str, Any]:
        """
        Sync users from both Google and IIQ, merge by email, and sync fees.

        Algorithm:
        1. Fetch all Google users from database
        2. Fetch all IIQ users via pagination
        3. Match by email (case-insensitive)
        4. For each matched pair: merge with IIQ authoritative for location/role/student ID
        5. For IIQ-only users: create new records
        6. Fetch fee balances for all users
        7. Upsert to unified users table

        Returns:
            Dict with: users_processed, users_merged, users_google_only, users_iiq_only,
                      fees_fetched, duration_seconds
        """
        start_time = datetime.now()
        users_processed = 0
        users_merged = 0
        users_google_only = 0
        users_iiq_only = 0
        fees_fetched = 0

        try:
            print("\n" + "=" * 80)
            print("PHASE 2: SYNCING UNIFIED USERS (Google + IIQ)")
            print("=" * 80)

            # STEP 1: Fetch all Google users from database
            print("\nSTEP 1: Fetching Google Workspace users from database...")
            google_users_by_email = {}
            with db.get_session() as session:
                google_users = session.query(User).filter(
                    User.data_source.in_(['google', None])  # Existing users or unset
                ).all()

                for user in google_users:
                    if user.email:
                        email_lower = user.email.lower()
                        google_users_by_email[email_lower] = {
                            'user_id': user.user_id,
                            'email': user.email,
                            'full_name': user.full_name,
                            'first_name': user.first_name,
                            'last_name': user.last_name,
                            'org_unit_path': user.org_unit_path,
                            'is_admin': user.is_admin,
                            'is_suspended': user.is_suspended,
                            'student_id': user.student_id,
                            'student_grade': user.student_grade,
                            'last_login': user.last_login
                        }

                print(f"  Found {len(google_users_by_email)} Google users in database")

            # STEP 2 & 3 & 4: Fetch IIQ users via pagination and stream-process (no memory buildup)
            print("\nSTEP 2: Fetching and processing IncidentIQ users via streaming pagination...")
            page_size = 1000
            page_num = 1
            total_iiq_fetched = 0
            merged_emails = set()

            with db.get_session() as session:
                while True:
                    print(f"  Fetching page {page_num} ({page_size} users/page)...")
                    try:
                        iiq_page = self.iiq.get_users(page=page_num, page_size=page_size)
                        if not iiq_page:
                            print(f"    No more users found. Stopping pagination.")
                            break

                        total_iiq_fetched += len(iiq_page)
                        print(f"    Got {len(iiq_page)} users (cumulative: {total_iiq_fetched})")

                        # STREAM PROCESS: Match and merge each IIQ user immediately without storing all in memory
                        for iiq_user in iiq_page:
                            email = iiq_user.get('Email', '').strip()
                            if not email:
                                continue

                            email_lower = email.lower()
                            iiq_user_id = iiq_user.get('UserId', '')

                            # Extract location and role names from nested objects
                            location_obj = iiq_user.get('Location', {})
                            location_name = location_obj.get('Name', '') if isinstance(location_obj, dict) else str(location_obj)

                            role_obj = iiq_user.get('Role', {})
                            role_name = role_obj.get('Name', '') if isinstance(role_obj, dict) else str(role_obj)

                            iiq_data = {
                                'user_id': iiq_user_id,
                                'email': email,
                                'name': iiq_user.get('Name', ''),
                                'first_name': iiq_user.get('FirstName', ''),
                                'last_name': iiq_user.get('LastName', ''),
                                'location': location_name,
                                'role': role_name,
                                'student_id': iiq_user.get('SchoolIdNumber', ''),
                                'grade': iiq_user.get('Grade', ''),
                                'username': iiq_user.get('UserName', ''),
                                'is_active': iiq_user.get('IsActive', True)
                            }

                            if email_lower in google_users_by_email:
                                # MATCHED: Merge user
                                google_data = google_users_by_email[email_lower]
                                merged_emails.add(email_lower)
                                users_merged += 1

                                user = session.query(User).filter(
                                    User.user_id == google_data['user_id']
                                ).first()

                                if user:
                                    user.google_user_id = google_data['user_id']
                                    user.iiq_user_id = iiq_data['user_id']
                                    user.iiq_location = iiq_data['location']
                                    user.iiq_role_name = iiq_data['role']
                                    user.is_active_iiq = iiq_data['is_active']
                                    user.username = iiq_data['username']

                                    if iiq_data['student_id']:
                                        user.student_id = iiq_data['student_id']
                                    if iiq_data['grade']:
                                        user.student_grade = iiq_data['grade']

                                    user.data_source = 'merged'
                                    user.is_merged = True
                                    user.iiq_synced_at = datetime.now()
                                    user.google_synced_at = datetime.now()
                                    user.updated_at = datetime.now()
                            else:
                                # IIQ-ONLY: Skip for now (requires Google ID as primary key)
                                # TODO: Future phase: implement user_id generation for IIQ-only users
                                users_iiq_only += 1
                                pass

                            users_processed += 1

                        # Commit after each page to free memory
                        session.commit()
                        gc.collect()  # Force garbage collection to release memory immediately
                        print(f"    Committed page {page_num}. Memory released.")

                        if len(iiq_page) < page_size:
                            print(f"    Last page detected (got {len(iiq_page)} users < {page_size}). Done.")
                            break

                        page_num += 1
                    except Exception as e:
                        print(f"  Warning: Error fetching IIQ users page {page_num}: {e}")
                        break

                print(f"\n  Total IIQ users processed: {total_iiq_fetched}")
                print(f"  Users merged (Google + IIQ): {users_merged}")
                print(f"  IIQ-only users added: {users_iiq_only}")

                # Process remaining Google-only users
                print("\nSTEP 3: Marking Google-only users...")
                google_only_count = 0
                for email_lower, google_data in google_users_by_email.items():
                    if email_lower not in merged_emails:
                        user = session.query(User).filter(
                            User.user_id == google_data['user_id']
                        ).first()

                        if user:
                            user.google_user_id = google_data['user_id']
                            user.data_source = 'google'
                            user.is_merged = False
                            user.google_synced_at = datetime.now()
                            user.updated_at = datetime.now()
                            google_only_count += 1

                    if google_only_count % 100 == 0:
                        session.commit()

                session.commit()
                users_google_only = google_only_count
                print(f"  Marked {google_only_count} Google-only users")

            # STEP 4: Fetch fee balances for all users
            print("\nSTEP 4: Fetching fee balances from IIQ Fee Tracker...")
            users_with_fees = []

            with db.get_session() as session:
                all_iiq_users = session.query(User).filter(
                    User.iiq_user_id.isnot(None)
                ).all()

                print(f"  Fetching fees for {len(all_iiq_users)} IIQ users...")

                for idx, user in enumerate(all_iiq_users):
                    if user.iiq_user_id:
                        try:
                            # Try to fetch fee balance from cache first
                            fee_balance = self.iiq.get_user_fees(user.iiq_user_id)

                            if fee_balance is not None and fee_balance > 0:
                                user.total_fee_balance = Decimal(str(fee_balance))
                                user.has_outstanding_fees = True
                                user.fee_last_synced = datetime.now()
                                fees_fetched += 1
                                users_with_fees.append({
                                    'email': user.email,
                                    'balance': fee_balance
                                })
                        except Exception as e:
                            print(f"    Warning: Failed to fetch fees for {user.email}: {e}")

                    if (idx + 1) % 100 == 0:
                        session.commit()
                        print(f"  Processed fees for {idx + 1} users...")

                session.commit()
                gc.collect()  # Force garbage collection after fee processing
                print(f"  Fetched fees for {fees_fetched} users with outstanding balances")

            # STEP 5: Summary
            duration = int((datetime.now() - start_time).total_seconds())

            print(f"\n✓ Unified user sync complete (stream-processed, memory-efficient):")
            print(f"  Total users processed: {users_processed}")
            print(f"  Users merged (Google + IIQ): {users_merged}")
            print(f"  Google-only users: {users_google_only}")
            print(f"  IIQ-only users: {users_iiq_only}")
            print(f"  Users with fees: {fees_fetched}")
            print(f"  Duration: {duration} seconds")

            if users_with_fees:
                print(f"\n  Users with outstanding fees:")
                for uf in users_with_fees[:10]:  # Show first 10
                    print(f"    - {uf['email']}: ${uf['balance']:.2f}")
                if len(users_with_fees) > 10:
                    print(f"    ... and {len(users_with_fees) - 10} more")

            # Clear related cache
            cache.delete_pattern('user:*')
            cache.delete_pattern('search:*')

            return {
                'success': True,
                'users_processed': users_processed,
                'users_merged': users_merged,
                'users_google_only': users_google_only,
                'users_iiq_only': users_iiq_only,
                'fees_fetched': fees_fetched,
                'duration_seconds': duration
            }

        except Exception as e:
            print(f"\n✗ Unified user sync failed: {e}")
            import traceback
            traceback.print_exc()
            raise

    def sync_unified_users_fast(self, max_workers: int = 5, page_size: int = 5000, fee_workers: int = 10, max_memory_percent: float = 75.0) -> Dict[str, Any]:
        """
        Ultra-fast unified user sync with parallel page fetching and fee requests.

        MEMORY-SAFE: Pauses if RAM usage exceeds max_memory_percent.

        Trade-off: Uses more RAM to achieve maximum speed.
        - Parallel page fetching (5 pages at once by default)
        - Parallel fee fetching (10 users at once)
        - Larger page size (5000 users)
        - Bulk inserts instead of individual adds
        - Fewer, larger commits
        - MEMORY LIMITED: Won't exceed max_memory_percent (default 75%)

        Args:
            max_workers: Number of parallel page fetches (default 5)
            page_size: IIQ users per page (default 5000, was 1000)
            fee_workers: Parallel fee fetches (default 10)
            max_memory_percent: Max RAM usage % before pausing (default 75%)

        Returns:
            Dict with sync results and duration
        """
        start_time = datetime.now()
        users_processed = 0
        users_merged = 0
        users_google_only = 0
        fees_fetched = 0
        lock = threading.Lock()

        try:
            current_mem = self.get_memory_percent()
            print("\n" + "=" * 80)
            print(f"PHASE 2: FAST UNIFIED USER SYNC (Parallel Processing - Memory Safe)")
            print(f"  Current memory: {current_mem:.1f}% / {max_memory_percent}% limit")
            print(f"  Workers: {max_workers} page fetchers, {fee_workers} fee fetchers")
            print(f"  Page size: {page_size} users/page")
            print("=" * 80)

            # STEP 1: Fetch all Google users from database
            print("\nSTEP 1: Fetching Google Workspace users from database...")
            google_users_by_email = {}
            with db.get_session() as session:
                google_users = session.query(User).filter(
                    User.data_source.in_(['google', None])
                ).all()

                for user in google_users:
                    if user.email:
                        email_lower = user.email.lower()
                        google_users_by_email[email_lower] = {
                            'user_id': user.user_id,
                            'email': user.email,
                            'full_name': user.full_name,
                            'first_name': user.first_name,
                            'last_name': user.last_name,
                            'org_unit_path': user.org_unit_path,
                            'is_admin': user.is_admin,
                            'is_suspended': user.is_suspended,
                            'student_id': user.student_id,
                            'student_grade': user.student_grade,
                            'last_login': user.last_login
                        }

                print(f"  Found {len(google_users_by_email)} Google users in database")

            # STEP 2: Determine max page number (need to test first page)
            print("\nSTEP 2: Fetching IIQ users via parallel pagination...")
            first_page = self.iiq.get_users(page=1, page_size=page_size)
            print(f"  Page 1: {len(first_page)} users")

            # Estimate max pages (assume similar size for all pages)
            # We'll just fetch until we get an empty page
            all_iiq_pages = [first_page]

            # STEP 3: Parallel fetch remaining pages
            def fetch_page(page_num):
                try:
                    return self.iiq.get_users(page=page_num, page_size=page_size)
                except Exception as e:
                    print(f"    Error fetching page {page_num}: {e}")
                    return []

            page_num = 2
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {}
                pending_pages = set(range(2, 100))  # Try up to 100 pages

                while pending_pages or futures:
                    # Check memory before fetching more pages
                    if pending_pages and len(futures) < max_workers:
                        current_mem = self.get_memory_percent()
                        if current_mem > max_memory_percent:
                            self.wait_for_memory(max_memory_percent)

                    # Submit new pages up to max_workers
                    while len(futures) < max_workers and pending_pages:
                        page = min(pending_pages)
                        pending_pages.remove(page)
                        futures[executor.submit(fetch_page, page)] = page

                    # Get completed pages
                    for future in as_completed(futures.keys()):
                        page = futures.pop(future)
                        iiq_page = future.result()

                        if not iiq_page:
                            print(f"    Page {page}: Empty (end of pages)")
                            break

                        all_iiq_pages.append(iiq_page)
                        print(f"    Page {page}: {len(iiq_page)} users (total: {sum(len(p) for p in all_iiq_pages)})")

                        if len(iiq_page) < page_size:
                            # Last page
                            pending_pages.clear()
                            break

            print(f"  Total IIQ users fetched: {sum(len(p) for p in all_iiq_pages)}")

            # STEP 4: Process all users in bulk
            print("\nSTEP 3: Matching and merging users in parallel...")
            merged_emails = set()
            users_to_update = []
            all_iiq_users = []

            for page_num, iiq_page in enumerate(all_iiq_pages, 1):
                for iiq_user in iiq_page:
                    email = iiq_user.get('Email', '').strip().lower()
                    if not email:
                        continue

                    all_iiq_users.append((email, iiq_user))

                    if email in google_users_by_email:
                        merged_emails.add(email)
                        google_data = google_users_by_email[email]

                        # Extract location and role
                        location_obj = iiq_user.get('Location', {})
                        location_name = location_obj.get('Name', '') if isinstance(location_obj, dict) else str(location_obj)

                        role_obj = iiq_user.get('Role', {})
                        role_name = role_obj.get('Name', '') if isinstance(role_obj, dict) else str(role_obj)

                        users_to_update.append({
                            'user_id': google_data['user_id'],
                            'google_user_id': google_data['user_id'],
                            'iiq_user_id': iiq_user.get('UserId', ''),
                            'iiq_location': location_name,
                            'iiq_role_name': role_name,
                            'is_active_iiq': iiq_user.get('IsActive', True),
                            'username': iiq_user.get('UserName', ''),
                            'student_id': iiq_user.get('SchoolIdNumber', '') or google_data.get('student_id'),
                            'student_grade': iiq_user.get('Grade', '') or google_data.get('student_grade'),
                            'data_source': 'merged',
                            'is_merged': True,
                            'iiq_synced_at': datetime.now(),
                            'google_synced_at': datetime.now(),
                            'updated_at': datetime.now()
                        })
                        users_merged += 1
                        users_processed += 1

            # STEP 5: Bulk update merged users
            print(f"  Merging {len(users_to_update)} users...")
            with db.get_session() as session:
                for user_data in users_to_update:
                    user_id = user_data.pop('user_id')
                    user = session.query(User).filter(User.user_id == user_id).first()
                    if user:
                        for key, value in user_data.items():
                            setattr(user, key, value)

                    if users_processed % 500 == 0:
                        session.commit()
                        gc.collect()

                session.commit()
                print(f"  Updated {users_merged} users")

            # Mark Google-only users
            google_only_count = 0
            with db.get_session() as session:
                for email_lower, google_data in google_users_by_email.items():
                    if email_lower not in merged_emails:
                        user = session.query(User).filter(User.user_id == google_data['user_id']).first()
                        if user:
                            user.google_user_id = google_data['user_id']
                            user.data_source = 'google'
                            user.is_merged = False
                            user.google_synced_at = datetime.now()
                            user.updated_at = datetime.now()
                            google_only_count += 1

                session.commit()

            users_google_only = google_only_count
            print(f"  Marked {google_only_count} Google-only users")

            # STEP 6: Fetch fees in parallel (most expensive operation)
            print(f"\nSTEP 4: Fetching fee balances in parallel ({fee_workers} workers)...")
            iiq_user_ids = [email for email, _ in all_iiq_users if email in merged_emails]

            # Check memory before fetching fees
            current_mem = self.get_memory_percent()
            if current_mem > max_memory_percent:
                print(f"  Checking memory before fee fetch...")
                self.wait_for_memory(max_memory_percent)

            def fetch_fees(iiq_user_id):
                try:
                    return (iiq_user_id, self.iiq.get_user_fees(iiq_user_id))
                except Exception as e:
                    return (iiq_user_id, None)

            fees_dict = {}
            with ThreadPoolExecutor(max_workers=fee_workers) as executor:
                futures = {executor.submit(fetch_fees, uid): uid for uid in iiq_user_ids}
                completed = 0
                for future in as_completed(futures):
                    iiq_user_id, fee_info = future.result()
                    if fee_info and fee_info.get('total_balance', 0) > 0:
                        fees_dict[iiq_user_id] = fee_info
                        fees_fetched += 1

                    completed += 1
                    if completed % 100 == 0:
                        print(f"  Fetched fees for {completed}/{len(iiq_user_ids)} users...")

            # STEP 7: Update fees in database
            if fees_dict:
                with db.get_session() as session:
                    for iiq_user_id, fee_info in fees_dict.items():
                        user = session.query(User).filter(User.iiq_user_id == iiq_user_id).first()
                        if user:
                            user.total_fee_balance = Decimal(str(fee_info.get('total_balance', 0)))
                            user.has_outstanding_fees = True
                            user.fee_last_synced = datetime.now()

                    session.commit()
                    gc.collect()

            # Summary
            duration = int((datetime.now() - start_time).total_seconds())

            print(f"\n✓ Fast unified user sync complete (took {duration}s):")
            print(f"  Total users processed: {users_processed}")
            print(f"  Users merged (Google + IIQ): {users_merged}")
            print(f"  Google-only users: {users_google_only}")
            print(f"  Users with fees: {fees_fetched}")
            print(f"  Duration: {duration} seconds")

            # Clear cache
            cache.delete_pattern('user:*')
            cache.delete_pattern('search:*')

            return {
                'success': True,
                'users_processed': users_processed,
                'users_merged': users_merged,
                'users_google_only': users_google_only,
                'fees_fetched': fees_fetched,
                'duration_seconds': duration,
                'method': 'fast_parallel'
            }

        except Exception as e:
            print(f"\n✗ Fast sync failed: {e}")
            import traceback
            traceback.print_exc()
            raise


if __name__ == "__main__":
    """Run sync when module is executed directly"""
    import os
    # Import the API clients we need
    from integrations.google_admin import GoogleAdminClient
    from integrations.incidentiq import IncidentIQClient
    from integrations.meraki import MerakiClient

    print("Starting Chromebook Sync Service...")
    print("=" * 80)

    # Initialize API clients
    google_client = GoogleAdminClient(
        customer_id=os.getenv('GOOGLE_CUSTOMER_ID', 'my_customer'),
        credentials_file=os.getenv('GOOGLE_CREDENTIALS_FILE', '/opt/chromebook-dashboard/credentials.json')
    )

    iiq_client = IncidentIQClient(
        site_id=os.getenv('INCIDENTIQ_SITE_ID'),
        api_token=os.getenv('INCIDENTIQ_API_TOKEN'),
        product_id=os.getenv('INCIDENTIQ_PRODUCT_ID', '88df910c-91aa-e711-80c2-0004ffa00050')
    )

    meraki_client = MerakiClient(
        api_key=os.getenv('MERAKI_API_KEY'),
        org_id=os.getenv('MERAKI_ORG_ID')
    )

    # Optional: Telemetry client
    telemetry_client = None
    try:
        telemetry_client = ChromeTelemetryClient(
            customer_id=os.getenv('GOOGLE_CUSTOMER_ID', 'my_customer'),
            credentials_file=os.getenv('GOOGLE_CREDENTIALS_FILE', '/opt/chromebook-dashboard/credentials.json')
        )
        print("✓ Telemetry client initialized")
    except Exception as e:
        print(f"⚠ Telemetry client not available: {e}")

    # Create sync service and run
    sync_service = SimpleSyncService(
        google_api=google_client,
        iiq_api=iiq_client,
        meraki_api=meraki_client,
        telemetry_api=telemetry_client
    )

    print("\nRunning sync...")
    result = sync_service.sync_chromebooks()

    if result.get('success'):
        print("\n" + "=" * 80)
        print("SYNC COMPLETED SUCCESSFULLY")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("SYNC FAILED")
        print("=" * 80)
