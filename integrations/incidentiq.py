"""IncidentIQ API Integration - All asset types"""
import requests
import logging
from typing import Dict, List, Optional

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
        """Get asset by exact asset tag"""
        try:
            url = f'{self.base_url}/assets/assettag/{asset_tag}'
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get('ItemCount', 0) > 0:
                return data.get('Items', [])[0]
            return None
        except Exception as e:
            logger.error(f"Error fetching asset by tag: {e}")
            return None
    
    def search_assets(self, query: str, limit: int = 50) -> List[Dict]:
        """Search for assets - tries direct lookup first, then search with pagination"""
        try:
            # Try direct lookup first if query is not empty
            if query:
                direct = self.get_asset_by_tag(query)
                if direct:
                    return [direct]

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
            return all_items[:limit]  # Respect the limit
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
