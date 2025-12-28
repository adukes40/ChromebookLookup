"""
Google Chrome Management Telemetry API integration
Handles battery health and device telemetry data
"""

import os
from typing import Dict, List, Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging

logger = logging.getLogger(__name__)

class ChromeTelemetryClient:
    """Client for Chrome Management Telemetry API"""

    SCOPES = [
        'https://www.googleapis.com/auth/chrome.management.telemetry.readonly'
    ]

    def __init__(self, credentials_file: str, admin_email: str, customer_id: str = 'my_customer'):
        """
        Initialize Chrome Telemetry client

        Args:
            credentials_file: Path to service account JSON file
            admin_email: Admin email to impersonate for domain-wide delegation
            customer_id: Google Workspace customer ID (default: 'my_customer')
        """
        self.credentials_file = credentials_file
        self.admin_email = admin_email
        self.customer_id = customer_id
        self.service = None
        self._initialize_service()

    def _initialize_service(self):
        """Initialize the Chrome Management API service"""
        try:
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_file,
                scopes=self.SCOPES
            )

            # Delegate credentials to admin user
            delegated_credentials = credentials.with_subject(self.admin_email)

            # Build the service
            self.service = build('chromemanagement', 'v1', credentials=delegated_credentials)
            logger.info(f"Chrome Management Telemetry service initialized with delegation to {self.admin_email}")

        except Exception as e:
            logger.error(f"Failed to initialize Chrome Telemetry service: {e}")
            raise

    def get_device_telemetry(self, device_id: str) -> Optional[Dict]:
        """
        Get telemetry data for a specific device

        Args:
            device_id: The Chrome device ID

        Returns:
            Telemetry dictionary or None if not found
        """
        try:
            name = f"customers/{self.customer_id}/telemetry/devices/{device_id}"

            telemetry = self.service.customers().telemetry().devices().get(
                name=name,
                readMask='name,deviceId,serialNumber,batteryInfo,batteryStatusReport'
            ).execute()

            logger.info(f"Retrieved telemetry for device {device_id}")
            return telemetry

        except HttpError as e:
            if e.resp.status == 404:
                logger.warning(f"Telemetry for device {device_id} not found")
                return None
            logger.error(f"HTTP error getting telemetry for {device_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting telemetry for {device_id}: {e}")
            raise

    def list_device_telemetry(self, page_size: int = 100, max_results: int = None) -> List[Dict]:
        """
        List telemetry data for all devices with pagination

        Args:
            page_size: Number of devices per page (max 100)
            max_results: Maximum total results to return (None = all)

        Returns:
            List of telemetry dictionaries
        """
        try:
            devices = []
            page_token = None

            while True:
                parent = f"customers/{self.customer_id}"

                request = self.service.customers().telemetry().devices().list(
                    parent=parent,
                    pageSize=min(page_size, 100),
                    pageToken=page_token,
                    readMask='name,deviceId,serialNumber,batteryInfo,batteryStatusReport'
                )

                response = request.execute()

                batch = response.get('devices', [])
                devices.extend(batch)

                logger.info(f"Fetched {len(batch)} devices telemetry (total: {len(devices)})")

                # Check if we should continue
                page_token = response.get('nextPageToken')
                if not page_token:
                    break
                if max_results and len(devices) >= max_results:
                    devices = devices[:max_results]
                    break

            logger.info(f"Retrieved telemetry for {len(devices)} total devices")
            return devices

        except HttpError as e:
            logger.error(f"HTTP error listing device telemetry: {e}")
            raise
        except Exception as e:
            logger.error(f"Error listing device telemetry: {e}")
            raise

    def extract_battery_info(self, telemetry: Dict) -> Dict:
        """
        Extract battery information from telemetry data

        Args:
            telemetry: Telemetry dictionary from API

        Returns:
            Dictionary with battery fields
        """
        battery_data = {
            'device_id': telemetry.get('deviceId'),
            'serial_number': telemetry.get('serialNumber'),
            'battery_health': None,
            'battery_cycle_count': None,
            'battery_full_charge_capacity': None,
            'battery_design_capacity': None,
            'battery_manufacturer': None,
            'battery_report_time': None
        }

        try:
            # Get battery status reports (array of recent samples)
            battery_reports = telemetry.get('batteryStatusReport', [])

            if battery_reports and len(battery_reports) > 0:
                # Get most recent report (first in array, sorted by report_time desc)
                latest_report = battery_reports[0]

                # Extract report time
                report_time = latest_report.get('reportTime')
                if report_time:
                    battery_data['battery_report_time'] = report_time

                # Extract battery health percentage
                # batteryHealth can be: BATTERY_HEALTH_NORMAL, BATTERY_REPLACE_SOON, BATTERY_REPLACE_NOW
                battery_health_status = latest_report.get('batteryHealth')
                if battery_health_status:
                    # Map status to percentage (best guess without actual percentage)
                    health_map = {
                        'BATTERY_HEALTH_NORMAL': 80,  # Assume good if normal
                        'BATTERY_REPLACE_SOON': 40,   # Degraded
                        'BATTERY_REPLACE_NOW': 20     # Critical
                    }
                    battery_data['battery_health'] = health_map.get(battery_health_status)

                # Extract charge capacity
                full_charge_str = latest_report.get('fullChargeCapacity')
                if full_charge_str:
                    try:
                        battery_data['battery_full_charge_capacity'] = int(full_charge_str)
                    except (ValueError, TypeError):
                        pass

                # Extract cycle count
                cycle_count = latest_report.get('cycleCount')
                if cycle_count:
                    battery_data['battery_cycle_count'] = cycle_count

            # Get static battery info
            battery_info = telemetry.get('batteryInfo', [])
            if battery_info and len(battery_info) > 0:
                info = battery_info[0]
                battery_data['battery_manufacturer'] = info.get('manufacturer')

                # Parse design capacity
                design_capacity_str = info.get('designCapacity')
                if design_capacity_str:
                    try:
                        battery_data['battery_design_capacity'] = int(design_capacity_str)
                    except (ValueError, TypeError):
                        pass

        except Exception as e:
            logger.error(f"Error extracting battery info: {e}")

        return battery_data
