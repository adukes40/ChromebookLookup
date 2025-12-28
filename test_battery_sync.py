#!/usr/bin/env python3
"""
Test battery data sync with a few devices
"""
import sys
import os
sys.path.insert(0, '/opt/chromebook-dashboard')

from integrations.google import GoogleWorkspaceClient
from integrations.google_telemetry import ChromeTelemetryClient
from database.connection import db
from database.models import Chromebook

CREDENTIALS_FILE = '/opt/chromebook-dashboard/credentials.json'
ADMIN_EMAIL = 'gsync@cr.k12.de.us'

def test_battery_sync():
    """Test battery data integration with database"""

    print("=" * 80)
    print("Testing Battery Data Sync")
    print("=" * 80)
    print()

    # Initialize clients
    print("Initializing clients...")
    google = GoogleWorkspaceClient(CREDENTIALS_FILE, ADMIN_EMAIL)
    telemetry = ChromeTelemetryClient(CREDENTIALS_FILE, ADMIN_EMAIL)
    print("✓ Clients initialized\n")

    # Fetch first 3 Google devices
    print("Fetching 3 devices from Google Admin...")
    devices = google.get_chromebooks(max_results=3)
    print(f"✓ Retrieved {len(devices)} devices\n")

    # Fetch battery telemetry for first 3 devices
    print("Fetching battery telemetry...")
    telemetry_devices = telemetry.list_device_telemetry(page_size=3, max_results=3)
    print(f"✓ Retrieved telemetry for {len(telemetry_devices)} devices\n")

    # Create battery lookup
    battery_lookup = {}
    for telem in telemetry_devices:
        device_id = telem.get('deviceId')
        if device_id:
            battery_info = telemetry.extract_battery_info(telem)
            battery_lookup[device_id] = battery_info

    print(f"Battery data available for {len(battery_lookup)} devices\n")

    # Update database
    print("Updating database with battery data...")
    print("-" * 80)

    with db.get_session() as session:
        for device in devices:
            device_id = device.get('deviceId')
            serial = device.get('serialNumber')

            if not device_id:
                continue

            # Find device in database
            db_device = session.query(Chromebook).filter(
                Chromebook.device_id == device_id
            ).first()

            if not db_device:
                print(f"  Device {serial} not in database (skipping)")
                continue

            # Update battery data if available
            if device_id in battery_lookup:
                battery = battery_lookup[device_id]

                print(f"\n  Device: {serial}")
                print(f"    Battery Health: {battery.get('battery_health')}%")
                print(f"    Cycle Count: {battery.get('battery_cycle_count')}")
                print(f"    Full Charge Capacity: {battery.get('battery_full_charge_capacity')} mAh")
                print(f"    Design Capacity: {battery.get('battery_design_capacity')} mAh")
                print(f"    Manufacturer: {battery.get('battery_manufacturer')}")

                # Update fields
                db_device.battery_health = battery.get('battery_health')
                db_device.battery_cycle_count = battery.get('battery_cycle_count')
                db_device.battery_full_charge_capacity = battery.get('battery_full_charge_capacity')
                db_device.battery_design_capacity = battery.get('battery_design_capacity')
                db_device.battery_manufacturer = battery.get('battery_manufacturer')

                # Convert report time
                report_time_str = battery.get('battery_report_time')
                if report_time_str:
                    from datetime import datetime
                    try:
                        dt = datetime.fromisoformat(report_time_str.replace('Z', '+00:00'))
                        db_device.battery_report_time = int(dt.timestamp())
                        print(f"    Report Time: {report_time_str}")
                    except:
                        pass

                print("    ✓ Updated in database")
            else:
                print(f"\n  Device: {serial} - No battery data available")

        session.commit()

    print("\n" + "=" * 80)
    print("✓ Battery sync test complete!")
    print("=" * 80)

    # Verify data was stored
    print("\nVerifying data in database...")
    with db.get_session() as session:
        devices_with_battery = session.query(Chromebook).filter(
            Chromebook.battery_health.isnot(None)
        ).limit(5).all()

        print(f"\nDevices with battery data: {len(devices_with_battery)}")
        for dev in devices_with_battery:
            print(f"  {dev.serial_number}: {dev.battery_health}% health, {dev.battery_cycle_count} cycles")

if __name__ == '__main__':
    test_battery_sync()
