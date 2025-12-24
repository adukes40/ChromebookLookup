#!/usr/bin/env python3
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import everything from main
from main import (
    get_google_service,
    INCIDENTIQ_SITE_ID,
    INCIDENTIQ_API_TOKEN,
    INCIDENTIQ_PRODUCT_ID,
    MERAKI_API_KEY,
    MERAKI_ORG_ID
)
from services.sync_service_simple import SimpleSyncService
from integrations.incidentiq import IncidentIQClient
from integrations.meraki import MerakiClient

if __name__ == '__main__':
    print("Starting Chromebook sync...")
    
    # Initialize clients
    google_service = get_google_service()
    iiq_client = IncidentIQClient(
        site_id=INCIDENTIQ_SITE_ID,
        api_token=INCIDENTIQ_API_TOKEN,
        product_id=INCIDENTIQ_PRODUCT_ID
    )
    meraki_client = MerakiClient(
        api_key=MERAKI_API_KEY,
        org_id=MERAKI_ORG_ID
    ) if MERAKI_API_KEY and MERAKI_ORG_ID else None
    
    # Run sync
    sync_service = SimpleSyncService(google_service, iiq_client, meraki_client)
    result = sync_service.sync_chromebooks()
    
    print(f"\n✓ Sync completed!")
    print(f"  Processed: {result.get('processed', 0)}")
    print(f"  Created: {result.get('created', 0)}")
    print(f"  Updated: {result.get('updated', 0)}")
