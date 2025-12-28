#!/usr/bin/env python3
"""
Test script to check what fields Google Admin SDK returns for ChromeOS devices
Specifically looking for battery-related fields
"""
import sys
import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Configuration
CREDENTIALS_FILE = '/opt/chromebook-dashboard/credentials.json'
ADMIN_EMAIL = 'gsync@cr.k12.de.us'
SCOPES = [
    'https://www.googleapis.com/auth/admin.directory.device.chromeos.readonly',
]

def test_google_api_fields():
    """Test what fields are returned by Google Admin SDK"""

    print("Initializing Google Admin SDK...")
    try:
        # Load credentials
        credentials = service_account.Credentials.from_service_account_file(
            CREDENTIALS_FILE,
            scopes=SCOPES
        )

        # Delegate to admin user
        delegated_credentials = credentials.with_subject(ADMIN_EMAIL)

        # Build service
        service = build('admin', 'directory_v1', credentials=delegated_credentials)

        print(f"✓ Connected as {ADMIN_EMAIL}\n")

        # Fetch ONE device with FULL projection to see all available fields
        print("Fetching one device with projection='FULL'...")
        result = service.chromeosdevices().list(
            customerId='my_customer',
            maxResults=1,
            projection='FULL'
        ).execute()

        devices = result.get('chromeosdevices', [])

        if not devices:
            print("✗ No devices found")
            return

        device = devices[0]

        print(f"✓ Retrieved device: {device.get('serialNumber', 'Unknown')}\n")

        # List ALL fields returned
        print("=" * 80)
        print("ALL FIELDS RETURNED BY GOOGLE ADMIN SDK:")
        print("=" * 80)
        for key in sorted(device.keys()):
            print(f"  {key}")
        print()

        # Check for battery-related fields
        print("=" * 80)
        print("SEARCHING FOR BATTERY-RELATED FIELDS:")
        print("=" * 80)
        battery_keywords = ['battery', 'power', 'charge', 'energy']
        found_battery_fields = []

        for key in device.keys():
            if any(keyword in key.lower() for keyword in battery_keywords):
                found_battery_fields.append(key)
                print(f"  ✓ FOUND: {key}")
                print(f"    Value: {device[key]}")
                print()

        if not found_battery_fields:
            print("  ✗ NO battery-related fields found in API response")
            print()

        # Save full device response to file for inspection
        output_file = '/tmp/google_device_response.json'
        with open(output_file, 'w') as f:
            json.dump(device, f, indent=2, default=str)

        print("=" * 80)
        print(f"Full device response saved to: {output_file}")
        print("=" * 80)

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_google_api_fields()
