#!/usr/bin/env python3
"""Test script for unified user sync (Google + IIQ matching)"""
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, '/opt/chromebook-dashboard')

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv('/opt/chromebook-dashboard/.env')

# Import what we need
from services.sync_service_simple import SimpleSyncService
from integrations.google import GoogleWorkspaceClient
from integrations.incidentiq import IncidentIQClient
from integrations.meraki import MerakiClient
from database.connection import db
from database.models import User

print("\n" + "=" * 80)
print("UNIFIED USER SYNC TEST")
print("=" * 80)

# Initialize API clients
print("\n1. Initializing API clients...")
try:
    google_client = GoogleWorkspaceClient(
        credentials_file=os.getenv('GOOGLE_CREDENTIALS_FILE', '/opt/chromebook-dashboard/credentials.json'),
        admin_email=os.getenv('GOOGLE_ADMIN_EMAIL', 'gsync@cr.k12.de.us')
    )
    print("   ✓ Google Workspace client initialized")
except Exception as e:
    print(f"   ✗ Google client failed: {e}")
    sys.exit(1)

try:
    iiq_client = IncidentIQClient(
        site_id=os.getenv('INCIDENTIQ_SITE_ID'),
        api_token=os.getenv('INCIDENTIQ_API_TOKEN'),
        product_id=os.getenv('INCIDENTIQ_PRODUCT_ID', '88df910c-91aa-e711-80c2-0004ffa00050')
    )
    print("   ✓ IncidentIQ client initialized")
except Exception as e:
    print(f"   ✗ IIQ client failed: {e}")
    sys.exit(1)

try:
    meraki_client = MerakiClient(
        api_key=os.getenv('MERAKI_API_KEY'),
        org_id=os.getenv('MERAKI_ORG_ID')
    )
    print("   ✓ Meraki client initialized")
except Exception as e:
    print(f"   ✗ Meraki client failed: {e}")
    sys.exit(1)

# Create sync service
print("\n2. Creating sync service...")
sync_service = SimpleSyncService(
    google_api=google_client,
    iiq_api=iiq_client,
    meraki_api=meraki_client,
    telemetry_api=None
)
print("   ✓ Sync service created")

# Run the unified user sync
print("\n3. Running unified user sync...")
start_time = datetime.now()
try:
    result = sync_service.sync_unified_users()
    elapsed = (datetime.now() - start_time).total_seconds()

    print(f"\n✓ Sync completed in {elapsed:.1f} seconds")
    print(f"  Users processed: {result.get('users_processed')}")
    print(f"  Users merged (Google + IIQ): {result.get('users_merged')}")
    print(f"  Google-only users: {result.get('users_google_only')}")
    print(f"  IIQ-only users: {result.get('users_iiq_only')}")
    print(f"  Users with fees fetched: {result.get('fees_fetched')}")

except Exception as e:
    print(f"\n✗ Sync failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Verify test user
print("\n4. Verifying test user: aadcar677@cr.k12.de.us...")
try:
    with db.get_session() as session:
        test_user = session.query(User).filter(
            User.email.ilike('%aadcar677%')
        ).first()

        if test_user:
            print(f"   ✓ Found user: {test_user.email}")
            print(f"     Name: {test_user.full_name}")
            print(f"     Data source: {test_user.data_source}")
            print(f"     Is merged: {test_user.is_merged}")
            print(f"     Fee balance: ${test_user.total_fee_balance:.2f}" if test_user.total_fee_balance else "     Fee balance: $0.00")
            print(f"     Has outstanding fees: {test_user.has_outstanding_fees}")
            print(f"     IIQ location: {test_user.iiq_location}")
            print(f"     IIQ role: {test_user.iiq_role_name}")

            if test_user.total_fee_balance and test_user.total_fee_balance > 0:
                print(f"\n   ✓✓✓ TEST PASSED: User has fee balance!")
            else:
                print(f"\n   ⚠ WARNING: Expected $50 fee balance, got ${test_user.total_fee_balance:.2f}" if test_user.total_fee_balance else "   ⚠ WARNING: Expected $50 fee balance, got $0.00")
        else:
            print(f"   ✗ Test user not found!")
except Exception as e:
    print(f"   ✗ Error checking test user: {e}")

# Show database stats
print("\n5. Database statistics...")
try:
    with db.get_session() as session:
        total_users = session.query(User).count()
        merged_users = session.query(User).filter(User.is_merged == True).count()
        google_only = session.query(User).filter(User.data_source == 'google').count()
        iiq_only = session.query(User).filter(User.data_source == 'iiq').count()
        merged_data_source = session.query(User).filter(User.data_source == 'merged').count()
        users_with_fees = session.query(User).filter(User.has_outstanding_fees == True).count()
        total_fees = session.query(User).filter(User.total_fee_balance > 0).all()
        total_fee_sum = sum(u.total_fee_balance or 0 for u in total_fees)

        print(f"   Total users: {total_users}")
        print(f"   Merged users (data_source='merged'): {merged_data_source}")
        print(f"   Google-only (data_source='google'): {google_only}")
        print(f"   IIQ-only (data_source='iiq'): {iiq_only}")
        print(f"   Users with outstanding fees: {users_with_fees}")
        print(f"   Total fee balance: ${total_fee_sum:.2f}")

except Exception as e:
    print(f"   ✗ Error getting stats: {e}")

print("\n" + "=" * 80)
