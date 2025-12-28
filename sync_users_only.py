#!/usr/bin/env python3
"""Quick unified user sync - Google + IIQ merge with fees"""
import os
import sys

sys.path.insert(0, '/opt/chromebook-dashboard')

from dotenv import load_dotenv
load_dotenv('/opt/chromebook-dashboard/.env')

from services.sync_service_simple import SimpleSyncService
from integrations.google import GoogleWorkspaceClient
from integrations.incidentiq import IncidentIQClient
from integrations.meraki import MerakiClient

print("\n" + "=" * 80)
print("UNIFIED USER SYNC - Google + IIQ + Fees")
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

# Create sync service
sync_service = SimpleSyncService(
    google_api=google_client,
    iiq_api=iiq_client,
    meraki_api=meraki_client
)

# Run unified user sync only
try:
    result = sync_service.sync_unified_users()

    if result.get('success'):
        print("\n" + "=" * 80)
        print("USER SYNC COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print(f"\n✓ Summary:")
        print(f"  Total processed: {result.get('users_processed')}")
        print(f"  Merged (Google + IIQ): {result.get('users_merged')}")
        print(f"  Google-only: {result.get('users_google_only')}")
        print(f"  IIQ-only: {result.get('users_iiq_only')}")
        print(f"  Fees fetched: {result.get('fees_fetched')}")
        print(f"  Duration: {result.get('duration_seconds')}s")
    else:
        print("\n✗ USER SYNC FAILED")

except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
