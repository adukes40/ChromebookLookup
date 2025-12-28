"""
Database models for caching Chromebook, User, and Meraki data
Designed for PostgreSQL with SQLAlchemy
"""
from sqlalchemy import Column, String, DateTime, Integer, BigInteger, Text, Boolean, JSON, Numeric
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class Chromebook(Base):
    """Cached chromebook data from Google Admin + IncidentIQ"""
    __tablename__ = 'chromebooks'
    
    # Primary identifiers
    device_id = Column(String(255), primary_key=True)  # Google device ID
    serial_number = Column(String(100), unique=True, index=True)
    mac_address = Column(String(255))
    ethernet_mac = Column(String(255))
    ip_address = Column(String(100))
    wan_ip_address = Column(String(100))
    aue_date = Column(String(20))
    aue_timestamp = Column(BigInteger)

    # Quick Wins Phase 2: Device lifecycle & extended fields
    auto_update_expiration = Column(String(20))  # YYYY-MM-DD format from autoUpdateThrough
    support_end_date = Column(String(20))
    boot_mode = Column(String(50))  # Verified, Dev, etc.
    device_license_type = Column(String(100))
    extended_support_enabled = Column(Boolean, default=False)
    extended_support_eligible = Column(Boolean, default=False)
    manufacture_date = Column(String(20))
    first_enrollment_time = Column(String(50))
    deprovision_reason = Column(String(255))
    last_known_network_name = Column(String(255))
    last_known_network_ssid = Column(String(255))
    os_update_state = Column(String(50))
    os_target_version = Column(String(100))

    # Battery health data
    battery_health = Column(Integer)  # Percentage (0-100)
    battery_cycle_count = Column(Integer)
    battery_full_charge_capacity = Column(Integer)
    battery_design_capacity = Column(Integer)
    battery_manufacturer = Column(String(100))
    battery_report_time = Column(BigInteger)
    os_version = Column(String(100))
    platform_version = Column(String(255))
    firmware_version = Column(String(255))
    last_used_date = Column(DateTime)
    asset_tag = Column(String(100), unique=True, index=True, nullable=True)
    
    # Device info
    model = Column(String(255))
    status = Column(String(50))  # ACTIVE, DEPROVISIONED, etc.
    annotated_user = Column(String(255), index=True)  # Email
    annotated_location = Column(String(255))
    annotated_asset_id = Column(String(100))
    org_unit_path = Column(String(500))
    
    # Last sync info
    last_sync_status = Column(String(50))
    last_policy_sync_time = Column(DateTime)
    recent_users = Column(JSON)  # List of recent user emails
    
    # IncidentIQ data
    iiq_asset_id = Column(String(100), index=True)
    iiq_location = Column(String(255))
    iiq_room = Column(String(100))
    iiq_notes = Column(Text)
    iiq_owner_email = Column(String(255), index=True)  # Official assigned user from IIQ
    iiq_owner_name = Column(String(255))  # Full name of assigned user from IIQ
    iiq_status = Column(String(100), index=True)  # Asset status (In Use, In Repair, etc.)

    # Meraki data (populated separately)
    last_seen_meraki = Column(DateTime, nullable=True)
    meraki_ap_name = Column(String(255), nullable=True)
    meraki_network = Column(String(255), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    data_source = Column(String(50))  # 'google_admin', 'incidentiq', 'merged'
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'device_id': self.device_id,
            'serial_number': self.serial_number,
            'asset_tag': self.asset_tag,
            'model': self.model,
            'status': self.status,
            'user': self.annotated_user,
            'location': self.annotated_location,
            'org_unit_path': self.org_unit_path,
            'last_sync': self.last_sync_status,
            'last_policy_sync_time': self.last_policy_sync_time.isoformat() if self.last_policy_sync_time else None,
            'recent_users': self.recent_users,
            'iiq_asset_id': self.iiq_asset_id,
            'iiq_location': self.iiq_location,
            'iiq_room': self.iiq_room,
            'iiq_owner_email': self.iiq_owner_email,
            'iiq_owner_name': self.iiq_owner_name,
            'iiq_status': self.iiq_status,
            'notes': self.iiq_notes,
            'meraki': {
                'last_seen': self.last_seen_meraki.isoformat() if self.last_seen_meraki else None,
                'ap_name': self.meraki_ap_name,
                'network': self.meraki_network
            } if self.last_seen_meraki else None,
            'mac_address': self.mac_address,
            'ethernet_mac': self.ethernet_mac,
            'ip_address': self.ip_address,
            'os_version': self.os_version,
            'platform_version': self.platform_version,
            'firmware_version': self.firmware_version,
            'wan_ip_address': self.wan_ip_address,
            'last_used_date': self.last_used_date.isoformat() if self.last_used_date else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'battery_health': self.battery_health,
            'battery_cycle_count': self.battery_cycle_count
        }


