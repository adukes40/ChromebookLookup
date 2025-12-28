#!/usr/bin/env python3
"""
Run unified user sync with memory monitoring
Usage: python3 run_unified_sync.py
"""
import os
import sys
import psutil
import subprocess

# Add project root to path
sys.path.insert(0, '/opt/chromebook-dashboard')

# Load environment variables
from dotenv import load_dotenv
load_dotenv('/opt/chromebook-dashboard/.env')

# Import sync service
from services.sync_service_simple import SimpleSyncService
from integrations.google import GoogleWorkspaceClient
from integrations.incidentiq import IncidentIQClient
from integrations.meraki import MerakiClient

def get_memory_usage():
    """Get current process and system memory info"""
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    return mem_info.rss / 1024 / 1024  # Convert to MB

def monitor_sync():
    """Run sync with memory monitoring"""
    print("=" * 80)
    print("UNIFIED USER SYNC - STREAM-PROCESSED (MEMORY-EFFICIENT)")
    print("=" * 80)
    print(f"\nStarting memory: {get_memory_usage():.1f} MB")

    try:
        # Initialize API clients
        google_client = GoogleWorkspaceClient(
            credentials_file=os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', '/opt/chromebook-dashboard/credentials.json'),
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

        # Create sync service
        sync_service = SimpleSyncService(
            google_api=google_client,
            iiq_api=iiq_client,
            meraki_api=meraki_client
        )

        print(f"Starting unified user sync...\n")
        print(f"Memory before sync: {get_memory_usage():.1f} MB")
        print("-" * 80)

        # Run sync
        result = sync_service.sync_unified_users()

        print("-" * 80)
        print(f"Memory after sync: {get_memory_usage():.1f} MB")

        if result.get('success'):
            print(f"\n✓ SYNC COMPLETED SUCCESSFULLY")
            print(f"\n  Summary:")
            print(f"    Users processed: {result['users_processed']}")
            print(f"    Merged (Google + IIQ): {result['users_merged']}")
            print(f"    Google-only: {result['users_google_only']}")
            print(f"    IIQ-only: {result['users_iiq_only']}")
            print(f"    Fees fetched: {result['fees_fetched']}")
            print(f"    Duration: {result['duration_seconds']}s")
            return 0
        else:
            print(f"\n✗ SYNC FAILED")
            return 1

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(monitor_sync())
