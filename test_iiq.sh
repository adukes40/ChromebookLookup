#!/bin/bash

# Update incidentiq.py
cat > /opt/chromebook-dashboard/integrations/incidentiq.py << 'ENDPY'
import requests
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

class IncidentIQClient:
    def __init__(self, site_id: str, api_token: str, base_url: str = "https://crsd.incidentiq.com/api/v1.0"):
        self.site_id = site_id
        self.api_token = api_token
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json'
        })
    
    def search_assets(self, query: str, limit: int = 50) -> List[Dict]:
        try:
            url = f"{self.base_url}/assets/search"
            payload = {"SiteId": self.site_id, "SearchText": query, "PageSize": limit, "PageNumber": 1}
            response = self.session.post(url, json=payload, timeout=10)
            response.raise_for_status()
            return response.json().get('Items', [])
        except Exception as e:
            logger.error(f"IIQ search failed: {e}")
            return []
    
    def extract_asset_info(self, asset: Dict) -> Dict:
        return {
            'assetTag': asset.get('AssetTag', 'N/A'),
            'serialNumber': asset.get('SerialNumber', 'N/A'),
            'assignedUser': asset.get('AssignedUserName', 'Not assigned'),
            'assignedUserEmail': asset.get('AssignedUserEmail', ''),
            'location': asset.get('LocationName', 'N/A'),
            'model': asset.get('Model', 'N/A')
        }
    
    def search_and_extract(self, query: str, limit: int = 50) -> List[Dict]:
        return [self.extract_asset_info(a) for a in self.search_assets(query, limit)]
ENDPY

# Add to .env
grep -q "INCIDENTIQ_SITE_ID" /opt/chromebook-dashboard/.env || cat >> /opt/chromebook-dashboard/.env << 'ENDENV'

INCIDENTIQ_SITE_ID=7c7ece18-33b0-4937-ac36-77d9373997c6
INCIDENTIQ_API_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI3YzdlY2UxOC0zM2IwLTQ5MzctYWMzNi03N2Q5MzczOTk3YzYiLCJzY29wZSI6Imh0dHBzOi8vY3JzZC5pbmNpZGVudGlxLmNvbSIsInN1YiI6Ijc1N2E0NmEyLTU3ZTUtNDNmNi05YzU5LTljZTg2MTJiOWJlMyIsImp0aSI6IjFhOWUwOTA5LTJiZDktZjAxMS04MTk1LTAwMGQzYWUzOWM5ZSIsImlhdCI6MTc2NTc0MzkzMi44MDMsImV4cCI6MTg2MDQzODMzMi44MTd9.f0iEUdvoo2BFwdrtHmkRwomx-q8PObzds2oEzu3Peyw
INCIDENTIQ_API_URL=https://crsd.incidentiq.com/api/v1.0
ENDENV

echo "✅ IncidentIQ integration installed"

# Test connection
cd /opt/chromebook-dashboard
/opt/chromebook-dashboard/venv/bin/python3 << 'ENDTEST'
import sys
sys.path.insert(0, '/opt/chromebook-dashboard')
from integrations.incidentiq import IncidentIQClient

print("Testing IncidentIQ connection...")
client = IncidentIQClient(
    site_id='7c7ece18-33b0-4937-ac36-77d9373997c6',
    api_token='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI3YzdlY2UxOC0zM2IwLTQ5MzctYWMzNi03N2Q5MzczOTk3YzYiLCJzY29wZSI6Imh0dHBzOi8vY3JzZC5pbmNpZGVudGlxLmNvbSIsInN1YiI6Ijc1N2E0NmEyLTU3ZTUtNDNmNi05YzU5LTljZTg2MTJiOWJlMyIsImp0aSI6IjFhOWUwOTA5LTJiZDktZjAxMS04MTk1LTAwMGQzYWUzOWM5ZSIsImlhdCI6MTc2NTc0MzkzMi44MDMsImV4cCI6MTg2MDQzODMzMi44MTd9.f0iEUdvoo2BFwdrtHmkRwomx-q8PObzds2oEzu3Peyw'
)

results = client.search_assets('chromebook', limit=2)
if results:
    print(f SUCCESS! Found {len(results)} assets")
    for asset in results[:2]:
        print(f"  Asset: {asset.get('AssetTag', 'N/A')} | Serial: {asset.get('SerialNumber', 'N/A')}")
else:
    print("⚠️  Connection OK but no results found")
ENDTEST