class User(Base):
    """Cached user data from Google Admin"""
    __tablename__ = 'users'
    
    # Primary identifiers
    user_id = Column(String(255), primary_key=True)  # Google user ID
    email = Column(String(255), unique=True, index=True)
    
    # User info
    full_name = Column(String(255))
    first_name = Column(String(100))
    last_name = Column(String(100))
    org_unit_path = Column(String(500))
    is_admin = Column(Boolean, default=False)
    is_suspended = Column(Boolean, default=False)
    
    # Device assignments (JSON array of device IDs)
    assigned_devices = Column(JSON)  # List of device_ids
    device_count = Column(Integer, default=0)

    # Student data (from Google customSchemas.Student_Data or IIQ Owner.StudentId)
    student_id = Column(String(50), index=True)
    student_grade = Column(String(20))

    # Data source tracking (Unified User Management)
    google_user_id = Column(String(255), index=True, nullable=True)  # From Google
    iiq_user_id = Column(String(255), index=True, nullable=True)  # From IIQ
    google_synced_at = Column(DateTime, nullable=True)
    iiq_synced_at = Column(DateTime, nullable=True)

    # Fee Tracker integration
    total_fee_balance = Column(Numeric(10, 2), default=0.00)  # Dollar amount
    fee_last_synced = Column(DateTime, nullable=True)
    has_outstanding_fees = Column(Boolean, default=False, index=True)

    # IIQ-specific fields
    iiq_location = Column(String(255))
    iiq_role_name = Column(String(100))  # Student, Teacher, Staff, etc.
    is_active_iiq = Column(Boolean, default=True)
    username = Column(String(255), index=True, nullable=True)  # IIQ username

    # Merge metadata
    data_source = Column(String(50))  # 'google', 'iiq', 'merged'
    is_merged = Column(Boolean, default=False)

    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_login = Column(DateTime, nullable=True)
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'user_id': self.user_id,
            'email': self.email,
            'name': self.full_name,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'org_unit': self.org_unit_path,
            'is_admin': self.is_admin,
            'is_suspended': self.is_suspended,
            'assigned_devices': self.assigned_devices or [],
            'device_count': self.device_count,
            'student_id': self.student_id,
            'student_grade': self.student_grade,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            # Unified user management fields
            'google_user_id': self.google_user_id,
            'iiq_user_id': self.iiq_user_id,
            'google_synced_at': self.google_synced_at.isoformat() if self.google_synced_at else None,
            'iiq_synced_at': self.iiq_synced_at.isoformat() if self.iiq_synced_at else None,
            # Fee Tracker fields
            'total_fee_balance': float(self.total_fee_balance) if self.total_fee_balance else 0.0,
            'has_outstanding_fees': self.has_outstanding_fees,
            'fee_last_synced': self.fee_last_synced.isoformat() if self.fee_last_synced else None,
            # IIQ fields
            'iiq_location': self.iiq_location,
            'iiq_role_name': self.iiq_role_name,
            'is_active_iiq': self.is_active_iiq,
            'username': self.username,
            # Metadata
            'data_source': self.data_source,
            'is_merged': self.is_merged,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Asset(Base):
    """Cached IIQ asset data for all device types"""
    __tablename__ = 'assets'

    # Primary identifiers (from IIQ)
    asset_id = Column(String(100), primary_key=True)  # IIQ AssetID
    asset_tag = Column(String(100), unique=True, index=True)
    serial_number = Column(String(100), index=True)

    # Device info (from IIQ)
    device_type = Column(String(100), index=True)  # Category name: "Chromebooks", "iPads", etc.
    model = Column(String(255))
    status = Column(String(100))  # IIQ status: "In Use", "In Repair", etc.

    # Assignment (from IIQ)
    owner_email = Column(String(255), index=True)
    owner_name = Column(String(255))
    owner_student_id = Column(String(50), index=True)  # Student ID from IIQ Owner.SchoolIdNumber
    owner_student_grade = Column(String(20))  # Student grade from IIQ Owner.Grade
    location = Column(String(255))
    room = Column(String(100))

    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_synced = Column(DateTime)  # When we last fetched from IIQ

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'assetId': self.asset_id,
            'assetTag': self.asset_tag,
            'serialNumber': self.serial_number,
            'deviceType': self.device_type,
            'model': self.model,
            'status': self.status,
            'ownerEmail': self.owner_email,
            'ownerName': self.owner_name,
            'location': self.location,
            'room': self.room,
            'lastSynced': self.last_synced.isoformat() if self.last_synced else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None
        }


class MerakiClient(Base):
    """Cached Meraki client/device location data"""
    __tablename__ = 'meraki_clients'
    
    # Primary identifiers
    mac_address = Column(String(17), primary_key=True)  # MAC address
    serial_number = Column(String(100), index=True, nullable=True)  # If we can match to chromebook
    
    # Location info
    network_id = Column(String(100))
    network_name = Column(String(255))
    ap_name = Column(String(255))
    ap_mac = Column(String(17))
    
    # Connection details
    ip_address = Column(String(45))
    vlan = Column(Integer, nullable=True)
    description = Column(String(255), nullable=True)
    
    # Timestamps
    first_seen = Column(DateTime)
    last_seen = Column(DateTime, index=True)
    
    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'mac_address': self.mac_address,
            'serial_number': self.serial_number,
            'network': self.network_name,
            'ap_name': self.ap_name,
            'ip_address': self.ip_address,
            'vlan': self.vlan,
            'first_seen': self.first_seen.isoformat() if self.first_seen else None,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class SyncLog(Base):
    """Track sync operations for monitoring"""
    __tablename__ = 'sync_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sync_type = Column(String(50), index=True)  # 'chromebooks', 'users', 'meraki', 'full'
    status = Column(String(20))  # 'started', 'completed', 'failed'
    records_processed = Column(Integer, default=0)
    records_created = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    duration_seconds = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'sync_type': self.sync_type,
            'status': self.status,
            'records_processed': self.records_processed,
            'records_created': self.records_created,
            'records_updated': self.records_updated,
            'duration_seconds': self.duration_seconds,
            'error_message': self.error_message,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

# Note: aue_date field should be added to Chromebook model
# Updating the to_dict() method to include it
