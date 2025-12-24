#!/usr/bin/env python3
import json
import os
import sys

print("="*70)
print("GOOGLE API DIAGNOSTIC")
print("="*70)
# Check 1: Files exist
print("\n[1/9] Checking files...")
if os.path.exists('/opt/chromebook-dashboard/credentials.json'):
    print("✅ credentials.json exists")
    # Check if valid JSON
    try:
        with open('/opt/chromebook-dashboard/credentials.json') as f:
            creds = json.load(f)
        print("✅ credentials.json is valid JSON")
        print(f"   Service Account: {creds.get('client_email', 'NOT FOUND')}")
        print(f"   Client ID: {creds.get('client_id', 'NOT FOUND')}")
        print(f"   Project: {creds.get('project_id', 'NOT FOUND')}")
    except Exception as e:
        print(f"❌ credentials.json is INVALID: {e}")
        sys.exit(1)
else:
    print("❌ credentials.json NOT FOUND")
    sys.exit(1)

if os.path.exists('/opt/chromebook-dashboard/.env'):
    print("✅ .env exists")
    with open('/opt/chromebook-dashboard/.env') as f:
        for line in f:
            if 'GOOGLE_ADMIN_EMAIL' in line:
                print(f"   {line.strip()}")
else:
    print("❌ .env NOT FOUND")

# Check 2: Import packages
print("\n[2/9] Checking Python packages...")
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    print("✅ Google packages imported")
except ImportError as e:
    print(f"❌ Cannot import Google packages: {e}")
    sys.exit(1)

# Check 3: Load credentials
print("\n[3/9] Loading credentials...")
try:
    SCOPES = [
        'https://www.googleapis.com/auth/admin.directory.device.chromeos.readonly',
        'https://www.googleapis.com/auth/admin.directory.user.readonly',
        'https://www.googleapis.com/auth/admin.directory.orgunit.readonly'
    ]
    credentials = service_account.Credentials.from_service_account_file(
        '/opt/chromebook-dashboard/credentials.json',
        scopes=SCOPES
    )
    print(f"✅ Credentials loaded")
except Exception as e:
    print(f"❌ Cannot load credentials: {e}")
    sys.exit(1)

# Check 4: Delegate credentials
print("\n[4/9] Delegating credentials...")
admin_email = 'gsync@cr.k12.de.us'  # YOUR ADMIN EMAIL
try:
    delegated = credentials.with_subject(admin_email)
    print(f"✅ Delegated to {admin_email}")
except Exception as e:
    print(f"❌ Cannot delegate: {e}")
    sys.exit(1)

# Check 5: Build service
print("\n[5/9] Building Admin SDK service...")
try:
    service = build('admin', 'directory_v1', credentials=delegated)
    print("✅ Service built")
except Exception as e:
    print(f"❌ Cannot build service: {e}")
    sys.exit(1)

# Check 6: Test with my_customer
print("\n[6/9] Testing API with 'my_customer'...")
try:
    result = service.chromeosdevices().list(
        customerId='my_customer',
        maxResults=1
    ).execute()
    devices = result.get('chromeosdevices', [])
    print(f"✅ 'my_customer' WORKS! Found {len(devices)} device(s)")
    if devices:
        print(f"   Serial: {devices[0].get('serialNumber', 'N/A')}")
except Exception as e:
    print(f"❌ 'my_customer' FAILED: {e}")
    
# Check 7: Test with C01ymauv1
print("\n[7/9] Testing API with 'C01ymauv1'...")
try:
    result = service.chromeosdevices().list(
        customerId='C01ymauv1',
        maxResults=1
    ).execute()
    devices = result.get('chromeosdevices', [])
    print(f"✅ 'C01ymauv1' WORKS! Found {len(devices)} device(s)")
    if devices:
        print(f"   Serial: {devices[0].get('serialNumber', 'N/A')}")
except Exception as e:
    print(f"❌ 'C01ymauv1' FAILED: {e}")

# Check 8: Current google.py setting
print("\n[8/9] Checking google.py customer ID...")
try:
    with open('/opt/chromebook-dashboard/integrations/google.py') as f:
        content = f.read()
        if "'my_customer'" in content:
            print("   Current: Using 'my_customer'")
        elif "'C01ymauv1'" in content:
            print("   Current: Using 'C01ymauv1'")
        else:
            print("   Current: Unknown/Custom")
except Exception as e:
    print(f"❌ Cannot read google.py: {e}")

# Check 9: Check for cache
print("\n[9/9] Checking for Python cache...")
cache_dirs = []
for root, dirs, files in os.walk('/opt/chromebook-dashboard'):
    if '__pycache__' in dirs:
        cache_dirs.append(os.path.join(root, '__pycache__'))
    for f in files:
        if f.endswith('.pyc'):
            cache_dirs.append(os.path.join(root, f))

if cache_dirs:
    print(f"⚠️  Found {len(cache_dirs)} cache file(s)/dir(s)")
    print("   Run: rm -rf /opt/chromebook-dashboard/__pycache__ /opt/chromebook-dashboard/integrations/__pycache__")
else:
    print("✅ No cache found")

print("\n" + "="*70)
print("DIAGNOSTIC COMPLETE")
print("="*70)
