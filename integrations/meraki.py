"""Meraki API Integration - Device location tracking"""
import requests
import logging
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class MerakiClient:
    def __init__(self, api_key: str, org_id: str):
        self.api_key = api_key
        self.org_id = org_id
        self.base_url = 'https://api.meraki.com/api/v1'
        self.session = requests.Session()
        self.session.headers.update({
            'X-Cisco-Meraki-API-Key': api_key,
            'Content-Type': 'application/json'
        })
    
    def get_ap_name_by_mac(self, network_id: str, ap_mac: str) -> str:
        """Get friendly AP name from MAC address"""
        try:
            url = f'{self.base_url}/networks/{network_id}/devices'
            response = self.session.get(url, timeout=5)
            response.raise_for_status()
            
            devices = response.json()
            
            for device in devices:
                if device.get('mac', '').lower() == ap_mac.lower():
                    return device.get('name') or device.get('model', 'Unknown AP')
            
            return f'AP ({ap_mac[-8:]})'
        except Exception as e:
            logger.error(f"Error getting AP name: {e}")
            return f'AP ({ap_mac[-8:]})'
    
    def get_network_client(self, network_id: str, mac_address: str) -> Optional[Dict]:
        """Get detailed client info from specific network"""
        try:
            # Format MAC without colons
            mac_clean = mac_address.replace(':', '')
            url = f'{self.base_url}/networks/{network_id}/clients/{mac_clean}'
            response = self.session.get(url, timeout=5)
            
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.debug(f"Could not get network client: {e}")
            return None
    
    def get_wireless_client_details(self, network_id: str, mac_address: str) -> Optional[Dict]:
        """Get detailed wireless client info including connected AP"""
        try:
            # Get connection stats for last 24 hours
            url = f'{self.base_url}/networks/{network_id}/wireless/clients/{mac_address}/connectionStats'
            params = {'timespan': 86400}  # 24 hours in seconds
            response = self.session.get(url, params=params, timeout=5)
            response.raise_for_status()
            
            stats = response.json()
            # connectionStats returns the AP MAC in the response
            return stats
        except Exception as e:
            logger.debug(f"Could not get wireless details: {e}")
            return None
    
    def get_device_by_mac(self, mac_address: str) -> Optional[Dict]:
        """
        Get device location info from Meraki by MAC address
        Tries both network clients (current) and search (historical)
        """
        try:
            # First, search to find which network the client is in
            search_url = f'{self.base_url}/organizations/{self.org_id}/clients/search'
            params = {'mac': mac_address}
            
            response = self.session.get(search_url, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get('records'):
                logger.info(f"No Meraki data for MAC {mac_address}")
                return None
            
            # Get the most recent record
            records = sorted(
                data.get('records', []), 
                key=lambda x: x.get('lastSeen', ''), 
                reverse=True
            )
            
            if not records:
                return None
            
            search_client = records[0]
            network_id = search_client.get('network', {}).get('id')
            
            # Try network clients endpoint first (for currently connected devices)
            client = None
            if network_id:
                try:
                    clients_url = f'{self.base_url}/networks/{network_id}/clients'
                    params = {'mac': mac_address}
                    
                    response = self.session.get(clients_url, params=params, timeout=5)
                    
                    if response.status_code == 200:
                        clients = response.json()
                        if clients and len(clients) > 0:
                            client = clients[0]
                            logger.info(f"Found current client data for {mac_address}")
                except Exception as e:
                    logger.debug(f"Network clients query failed: {e}")
            
            # If not currently connected, use search data
            if not client:
                client = search_client
                logger.info(f"Using historical search data for {mac_address}")
            
            # Extract data - handle various field names
            last_seen = client.get('lastSeen')
            
            # Convert timestamp if needed (Meraki can return epoch in seconds)
            if isinstance(last_seen, (int, float)):
                from datetime import datetime
                last_seen = datetime.fromtimestamp(last_seen).isoformat()
            
            # Try to get actual AP from network client details
            network_name = client.get('network', {}).get('name', 'Unknown Network')
            ap_mac = None
            ap_name = None
            
            if network_id:
                # Get detailed client info which may have AP connection
                network_client = self.get_network_client(network_id, mac_address)
                
                if network_client:
                    # Look for AP MAC in various fields
                    ap_mac = (network_client.get('apMac') or 
                             network_client.get('recentDeviceMac'))
                    
                    if ap_mac:
                        device_name = self.get_ap_name_by_mac(network_id, ap_mac)
                        # Only use if it's wireless (AP), not a switch
                        if 'wireless' in device_name.lower() or 'AP' in device_name or '-AP-' in device_name:
                            ap_name = device_name
                
                # Fall back to recentDeviceMac from search
                if not ap_name:
                    ap_mac = client.get('recentDeviceMac')
                    if ap_mac:
                        device_name = self.get_ap_name_by_mac(network_id, ap_mac)
                        if 'wireless' in device_name.lower() or 'AP' in device_name or '-AP-' in device_name:
                            ap_name = device_name
            
            location_info = {
                'lastSeen': last_seen,
                'apName': ap_name or 'Not on Wireless',
                'apMac': ap_mac,
                'networkName': network_name,
                'ssid': client.get('ssid'),
                'ipAddress': client.get('ip'),
                'vlan': client.get('vlan')
            }
            
            logger.info(f"Found Meraki data for {mac_address}: {ap_name or 'No AP'}")
            return location_info
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.info(f"MAC {mac_address} not found in Meraki")
                return None
            logger.error(f"Meraki API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error querying Meraki: {e}")
            return None
    
    def compare_timestamps(self, meraki_time, google_time: str) -> Dict:
        """
        Compare Meraki and Google timestamps
        Returns which is newer and helpful context
        """
        try:
            # Parse timestamps - Meraki can be epoch or ISO
            from datetime import timezone
            
            if isinstance(meraki_time, (int, float)) or (isinstance(meraki_time, str) and meraki_time.isdigit()):
                meraki_dt = datetime.fromtimestamp(float(meraki_time), tz=timezone.utc)
            else:
                meraki_dt = datetime.fromisoformat(str(meraki_time).replace('Z', '+00:00'))
            
            google_dt = datetime.fromisoformat(google_time.replace('Z', '+00:00'))
            
            time_diff = (meraki_dt - google_dt).total_seconds()
            
            if time_diff > 0:
                return {
                    'newerSource': 'meraki',
                    'timeDiff': abs(time_diff),
                    'useLocation': True,
                    'note': 'Meraki location is current'
                }
            else:
                return {
                    'newerSource': 'google',
                    'timeDiff': abs(time_diff),
                    'useLocation': False,
                    'note': 'Google sync is newer - device may have left campus'
                }
        except Exception as e:
            logger.error(f"Error comparing timestamps: {e}")
            return {
                'newerSource': 'unknown',
                'useLocation': True,
                'note': 'Could not compare timestamps'
            }
