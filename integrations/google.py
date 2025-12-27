"""
Google Workspace Admin SDK integration
Handles Chromebook device management via Google Admin API
"""

import os
import time
from typing import Dict, List, Optional, Callable, Any
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryError
)
import logging

logger = logging.getLogger(__name__)

class GoogleWorkspaceClient:
    """Client for Google Workspace Admin SDK"""
    
    SCOPES = [
        'https://www.googleapis.com/auth/admin.directory.device.chromeos.readonly',
        'https://www.googleapis.com/auth/admin.directory.user.readonly',
        'https://www.googleapis.com/auth/admin.directory.orgunit.readonly'
    ]
    
    def __init__(self, credentials_file: str, admin_email: str):
        """
        Initialize Google Workspace client
        
        Args:
            credentials_file: Path to service account JSON file
            admin_email: Email of admin user to impersonate
        """
        self.credentials_file = credentials_file
        self.admin_email = admin_email
        self.service = None
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize the Google Admin SDK service"""
        try:
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_file,
                scopes=self.SCOPES
            )
            
            # Delegate credentials to admin user
            delegated_credentials = credentials.with_subject(self.admin_email)
            
            # Build the service
            self.service = build('admin', 'directory_v1', credentials=delegated_credentials)
            logger.info("Google Workspace service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Workspace service: {e}")
            raise

    def _execute_with_retry(self, request_func: Callable) -> Any:
        """
        Execute a Google API request with exponential backoff retry logic

        Handles transient failures (timeout, connection errors) and rate limiting (429)

        Args:
            request_func: Callable that returns a Google API request object

        Returns:
            Result from the API call
        """
        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=60),
            retry=retry_if_exception_type((
                Exception,  # Catches connection errors, timeouts
            )),
            reraise=True
        )
        def execute_request():
            try:
                result = request_func().execute()
                return result
            except HttpError as e:
                # Handle rate limiting (429)
                if e.resp.status == 429:
                    retry_after = int(e.resp.get('retry-after', 60))
                    logger.warning(f"Rate limited by Google API. Waiting {retry_after}s before retry")
                    time.sleep(retry_after)
                    # Retry the request one more time after waiting
                    return request_func().execute()
                # Temporary server errors that should be retried
                elif e.resp.status in (500, 502, 503, 504):
                    logger.warning(f"Google API returned {e.resp.status}, retrying...")
                    raise  # Let tenacity handle the retry
                # Permanent errors that should not be retried
                elif e.resp.status in (400, 401, 403, 404):
                    logger.error(f"Permanent Google API error {e.resp.status}: {e}")
                    raise  # Don't retry
                else:
                    logger.warning(f"Google API error {e.resp.status}, will retry...")
                    raise
            except Exception as e:
                # Transient network errors - will be retried
                logger.warning(f"Transient error calling Google API: {e}, will retry...")
                raise

        return execute_request()

    def get_chromebooks(self, query: Optional[str] = None, max_results: int = 500) -> List[Dict]:
        """
        Get list of Chromebook devices
        
        Args:
            query: Optional search query
            max_results: Maximum number of results to return
            
        Returns:
            List of Chromebook device dictionaries
        """
        try:
            chromebooks = []
            page_token = None

            while True:
                if query:
                    results = self._execute_with_retry(
                        lambda: self.service.chromeosdevices().list(
                            customerId='my_customer',
                            query=query,
                            maxResults=min(max_results, 100),
                            pageToken=page_token,
                            projection='FULL'
                        )
                    )
                else:
                    results = self._execute_with_retry(
                        lambda: self.service.chromeosdevices().list(
                            customerId='my_customer',
                            maxResults=min(max_results, 100),
                            pageToken=page_token,
                            projection='FULL'
                        )
                    )

                devices = results.get('chromeosdevices', [])
                chromebooks.extend(devices)

                page_token = results.get('nextPageToken')
                if not page_token or len(chromebooks) >= max_results:
                    break

            logger.info(f"Retrieved {len(chromebooks)} Chromebooks")
            return chromebooks[:max_results]

        except HttpError as e:
            logger.error(f"HTTP error getting Chromebooks after retries: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting Chromebooks after retries: {e}")
            raise
    
    def get_chromebook_by_id(self, device_id: str) -> Optional[Dict]:
        """
        Get a single Chromebook by device ID

        Args:
            device_id: The device ID to look up

        Returns:
            Device dictionary or None if not found
        """
        try:
            device = self._execute_with_retry(
                lambda: self.service.chromeosdevices().get(
                    customerId='my_customer',
                    deviceId=device_id,
                    projection='FULL'
                )
            )

            logger.info(f"Retrieved Chromebook {device_id}")
            return device

        except HttpError as e:
            if e.resp.status == 404:
                logger.warning(f"Chromebook {device_id} not found")
                return None
            logger.error(f"HTTP error getting Chromebook {device_id} after retries: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting Chromebook {device_id} after retries: {e}")
            raise
    
    def search_chromebooks(self, serial: Optional[str] = None, 
                          asset_id: Optional[str] = None,
                          user: Optional[str] = None) -> List[Dict]:
        """
        Search for Chromebooks by various criteria
        
        Args:
            serial: Serial number
            asset_id: Asset ID
            user: User email
            
        Returns:
            List of matching Chromebook devices
        """
        queries = []
        
        if serial:
            queries.append(f"serial_number:{serial}")
        if asset_id:
            queries.append(f"asset_id:{asset_id}")
        if user:
            queries.append(f"user:{user}")
        
        if not queries:
            return self.get_chromebooks()
        
        query = " OR ".join(queries)
        return self.get_chromebooks(query=query)
    
    def get_user_info(self, email: str) -> Optional[Dict]:
        """
        Get information about a user

        Args:
            email: User email address

        Returns:
            User dictionary or None if not found
        """
        try:
            user = self._execute_with_retry(
                lambda: self.service.users().get(userKey=email)
            )
            logger.info(f"Retrieved user info for {email}")
            return user

        except HttpError as e:
            if e.resp.status == 404:
                logger.warning(f"User {email} not found")
                return None
            logger.error(f"HTTP error getting user {email}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting user {email}: {e}")
            raise

    def list_all_users(self, max_results: int = 50000) -> list:
        """
        List all users in the Google Workspace domain

        Args:
            max_results: Maximum number of users to fetch

        Returns:
            List of user dictionaries
        """
        try:
            users = []
            page_token = None

            logger.info("Fetching all users from Google Workspace...")

            while len(users) < max_results:
                # Fetch users in batches of 500 (max allowed by API)
                batch_size = min(500, max_results - len(users))

                response = self._execute_with_retry(
                    lambda: self.service.users().list(
                        customer='my_customer',
                        maxResults=batch_size,
                        pageToken=page_token,
                        orderBy='email',
                        projection='full',
                        viewType='domain_public'
                    )
                )

                batch_users = response.get('users', [])
                users.extend(batch_users)

                logger.info(f"Fetched {len(users)} users so far...")

                # Check if there are more pages
                page_token = response.get('nextPageToken')
                if not page_token:
                    break

            logger.info(f"Successfully fetched {len(users)} total users from Google Workspace")
            return users

        except HttpError as e:
            logger.error(f"HTTP error listing users: {e}")
            raise
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            raise

    def get_org_unit(self, org_unit_path: str) -> Optional[Dict]:
        """
        Get information about an organizational unit

        Args:
            org_unit_path: Path to the organizational unit

        Returns:
            Org unit dictionary or None if not found
        """
        try:
            org_unit = self._execute_with_retry(
                lambda: self.service.orgunits().get(
                    customerId='my_customer',
                    orgUnitPath=org_unit_path
                )
            )

            logger.info(f"Retrieved org unit {org_unit_path}")
            return org_unit

        except HttpError as e:
            if e.resp.status == 404:
                logger.warning(f"Org unit {org_unit_path} not found")
                return None
            logger.error(f"HTTP error getting org unit {org_unit_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting org unit {org_unit_path}: {e}")
            raise
    
    def get_statistics(self) -> Dict:
        """
        Get statistics about Chromebook devices
        
        Returns:
            Dictionary with device statistics
        """
        try:
            all_devices = self.get_chromebooks()
            
            stats = {
                'total_devices': len(all_devices),
                'active_devices': 0,
                'inactive_devices': 0,
                'provisioned_devices': 0,
                'deprovisioned_devices': 0,
                'disabled_devices': 0,
            }
            
            for device in all_devices:
                status = device.get('status', '').upper()
                
                if status == 'ACTIVE':
                    stats['active_devices'] += 1
                elif status == 'INACTIVE':
                    stats['inactive_devices'] += 1
                elif status == 'PROVISIONED':
                    stats['provisioned_devices'] += 1
                elif status == 'DEPROVISIONED':
                    stats['deprovisioned_devices'] += 1
                elif status == 'DISABLED':
                    stats['disabled_devices'] += 1
            
            logger.info("Retrieved device statistics")
            return stats
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            raise
