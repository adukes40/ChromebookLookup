#!/usr/bin/env python3
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import everything from main
from main import (
    SERVICE_ACCOUNT_FILE,
    DELEGATED_ADMIN_EMAIL,
    INCIDENTIQ_SITE_ID,
    INCIDENTIQ_API_TOKEN,
    INCIDENTIQ_PRODUCT_ID,
    MERAKI_API_KEY,
    MERAKI_ORG_ID
)
from services.sync_service_simple import SimpleSyncService
from integrations.incidentiq import IncidentIQClient
from integrations.meraki import MerakiClient
from integrations.google import GoogleWorkspaceClient
from integrations.google_telemetry import ChromeTelemetryClient

if __name__ == '__main__':
    print("Starting Chromebook sync...")

    # Initialize clients
    google_client = GoogleWorkspaceClient(
        credentials_file=SERVICE_ACCOUNT_FILE,
        admin_email=DELEGATED_ADMIN_EMAIL
    )
    iiq_client = IncidentIQClient(
        site_id=INCIDENTIQ_SITE_ID,
        api_token=INCIDENTIQ_API_TOKEN,
        product_id=INCIDENTIQ_PRODUCT_ID
    )
    meraki_client = MerakiClient(
        api_key=MERAKI_API_KEY,
        org_id=MERAKI_ORG_ID
    ) if MERAKI_API_KEY and MERAKI_ORG_ID else None

    # Initialize telemetry client if credentials available
    telemetry_client = None
    try:
        telemetry_client = ChromeTelemetryClient(
            credentials_file=SERVICE_ACCOUNT_FILE,
            admin_email=DELEGATED_ADMIN_EMAIL
        )
        print("  ✓ Telemetry client initialized")
    except Exception as e:
        print(f"  ⚠️  Telemetry client not available: {e}")

    # Run sync
    sync_service = SimpleSyncService(google_client, iiq_client, meraki_client, telemetry_client)
    result = sync_service.sync_chromebooks()
    
    print(f"\n✓ Sync completed!")
    print(f"  Processed: {result.get('processed', 0)}")
    print(f"  Created: {result.get('created', 0)}")
    print(f"  Updated: {result.get('updated', 0)}")
