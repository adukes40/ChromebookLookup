#!/usr/bin/env python3
"""Auto-installer for search functionality"""
import sys
import re

print("Installing search functionality...")

# Read main.py
with open('/opt/chromebook-dashboard/main.py', 'r') as f:
    content = f.read()

# Check if already installed
if '@app.get("/api/search")' in content:
    print("Search already installed!")
    sys.exit(0)

# Add search endpoint after stats endpoint
search_endpoint = '''

@app.get("/api/search")
async def search_devices(query: str = ""):
    """Search for Chromebook devices"""
    try:
        service = get_google_service()
        search_queries = []
        if query:
            search_queries.append(f"serial_number:{query}")
            search_queries.append(f"asset_id:{query}")
            search_queries.append(f"mac_address:{query}")
            search_queries.append(f"user:{query}")
        
        if not search_queries:
            results = service.chromeosdevices().list(customerId='my_customer', projection='FULL', maxResults=50).execute()
            devices = results.get('chromeosdevices', [])
        else:
            query_string = " OR ".join(search_queries)
            results = service.chromeosdevices().list(customerId='my_customer', query=query_string, projection='FULL', maxResults=50).execute()
            devices = results.get('chromeosdevices', [])
        
        formatted_devices = []
        for device in devices[:50]:
            formatted_devices.append({
                'deviceId': device.get('deviceId', ''),
                'serialNumber': device.get('serialNumber', 'N/A'),
                'assetId': device.get('annotatedAssetId', 'N/A'),
                'model': device.get('model', 'N/A'),
                'status': device.get('status', 'N/A'),
                'lastSync': device.get('lastSync', 'N/A'),
                'osVersion': device.get('osVersion', 'N/A'),
                'macAddress': device.get('macAddress', 'N/A'),
                'user': device.get('annotatedUser', 'N/A'),
                'orgUnitPath': device.get('orgUnitPath', 'N/A')
            })
        return {"devices": formatted_devices, "count": len(formatted_devices)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
'''

# Find where to insert
stats_match = re.search(r'(@app\.get\("/api/stats"\).*?(?=@app\.|$))', content, re.DOTALL)
if stats_match:
    insert_pos = stats_match.end()
    content = content[:insert_pos] + search_endpoint + content[insert_pos:]
    print("✅ Added search endpoint")

# Add search bar HTML
if '<div class="stats-grid">' in content and 'searchInput' not in content:
    search_html = '''        <!-- SEARCH BAR -->
        <div style="background: white; padding: 25px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px;">
            <div style="display: flex; gap: 10px; margin-bottom: 15px;">
                <input type="text" id="searchInput" style="flex: 1; padding: 12px 20px; font-size: 1em; border: 2px solid #e0e0e0; border-radius: 8px;" placeholder="🔍 Search by serial, asset tag, MAC, or user..." onkeypress="if(event.key === \'Enter\') searchDevices()">
                <button style="padding: 12px 30px; background: #667eea; color: white; border: none; border-radius: 8px; cursor: pointer;" onclick="searchDevices()">Search</button>
                <button style="padding: 12px 20px; background: #f44336; color: white; border: none; border-radius: 8px; cursor: pointer;" onclick="clearSearch()">Clear</button>
            </div>
            <div id="searchResults" style="font-size: 0.9em; color: #666;"></div>
        </div>

'''
    content = content.replace('<div class="stats-grid">', search_html + '        <div class="stats-grid">')
    print("✅ Added search bar")

# Add JavaScript
if 'function searchDevices()' not in content:
    js_code = '''
        async function searchDevices() {
            const searchTerm = document.getElementById('searchInput').value.trim();
            if (!searchTerm) { alert('Please enter a search term'); return; }
            document.getElementById('deviceList').innerHTML = '<div class="loading">Searching...</div>';
            try {
                const response = await fetch(`/api/search?query=${encodeURIComponent(searchTerm)}`);
                const data = await response.json();
                displayDevices(data.devices);
                document.getElementById('searchResults').innerHTML = `Found ${data.count} device(s)`;
            } catch (error) {
                document.getElementById('deviceList').innerHTML = '<div class="error">Search failed</div>';
            }
        }
        function clearSearch() {
            document.getElementById('searchInput').value = '';
            document.getElementById('searchResults').innerHTML = '';
            loadRecentDevices();
        }
        async function loadRecentDevices() {
            try {
                const response = await fetch('/api/search?query=');
                const data = await response.json();
                displayDevices(data.devices);
            } catch (error) { console.error(error); }
        }
        function displayDevices(devices) {
            const deviceList = document.getElementById('deviceList');
            if (!devices || devices.length === 0) {
                deviceList.innerHTML = '<div style="text-align: center; padding: 40px; color: #999;">No devices found</div>';
                return;
            }
            let html = '';
            devices.forEach(device => {
                const statusClass = device.status === 'ACTIVE' ? 'status-active' : 'status-disabled';
                html += `<div class="device-item"><div style="display: flex; justify-content: space-between; margin-bottom: 8px;"><span style="font-weight: bold;">${device.serialNumber}</span><span class="device-status ${statusClass}">${device.status}</span></div><div style="color: #666; font-size: 0.9em;"><div>Asset: ${device.assetId} | Model: ${device.model}</div><div>User: ${device.user} | MAC: ${device.macAddress}</div></div></div>`;
            });
            deviceList.innerHTML = html;
        }
'''
    content = content.replace('</script>', js_code + '\n    </script>')
    print("✅ Added search JavaScript")

# Save
with open('/opt/chromebook-dashboard/main.py', 'w') as f:
    f.write(content)

print("✅ Installation complete!")
print("\nNext: systemctl restart chromebook-dashboard")
