"""Export Google Workspace device data to Google Sheets for Looker Studio"""
import os
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
import gspread
from datetime import datetime

load_dotenv('/opt/chromebook-dashboard/.env')

# Configuration
CREDENTIALS_FILE = '/opt/chromebook-dashboard/credentials.json'
GOOGLE_ADMIN_EMAIL = os.getenv('GOOGLE_ADMIN', 'gsync@cr.k12.de.us')
GOOGLE_CUSTOMER_ID = 'my_customer'
SPREADSHEET_NAME = 'Chromebook Dashboard - Device Data'

SCOPES = [
    'https://www.googleapis.com/auth/admin.directory.device.chromeos.readonly',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
]

def get_all_chromebooks():
    """Fetch all Chromebooks from Google Workspace"""
    print("Fetching Chromebooks from Google Workspace...")
    
    credentials = service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE, scopes=SCOPES
    )
    credentials = credentials.with_subject(GOOGLE_ADMIN_EMAIL)
    
    service = build('admin', 'directory_v1', credentials=credentials)
    
    devices = []
    page_token = None
    
    while True:
        results = service.chromeosdevices().list(
            customerId=GOOGLE_CUSTOMER_ID,
            projection='FULL',
            maxResults=200,
            pageToken=page_token
        ).execute()
        
        devices.extend(results.get('chromeosdevices', []))
        page_token = results.get('nextPageToken')
        
        print(f"  Fetched {len(devices)} devices so far...")
        
        if not page_token:
            break
    
    print(f"✅ Total devices: {len(devices)}")
    return devices

def export_to_sheet(devices):
    """Export device data to Google Sheet"""
    print("Exporting to Google Sheet...")
    
    credentials = service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE, scopes=SCOPES
    )
    credentials = credentials.with_subject(GOOGLE_ADMIN_EMAIL)
    
    gc = gspread.authorize(credentials)
    
    # Try to open existing spreadsheet or create new one
    try:
        spreadsheet = gc.open(SPREADSHEET_NAME)
        print(f"✅ Opened existing spreadsheet")
    except gspread.SpreadsheetNotFound:
        spreadsheet = gc.create(SPREADSHEET_NAME)
        spreadsheet.share(GOOGLE_ADMIN_EMAIL, perm_type='user', role='writer')
        spreadsheet.share('austin.dukes@cr.k12.de.us', perm_type='user', role='writer')
        print(f"✅ Created new spreadsheet")
    
    # Prepare header row
    headers = [
        'Export Date',
        'Serial Number',
        'Asset ID',
        'Device ID',
        'Status',
        'Model',
        'OS Version',
        'Last Sync',
        'Last Enrolled',
        'Org Unit',
        'Recent User',
        'Annotated Location',
        'Annotated User',
        'MAC Address',
        'Ethernet MAC',
        'Boot Mode',
        'Last IP Address',
        'Active Time (Days)',
        'Auto Update Expiration',
        'Support End Date'
    ]
    
    worksheet_data = [headers]
    
    export_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    for device in devices:
        # Extract recent user
        recent_users = device.get('recentUsers', [])
        recent_user = recent_users[0].get('email', '') if recent_users else ''
        
        # Get last known network
        last_network = device.get('lastKnownNetwork', [{}])[0] if device.get('lastKnownNetwork') else {}
        
        # Calculate active time in days
        active_time_ms = device.get('activeTime', 0)
        active_days = active_time_ms // (1000 * 60 * 60 * 24) if active_time_ms else 0
        
        worksheet_data.append([
            export_date,
            device.get('serialNumber', ''),
            device.get('assetId', ''),
            device.get('deviceId', ''),
            device.get('status', ''),
            device.get('model', ''),
            device.get('osVersion', ''),
            device.get('lastSync', ''),
            device.get('lastEnrollmentTime', ''),
            device.get('orgUnitPath', ''),
            recent_user,
            device.get('annotatedLocation', ''),
            device.get('annotatedUser', ''),
            device.get('macAddress', ''),
            device.get('ethernetMacAddress', ''),
            device.get('bootMode', ''),
            last_network.get('ipAddress', ''),
            active_days,
            device.get('autoUpdateExpiration', ''),
            device.get('supportEndDate', '')
        ])
    
    # Update the worksheet
    try:
        worksheet = spreadsheet.sheet1
    except:
        worksheet = spreadsheet.add_worksheet(title="Device Data", rows=len(worksheet_data)+10, cols=20)
    
    worksheet.clear()
    worksheet.update(worksheet_data, value_input_option='RAW')
    
    print(f"✅ Exported {len(devices)} devices to Google Sheet")
    print(f"📊 Spreadsheet URL: {spreadsheet.url}")
    
    return spreadsheet.url

if __name__ == '__main__':
    try:
        devices = get_all_chromebooks()
        url = export_to_sheet(devices)
        print(f"\n🎉 Data export complete!")
        print(f"URL: {url}")
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
