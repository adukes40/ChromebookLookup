"""IncidentIQ API Integration - All asset types"""
import requests
import logging
from typing import Dict, List, Optional
from cache.redis_manager import cache, CacheKeys
import hashlib
import json

logger = logging.getLogger(__name__)

class IncidentIQClient:
    def __init__(self, site_id: str, api_token: str, product_id: str = '88df910c-91aa-e711-80c2-0004ffa00050'):
        self.site_id = site_id
        self.api_token = api_token
        self.product_id = product_id
        self.base_url = 'https://crsd.incidentiq.com/api/v1.0'
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_token}',
            'Accept': 'application/json'
        })
    
    # ========== ASSET METHODS ==========
    
    def get_asset_by_tag(self, asset_tag: str) -> Optional[Dict]:
        """Get asset by exact asset tag.

        OPTIMIZATION: Caches results for 5 minutes to deduplicate rapid lookups.
        """
        try:
            # Check cache first
            cache_key = f"iiq:asset:tag:{asset_tag.upper()}"
            cached_asset = cache.get(cache_key)
            if cached_asset is not None:
                if cached_asset == "NOT_FOUND":
                    # Cached miss result
                    return None
                logger.info(f"Cache HIT: Returning cached asset for tag {asset_tag}")
                return cached_asset

            url = f'{self.base_url}/assets/assettag/{asset_tag}'
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            if data.get('ItemCount', 0) > 0:
                result = data.get('Items', [])[0]
                # Cache for 5 minutes
                cache.set(cache_key, result, ttl=300)
                return result
            else:
                # Cache miss for 5 minutes to avoid repeated lookups
                cache.set(cache_key, "NOT_FOUND", ttl=300)
                return None
        except Exception as e:
            logger.error(f"Error fetching asset by tag: {e}")
            return None
    
    def search_assets(self, query: str, limit: int = 50) -> List[Dict]:
        """Search for assets - tries direct lookup first, then search with pagination.

        OPTIMIZATION: Full asset dumps (empty query) are cached for 24 hours.
        Individual searches are deduplicated for 5 minutes.
        """
        try:
            # Try direct lookup first if query is not empty
            if query:
                # Check for 5-minute dedup cache on individual searches
                cache_key = CacheKeys.iiq_asset_search(query)
                cached_result = cache.get(cache_key)
                if cached_result is not None:
                    logger.info(f"Cache HIT: Returning {len(cached_result)} assets for '{query}' (dedup 5min)")
                    return cached_result

                direct = self.get_asset_by_tag(query)
                if direct:
                    result = [direct]
                    # Cache for 5 minutes (300 seconds)
                    cache.set(cache_key, result, ttl=300)
                    return result

            # OPTIMIZATION: Check for 24-hour cache on full asset dump (empty query)
            if not query:
                cache_key = CacheKeys.iiq_asset_dump()
                cached_dump = cache.get(cache_key)
                if cached_dump is not None:
                    logger.info(f"Cache HIT: Returning {len(cached_dump)} assets from 24-hour full dump cache")
                    return cached_dump[:limit]

            # Fall back to paginated search
            all_items = []
            page_size = 100  # Max allowed by IIQ API
            skip = 0

            while len(all_items) < limit:
                url = f'{self.base_url}/assets?$s={page_size}&$sk={skip}'
                payload = {
                    "OnlyShowDeleted": False,
                    "Filters": [],
                    "SearchText": query
                }

                headers = self.session.headers.copy()
                headers.update({
                    'Content-Type': 'application/json',
                    'siteid': self.site_id,
                    'productid': self.product_id,
                    'client': 'ApiClient'
                })

                response = requests.post(url, json=payload, headers=headers, timeout=30)
                response.raise_for_status()

                data = response.json()
                items = data.get('Items', [])

                if not items:
                    # No more results
                    break

                all_items.extend(items)
                logger.info(f"Fetched {len(items)} assets (skip={skip}, total so far={len(all_items)})")

                # Check if we've reached the end
                if len(items) < page_size:
                    # Got fewer items than requested, we're done
                    break

                skip += page_size

            logger.info(f"Search found {len(all_items)} total assets for '{query}'")
            result = all_items[:limit]

            # OPTIMIZATION: Cache full asset dumps for 24 hours
            if not query:
                cache_key = CacheKeys.iiq_asset_dump()
                cache.set(cache_key, result, ttl=86400)  # 24 hours
                logger.info(f"Cached full asset dump ({len(result)} assets) for 24 hours")
            else:
                # Cache search results for 5 minutes (dedup)
                cache_key = CacheKeys.iiq_asset_search(query)
                cache.set(cache_key, result, ttl=300)

            return result
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def extract_asset_info(self, asset: Dict) -> Dict:
        """Extract info from IIQ asset including device type"""
        try:
            model = asset.get('Model', {})
            model_name = model.get('Name', 'N/A') if isinstance(model, dict) else str(model)
            
            # Get category to determine device type
            category = model.get('Category', {}) if isinstance(model, dict) else {}
            category_name = category.get('Name', 'Unknown') if isinstance(category, dict) else 'Unknown'
            is_chromebook = category_name == 'Chromebooks'
            
            owner = asset.get('Owner', {})
            owner_name = owner.get('FullName', 'Not assigned') if isinstance(owner, dict) else 'Not assigned'
            owner_email = owner.get('Email', '') if isinstance(owner, dict) else ''
            owner_student_id = owner.get('SchoolIdNumber', '') if isinstance(owner, dict) else ''  # Fixed: was StudentId
            owner_grade = owner.get('Grade', '') if isinstance(owner, dict) else ''

            location = asset.get('Location', {})
            location_name = location.get('Name', 'N/A') if isinstance(location, dict) else 'N/A'

            status = asset.get('Status', {})
            status_name = status.get('Name', 'N/A') if isinstance(status, dict) else 'N/A'

            return {
                'assetId': asset.get('AssetId', ''),
                'assetTag': asset.get('AssetTag', 'N/A'),
                'serialNumber': asset.get('SerialNumber', 'N/A'),
                'model': model_name,
                'assignedUser': owner_name,
                'assignedUserEmail': owner_email,
                'assignedUserStudentId': owner_student_id,
                'assignedUserGrade': owner_grade,
                'location': location_name,
                'room': asset.get('LocationRoomId', 'N/A'),
                'status': status_name,
                'deviceType': category_name,
                'isChromebook': is_chromebook
            }
        except Exception as e:
            logger.error(f"Error extracting asset: {e}")
            return {'serialNumber': 'N/A', 'assetTag': 'N/A', 'isChromebook': False}
    
    def search_and_extract(self, query: str, limit: int = 50) -> List[Dict]:
        """Search and return formatted results"""
        raw = self.search_assets(query, limit)
        return [self.extract_asset_info(a) for a in raw]
    
    # ========== USER METHODS ==========
    
    def search_users(self, query: str, limit: int = 50) -> List[Dict]:
        """Search users using /search/v2 endpoint"""
        try:
            url = f'{self.base_url}/search/v2'
            payload = {
                "Query": query,
                "Facets": 4,  # 4 = Users facet
                "IncludeMatchedItem": False
            }

            headers = self.session.headers.copy()
            headers.update({'Content-Type': 'application/json'})

            response = requests.post(url, json=payload, headers=headers, timeout=15)
            response.raise_for_status()

            data = response.json()
            items = data.get('Items', [])

            # Get full user details for each result
            users = []
            for item in items[:limit]:
                user_id = item.get('Id')
                if user_id:
                    # Fetch full user details
                    user_url = f'{self.base_url}/users/{user_id}'
                    user_response = self.session.get(user_url, timeout=10)
                    if user_response.status_code == 200:
                        user_data = user_response.json()
                        if user_data.get('Item'):
                            users.append(user_data.get('Item'))

            logger.info(f"User search found {len(users)} users for '{query}'")
            return users
        except Exception as e:
            logger.error(f"User search failed: {e}")
            return []

    def get_users(self, page: int = 1, page_size: int = 1000) -> List[Dict]:
        """
        Fetch users from IIQ via pagination.

        This is used for the unified user sync to bring in ALL IIQ users
        and match them with Google Workspace users by email.

        Args:
            page: Page number (1-based)
            page_size: Number of users per page (max 1000)

        Returns:
            List of user dicts with: UserId, Email, Name, FirstName, LastName,
                                    Location, Role, SchoolIdNumber, Grade, etc.
        """
        try:
            # IIQ API uses $skip for pagination (0-based)
            skip = (page - 1) * page_size
            url = f'{self.base_url}/users?$s={page_size}&$sk={skip}'

            response = self.session.get(url, timeout=15)
            response.raise_for_status()

            data = response.json()
            items = data.get('Items', [])

            logger.info(f"Fetched {len(items)} users (page {page}, skip {skip})")
            return items
        except Exception as e:
            logger.error(f"Error fetching users page {page}: {e}")
            return []

    def get_user_assets(self, user_id: str) -> List[Dict]:
        """Get assets assigned to a user"""
        try:
            url = f'{self.base_url}/assets/for/{user_id}'
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return data.get('Items', [])
        except Exception as e:
            logger.error(f"Error fetching user assets: {e}")
            return []
    
    def extract_user_info(self, user: Dict) -> Dict:
        """Extract user information from IIQ"""
        try:
            # Extract role information
            role = user.get('Role', {})
            role_name = role.get('Name', '') if isinstance(role, dict) else ''
            is_student = role_name.lower() == 'student'

            # Only include student ID if user is a student
            student_id = None
            if is_student:
                school_id = user.get('SchoolIdNumber')
                if school_id:
                    student_id = str(school_id)

            return {
                'userId': user.get('UserId', ''),
                'fullName': user.get('Name', 'N/A'),
                'firstName': user.get('FirstName', ''),
                'lastName': user.get('LastName', ''),
                'email': user.get('Email', 'N/A'),
                'username': user.get('Username', 'N/A'),
                'location': user.get('LocationName', 'N/A'),
                'locationId': user.get('LocationId', ''),
                'roleId': user.get('RoleId', ''),
                'roleName': role_name,
                'isStudent': is_student,
                'studentId': student_id,
                'grade': user.get('Grade', 'N/A'),
                'isActive': user.get('IsActive', False)
            }
        except Exception as e:
            logger.error(f"Error extracting user: {e}")
            return {'fullName': 'N/A', 'email': 'N/A'}
    
    def search_and_extract_users(self, query: str, limit: int = 50) -> List[Dict]:
        """Search users and return formatted results"""
        raw = self.search_users(query, limit)
        return [self.extract_user_info(u) for u in raw]

    # ========== FEE/INVOICE METHODS ==========

    def get_user_fees(self, user_id: str) -> Dict:
        """Get fee balance for a user with proper IIQ API headers.

        OPTIMIZATION: Caches the successful fee endpoint URL to avoid redundant testing.
        Results also cached for 5 minutes to deduplicate rapid requests.
        """
        try:
            # OPTIMIZATION: Check for 5-minute dedup cache on fee queries
            cache_key = CacheKeys.iiq_user_fees(user_id)
            cached_fees = cache.get(cache_key)
            if cached_fees is not None:
                logger.info(f"Cache HIT: Returning cached fees for user {user_id} (dedup 5min)")
                return cached_fees

            # FIXED: Add required headers for IIQ API v1.0
            # Many IIQ endpoints require siteid, productid, and client headers
            headers = self.session.headers.copy()
            headers.update({
                'siteid': self.site_id,
                'productid': self.product_id,
                'client': 'ApiClient'
            })

            # OPTIMIZATION: Try cached successful endpoint first
            successful_endpoint = cache.get(CacheKeys.iiq_fee_endpoint())
            if successful_endpoint:
                logger.info(f"Using cached successful fee endpoint: {successful_endpoint}")
                try:
                    response = self.session.get(successful_endpoint.format(user_id=user_id), headers=headers, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        result = self._extract_fee_info(data)
                        # Cache for 5 minutes
                        cache.set(cache_key, result, ttl=300)
                        return result
                except Exception as e:
                    logger.warning(f"Cached endpoint failed, will rediscover: {e}")
                    # Fall through to endpoint discovery

            # Try Fee Tracker module endpoints first (most likely)
            endpoints = [
                f'{self.base_url}/feetracker/users/{{user_id}}/balance',
                f'{self.base_url}/feetracker/users/{{user_id}}',
                f'{self.base_url}/apps/feetracker/users/{{user_id}}',
                # Fallback to original endpoints
                f'{self.base_url}/users/{{user_id}}/fees',
                f'{self.base_url}/fees/user/{{user_id}}',
                f'{self.base_url}/invoices/user/{{user_id}}'
            ]

            for endpoint_template in endpoints:
                url = endpoint_template.format(user_id=user_id)
                try:
                    response = self.session.get(url, headers=headers, timeout=10)
                    logger.info(f"Fee API attempt: {url} - Status: {response.status_code}")

                    if response.status_code == 200:
                        data = response.json()
                        logger.info(f"✅ Successfully fetched fees from {url}")
                        logger.debug(f"Fee data response: {data}")
                        result = self._extract_fee_info(data)

                        # OPTIMIZATION: Cache successful endpoint (without user_id param) for future use
                        cache.set(CacheKeys.iiq_fee_endpoint(), endpoint_template, ttl=604800)  # 7 days
                        logger.info(f"Cached successful fee endpoint for 7 days: {endpoint_template}")

                        # Cache result for 5 minutes
                        cache.set(cache_key, result, ttl=300)
                        return result
                    elif response.status_code == 404:
                        logger.debug(f"❌ 404 Not Found: {url}")
                        continue  # Try next endpoint
                    else:
                        logger.warning(f"⚠️ Unexpected status {response.status_code} from {url}")
                        continue
                except Exception as e:
                    logger.warning(f"Failed to fetch from {url}: {e}")
                    continue

            # If all endpoints fail, return zero balance
            logger.warning(f"❌ Could not fetch fees for user {user_id} from any endpoint - all failed")
            result = {'total_balance': 0.0, 'fees': [], 'endpoint_found': False}
            # Cache even the failure result to avoid retrying immediately
            cache.set(cache_key, result, ttl=300)
            return result

        except Exception as e:
            logger.error(f"Error fetching user fees: {e}")
            return {'total_balance': 0.0, 'fees': [], 'endpoint_found': False}

    def _extract_fee_info(self, fee_data: Dict) -> Dict:
        """Extract fee information from IIQ API response"""
        try:
            # Handle different possible response structures
            total_balance = 0.0
            fees = []

            # Check if response has a Balance field
            if 'Balance' in fee_data:
                total_balance = float(fee_data.get('Balance', 0))
            elif 'TotalBalance' in fee_data:
                total_balance = float(fee_data.get('TotalBalance', 0))

            # Check for items/fees list
            items = fee_data.get('Items', fee_data.get('Fees', []))

            if isinstance(items, list):
                for item in items:
                    fee_entry = {
                        'amount': float(item.get('Amount', 0)),
                        'description': item.get('Description', 'Fee'),
                        'date': item.get('Date', ''),
                        'status': item.get('Status', '')
                    }
                    fees.append(fee_entry)
                    # If no total balance provided, sum from items
                    if total_balance == 0:
                        # Only add unpaid/outstanding fees
                        if fee_entry['status'].lower() in ['unpaid', 'outstanding', '']:
                            total_balance += fee_entry['amount']

            return {
                'total_balance': total_balance,
                'fees': fees,
                'endpoint_found': True
            }
        except Exception as e:
            logger.error(f"Error extracting fee info: {e}")
            return {'total_balance': 0.0, 'fees': [], 'endpoint_found': False}
