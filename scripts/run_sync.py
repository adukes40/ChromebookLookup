#!/usr/bin/env python3
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv('/opt/chromebook-dashboard/.env')

from integrations.google import GoogleWorkspaceClient
from integrations.incidentiq import IncidentIQClient
from integrations.meraki import MerakiClient
from integrations.google_telemetry import ChromeTelemetryClient
from services.sync_service_simple import SimpleSyncService
from database.connection import db

def main():
    print("=" * 60)
    print("Chromebook Dashboard - Data Sync")
    print("=" * 60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    try:
        print("Initializing API clients...")
        
        # Get credentials from environment
        credentials_file = '/opt/chromebook-dashboard/credentials.json'
        admin_email = os.getenv('GOOGLE_ADMIN_EMAIL')
        iiq_site_id = os.getenv('IIQ_SITE_ID')
        iiq_token = os.getenv('IIQ_API_TOKEN')
        meraki_key = os.getenv('MERAKI_API_KEY')
        meraki_org = os.getenv('MERAKI_ORG_ID')
        
        google = GoogleWorkspaceClient(credentials_file, admin_email)
        iiq = IncidentIQClient(iiq_site_id, iiq_token)
        meraki = MerakiClient(meraki_key, meraki_org)
        telemetry = ChromeTelemetryClient(credentials_file, admin_email)
        print("✓ API clients initialized\n")

        sync = SimpleSyncService(google, iiq, meraki, telemetry)
        result = sync.sync_chromebooks()
        
        print("\n" + "=" * 60)
        if result.get('success'):
            print("✓ Sync completed successfully!")
            print("=" * 60)
            print(f"Duration: {result['duration_seconds']} seconds")
            print(f"\nAssets (IIQ):")
            print(f"  Processed: {result['assets_processed']}")
            print(f"  Created: {result['assets_created']}")
            print(f"  Updated: {result['assets_updated']}")
            print(f"\nChromebooks (Google):")
            print(f"  Processed: {result['chromebooks_processed']}")
            print(f"  Created: {result['chromebooks_created']}")
            print(f"  Updated: {result['chromebooks_updated']}")
            print(f"\nUsers (Google Workspace):")
            print(f"  Processed: {result.get('users_processed', 0)}")
            print(f"  Created: {result.get('users_created', 0)}")
            print(f"  Updated: {result.get('users_updated', 0)}")
        else:
            print("✗ Sync failed!")
            print(f"Error: {result.get('error')}")
        print()
        
    except Exception as e:
        print(f"\n✗ Sync error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
