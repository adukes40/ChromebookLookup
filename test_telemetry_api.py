#!/usr/bin/env python3
"""
Test script for Chrome Management Telemetry API
Tests battery data retrieval
"""
import sys
import os
sys.path.insert(0, '/opt/chromebook-dashboard')

from integrations.google_telemetry import ChromeTelemetryClient
import json

# Configuration
CREDENTIALS_FILE = '/opt/chromebook-dashboard/credentials.json'
ADMIN_EMAIL = 'gsync@cr.k12.de.us'

def test_telemetry_api():
    """Test Chrome Management Telemetry API"""

    print("=" * 80)
    print("Testing Chrome Management Telemetry API for Battery Data")
    print("=" * 80)
    print()

    try:
        # Initialize client
        print("Initializing Chrome Telemetry client...")
        client = ChromeTelemetryClient(CREDENTIALS_FILE, ADMIN_EMAIL)
        print("✓ Client initialized\n")

        # Test 1: List a few devices
        print("TEST 1: Fetching telemetry for first 5 devices...")
        print("-" * 80)
        devices = client.list_device_telemetry(page_size=5, max_results=5)

        if not devices:
            print("✗ No devices found")
            return

        print(f"✓ Retrieved {len(devices)} devices\n")

        # Test 2: Check what fields are returned
        print("TEST 2: Examining telemetry data structure...")
        print("-" * 80)
        first_device = devices[0]

        print("Fields available in telemetry response:")
        for key in sorted(first_device.keys()):
            print(f"  - {key}")
        print()

        # Test 3: Extract battery info
        print("TEST 3: Extracting battery information...")
        print("-" * 80)

        for i, device in enumerate(devices, 1):
            battery_data = client.extract_battery_info(device)

            print(f"\nDevice {i}:")
            print(f"  Serial: {battery_data['serial_number']}")
            print(f"  Device ID: {battery_data['device_id']}")
            print(f"  Battery Health: {battery_data['battery_health']}%")
            print(f"  Full Charge Capacity: {battery_data['battery_full_charge_capacity']} mAh")
            print(f"  Design Capacity: {battery_data['battery_design_capacity']} mAh")
            print(f"  Manufacturer: {battery_data['battery_manufacturer']}")
            print(f"  Report Time: {battery_data['battery_report_time']}")

        # Save full response for inspection
        print()
        print("=" * 80)
        output_file = '/tmp/telemetry_response.json'
        with open(output_file, 'w') as f:
            json.dump(devices, f, indent=2, default=str)

        print(f"Full telemetry response saved to: {output_file}")
        print("=" * 80)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_telemetry_api()
