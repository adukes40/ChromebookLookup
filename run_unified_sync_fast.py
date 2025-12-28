#!/usr/bin/env python3
"""
Run FAST unified user sync with parallel page/fee fetching
Usage: python3 run_unified_sync_fast.py [--workers 5] [--fee-workers 10] [--page-size 5000]
"""
import os
import sys

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

def run_fast_sync(max_workers=5, page_size=5000, fee_workers=10):
    """Run the fast parallel sync"""
    print("=" * 80)
    print("FAST UNIFIED USER SYNC - PARALLEL PROCESSING")
    print("=" * 80)
    print(f"\nConfiguration:")
    print(f"  Page fetcher workers: {max_workers}")
    print(f"  Fee fetcher workers: {fee_workers}")
    print(f"  Page size: {page_size} users/page")
    print(f"\nThis trades memory for speed - maximum parallelism!")

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

        # Run fast sync
        result = sync_service.sync_unified_users_fast(
            max_workers=max_workers,
            page_size=page_size,
            fee_workers=fee_workers
        )

        if result.get('success'):
            print(f"\n{'='*80}")
            print(f"✓ SYNC COMPLETED SUCCESSFULLY")
            print(f"{'='*80}")
            print(f"\nResults:")
            print(f"  Method: {result['method']}")
            print(f"  Duration: {result['duration_seconds']}s")
            print(f"  Users processed: {result['users_processed']}")
            print(f"  Merged: {result['users_merged']}")
            print(f"  Google-only: {result['users_google_only']}")
            print(f"  Fees fetched: {result['fees_fetched']}")
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
    import argparse

    parser = argparse.ArgumentParser(description='Fast unified user sync with parallel processing')
    parser.add_argument('--workers', type=int, default=5, help='Page fetcher workers (default 5)')
    parser.add_argument('--fee-workers', type=int, default=10, help='Fee fetcher workers (default 10)')
    parser.add_argument('--page-size', type=int, default=5000, help='Users per page (default 5000)')

    args = parser.parse_args()

    sys.exit(run_fast_sync(
        max_workers=args.workers,
        page_size=args.page_size,
        fee_workers=args.fee_workers
    ))
