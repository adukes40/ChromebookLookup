#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, '/opt/chromebook-dashboard')

from services.sync_service_simple import SimpleSyncService

class GoogleWrapper:
    def __init__(self, service):
        self.service = service
        self.customer_id = os.getenv('GOOGLE_CUSTOMER_ID', 'my_customer')
    
    def get_chromebooks(self, max_results=50000):
        devices = []
        request = self.service.chromeosdevices().list(
            customerId=self.customer_id,
            maxResults=100,
            projection='FULL'
            # Don't specify fields - get everything
        )
        while request is not None:
            response = request.execute()
            devices.extend(response.get('chromeosdevices', []))
            request = self.service.chromeosdevices().list_next(request, response)
            if len(devices) % 1000 == 0:
                print(f"  Fetched {len(devices)} devices so far...")
        return devices

from main import get_google_service, IncidentIQClient, MerakiClient
from main import INCIDENTIQ_SITE_ID, INCIDENTIQ_API_TOKEN, INCIDENTIQ_PRODUCT_ID
from main import MERAKI_API_KEY, MERAKI_ORG_ID

print("Initializing clients...")
google_raw = get_google_service()
google = GoogleWrapper(google_raw)

iiq = IncidentIQClient(INCIDENTIQ_SITE_ID, INCIDENTIQ_API_TOKEN, INCIDENTIQ_PRODUCT_ID)
meraki = MerakiClient(MERAKI_API_KEY, MERAKI_ORG_ID) if MERAKI_API_KEY else None

print("Starting full sync of ~26K devices...")
print("This will take several minutes...")
sync = SimpleSyncService(google, iiq, meraki)
result = sync.sync_chromebooks()

print(f"\n✓ Sync complete!")
print(f"  Processed: {result['processed']}")
print(f"  Created: {result['created']}")
print(f"  Updated: {result['updated']}")
