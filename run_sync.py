#!/usr/bin/env python3
"""Standalone script to run the IIQ sync"""
import os
import sys

# Add project root to path
sys.path.insert(0, '/opt/chromebook-dashboard')

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv('/opt/chromebook-dashboard/.env')

# Now import and run the sync
from services.sync_service_simple import SimpleSyncService
from integrations.google import GoogleWorkspaceClient
from integrations.incidentiq import IncidentIQClient
from integrations.meraki import MerakiClient
from integrations.google_telemetry import ChromeTelemetryClient

print("Starting Chromebook Sync Service...")
print("=" * 80)

# Initialize API clients
google_client = GoogleWorkspaceClient(
    credentials_file=os.getenv('GOOGLE_CREDENTIALS_FILE', '/opt/chromebook-dashboard/credentials.json'),
    admin_email=os.getenv('GOOGLE_ADMIN_EMAIL', 'gsync@cr.k12.de.us')
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
        credentials_file=os.getenv('GOOGLE_CREDENTIALS_FILE', '/opt/chromebook-dashboard/credentials.json'),
        admin_email=os.getenv('GOOGLE_ADMIN_EMAIL', 'gsync@cr.k12.de.us')
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
