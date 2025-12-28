"""
Chromebook Dashboard - Main Application
Combines IncidentIQ asset data with Google Workspace device information
"""

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from authlib.integrations.starlette_client import OAuth
import redis
import json
import os
from datetime import datetime
from typing import Optional, Dict, List
import logging

# Load environment variables
from dotenv import load_dotenv
load_dotenv('/opt/chromebook-dashboard/.env')

# Database imports
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

# Database Configuration
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'chromebook_dashboard')
DB_USER = os.getenv('DB_USER', 'chromebook_user')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Create database engine
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)

# Create session maker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
SECRET_KEY = os.getenv('SECRET_KEY')
ALLOWED_DOMAIN = os.getenv('ALLOWED_DOMAIN', 'cr.k12.de.us')
ALLOWED_GROUP = os.getenv('ALLOWED_GROUP', '') # Google Group email
REDIRECT_URI = os.getenv('REDIRECT_URI')

# Google API imports
from google.oauth2 import service_account
from googleapiclient.discovery import build

# IncidentIQ integration
from integrations.incidentiq import IncidentIQClient

# Meraki integration
from integrations.meraki import MerakiClient

# Cache integration
from cache.redis_manager import cache, CacheKeys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="Chromebook Dashboard", version="1.0.0")

# Add cache control middleware for static files
class NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Add no-cache headers for JS and CSS files
        if request.url.path.endswith(('.js', '.css')):
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'

        return response

app.add_middleware(NoCacheMiddleware)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Session middleware for authentication
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# OAuth setup
oauth = OAuth()
oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication dependency
async def get_current_user(request: Request):
    user = request.session.get('user')
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

# Redis connection
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Configuration from environment
SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', '/opt/chromebook-dashboard/credentials.json')
DELEGATED_ADMIN_EMAIL = os.getenv('GOOGLE_ADMIN_EMAIL', '')
CACHE_TTL = int(os.getenv('CACHE_TTL', '300'))

# IncidentIQ Configuration
INCIDENTIQ_SITE_ID = os.getenv('INCIDENTIQ_SITE_ID', '')
INCIDENTIQ_API_TOKEN = os.getenv('INCIDENTIQ_API_TOKEN', '')
INCIDENTIQ_PRODUCT_ID = os.getenv('INCIDENTIQ_PRODUCT_ID', '88df910c-91aa-e711-80c2-0004ffa00050')

# Meraki Configuration
MERAKI_API_KEY = os.getenv('MERAKI_API_KEY', '')
MERAKI_ORG_ID = os.getenv('MERAKI_ORG_ID', '')

# Google API scopes
SCOPES = [
    'https://www.googleapis.com/auth/admin.directory.device.chromeos.readonly',
    'https://www.googleapis.com/auth/admin.directory.user.readonly',
    'https://www.googleapis.com/auth/admin.directory.orgunit.readonly',
    'https://www.googleapis.com/auth/admin.directory.group.member.readonly'
]

def get_google_service():
    """Create Google Admin SDK service"""
    try:
        if not os.path.exists(SERVICE_ACCOUNT_FILE):
            raise HTTPException(status_code=500, detail="Service account file not found")
        
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=SCOPES
        )
        
        if DELEGATED_ADMIN_EMAIL:
            credentials = credentials.with_subject(DELEGATED_ADMIN_EMAIL)
        
        return build('admin', 'directory_v1', credentials=credentials)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create Google service: {str(e)}")

def format_mac_address(mac: str) -> str:
    """Format MAC address to XX:XX:XX:XX:XX:XX"""
    if not mac or mac == 'N/A':
        return 'N/A'
    
    clean_mac = mac.replace(':', '').replace('-', '').replace('.', '').upper()
    
    if len(clean_mac) == 12:
        return ':'.join(clean_mac[i:i+2] for i in range(0, 12, 2))
    
    return mac

def get_google_device_by_serial(service, serial_number: str) -> Optional[Dict]:
    """Get Google device by serial number using query"""
    try:
        results = service.chromeosdevices().list(
            customerId='my_customer',
            query=f'id:{serial_number}',
            projection='FULL',
            maxResults=1
        ).execute()
        
        devices = results.get('chromeosdevices', [])
        if devices:
            return devices[0]
        
        return None
        
    except Exception as e:
        logger.error(f"Error fetching Google device {serial_number}: {e}")
        return None


def get_google_user(service, email: str) -> Optional[Dict]:
    """Get Google user info"""
    try:
        user = service.users().get(userKey=email, projection='full').execute()
        return user
    except Exception as e:
        logger.error(f"Error fetching Google user {email}: {e}")
        return None

def get_user_chromebook_history(service, email: str, iiq_client) -> List[Dict]:
    """Get Chromebooks this user has logged into with asset tags from IIQ"""
    try:
        # Search for devices where this user appears in recentUsers
        results = service.chromeosdevices().list(
            customerId='my_customer',
            projection='FULL',
            maxResults=100
        ).execute()
        
        devices = results.get('chromeosdevices', [])
        user_devices = []
        
        for device in devices:
            recent_users = device.get('recentUsers', [])
            for recent_user in recent_users:
                if recent_user.get('email', '').lower() == email.lower():
                    serial = device.get('serialNumber', 'N/A')
                    
                    # Try to get asset tag from IIQ
                    asset_tag = 'N/A'
                    asset_id = ''
                    if serial != 'N/A':
                        iiq_results = iiq_client.search_and_extract(serial, limit=1)
                        if iiq_results:
                            asset_tag = iiq_results[0].get('assetTag', 'N/A')
                            asset_id = iiq_results[0].get('assetId', '')
                    
                    user_devices.append({
                        'assetTag': asset_tag,
                        'assetId': asset_id,
                        'serialNumber': serial,
                        'model': device.get('model', 'N/A'),
                        'lastSync': device.get('lastSync', 'N/A'),
                        'orgUnitPath': device.get('orgUnitPath', 'N/A')
                    })
                    break
        
        # Sort by most recent and limit to 10
        return user_devices[:10]
        
    except Exception as e:
        logger.error(f"Error fetching user device history: {e}")
        return []


@app.get("/login")
async def login(request: Request):
    """Redirect to Google login"""
    redirect_uri = REDIRECT_URI
    return await oauth.google.authorize_redirect(request, redirect_uri)

@app.get("/auth/callback")
async def auth_callback(request: Request):
    """Handle Google OAuth callback"""
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')
        
        # Check domain
        email = user_info.get('email', '')
        if not email.endswith(f'@{ALLOWED_DOMAIN}'):
            raise HTTPException(status_code=403, detail=f"Only {ALLOWED_DOMAIN} emails allowed")
        
        # Check group membership if specified
        if ALLOWED_GROUP:
            try:
                google_service = get_google_service()
                
                # Check if user is in the allowed group (including nested groups)
                try:
                    # hasMember checks both direct and nested membership
                    result = google_service.members().hasMember(
                        groupKey=ALLOWED_GROUP,
                        memberKey=email
                    ).execute()
                    
                    if result.get('isMember'):
                        logger.info(f"User {email} is member of {ALLOWED_GROUP} (direct or nested)")
                    else:
                        logger.warning(f"User {email} not in group {ALLOWED_GROUP}")
                        raise HTTPException(
                            status_code=403, 
                            detail=f"Access denied. You must be a member of {ALLOWED_GROUP}"
                        )
                except HTTPException:
                    raise
                except Exception as e:
                    logger.error(f"Error checking group membership for {email}: {e}")
                    raise HTTPException(
                        status_code=403, 
                        detail=f"Access denied. Could not verify group membership."
                    )
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error checking group membership: {e}")
                raise HTTPException(status_code=500, detail="Authentication error")
        
        # Store user in session
        request.session['user'] = {
            'email': email,
            'name': user_info.get('name'),
            'picture': user_info.get('picture')
        }
        
        return RedirectResponse(url='/')
    except Exception as e:
        logger.error(f"Auth error: {e}")
        raise HTTPException(status_code=400, detail="Authentication failed")

@app.get("/logout")
async def logout(request: Request):
    """Logout user"""
    request.session.clear()
    return RedirectResponse(url='/login')

@app.get("/api/health")
async def health_check(user: dict = Depends(get_current_user), ):
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "redis": redis_client.ping(),
        "google_configured": os.path.exists(SERVICE_ACCOUNT_FILE),
        "incidentiq_configured": bool(INCIDENTIQ_SITE_ID and INCIDENTIQ_API_TOKEN)
    }

@app.get("/api/dashboard/stats")
async def dashboard_stats(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get dashboard analytics from database - instant results"""
    try:
        # Query database for stats (much faster than API calls)
        query = text("""
            SELECT
                COUNT(*) as total_devices,
                COUNT(CASE WHEN status = 'ACTIVE' THEN 1 END) as active,
                COUNT(CASE WHEN status = 'DISABLED' THEN 1 END) as disabled,
                COUNT(CASE WHEN status = 'PROVISIONED' THEN 1 END) as provisioned,
                COUNT(CASE WHEN status = 'DEPROVISIONED' THEN 1 END) as deprovisioned,
                MAX(updated_at) as last_sync
            FROM chromebooks
        """)

        result = db.execute(query).fetchone()

        stats = {
            "total_devices": result[0],
            "active": result[1],
            "disabled": result[2],
            "provisioned": result[3],
            "deprovisioned": result[4],
            "last_sync": result[5].isoformat() if result[5] else None,
            "timestamp": datetime.utcnow().isoformat()
        }

        return stats

    except Exception as e:
        logger.error(f"Dashboard stats error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {str(e)}")

@app.get("/api/dashboard/aue-expiration")
async def dashboard_aue_expiration(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    force_refresh: bool = False
):
    """Get AUE expiration data grouped by year with model names"""
    try:
        cache_key = CacheKeys.dashboard_aue_expiration()
        if not force_refresh:
            cached = cache.get(cache_key)
            if cached:
                logger.info("AUE expiration data served from cache")
                return cached

        # Get current year
        current_year = datetime.now().year

        # Query for expired devices (before current year)
        expired_query = text("""
            SELECT COUNT(*)
            FROM chromebooks
            WHERE status = 'ACTIVE'
            AND aue_date IS NOT NULL
            AND aue_date <> ''
            AND EXTRACT(YEAR FROM aue_date::date) < :current_year
        """)
        expired_result = db.execute(expired_query, {"current_year": current_year}).fetchone()
        expired_count = expired_result[0] if expired_result else 0

        # Query for devices by year (current year and beyond) with models and counts
        years_query = text("""
            SELECT
                aue_year,
                SUM(model_count)::integer as device_count,
                jsonb_agg(
                    jsonb_build_object(
                        'model', model,
                        'count', model_count
                    ) ORDER BY model
                ) as models
            FROM (
                SELECT
                    EXTRACT(YEAR FROM aue_date::date)::integer as aue_year,
                    model,
                    COUNT(*) as model_count
                FROM chromebooks
                WHERE status = 'ACTIVE'
                AND aue_date IS NOT NULL
                AND aue_date <> ''
                AND EXTRACT(YEAR FROM aue_date::date) >= :current_year
                GROUP BY EXTRACT(YEAR FROM aue_date::date)::integer, model
            ) subquery
            GROUP BY aue_year
            ORDER BY aue_year
        """)
        years_results = db.execute(years_query, {"current_year": current_year}).fetchall()

        # Build year data
        years_data = []
        for row in years_results:
            years_data.append({
                "year": row[0],
                "count": row[1],
                "models": row[2] if row[2] else []
            })

        data = {
            "expiredCount": expired_count,
            "years": years_data,
            "currentYear": current_year,
            "timestamp": datetime.utcnow().isoformat()
        }

        cache.set(cache_key, data, ttl=43200)
        logger.info(f"AUE expiration data calculated: {expired_count} expired, {len(years_data)} future years")

        return data

    except Exception as e:
        logger.error(f"Dashboard AUE expiration error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch AUE data: {str(e)}")

@app.get("/api/dashboard/security-alerts")
async def dashboard_security_alerts(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    force_refresh: bool = False
):
    """Get security alerts: Dev mode, poor battery, pending repairs"""
    try:
        cache_key = CacheKeys.dashboard_security_alerts()
        if not force_refresh:
            cached = cache.get(cache_key)
            if cached:
                logger.info("Security alerts data served from cache")
                return cached

        query = text("""
            SELECT
                COUNT(CASE WHEN boot_mode = 'Dev' THEN 1 END) as dev_mode_count,
                COUNT(CASE WHEN battery_health IS NOT NULL AND battery_health < 30 THEN 1 END) as poor_battery_count,
                COUNT(CASE WHEN iiq_status IN ('In Repair', 'Pending Repair', 'Repair Needed') THEN 1 END) as pending_repairs_count,
                COUNT(CASE
                    WHEN boot_mode = 'Dev'
                    OR (battery_health IS NOT NULL AND battery_health < 30)
                    OR iiq_status IN ('In Repair', 'Pending Repair', 'Repair Needed')
                    THEN 1
                END) as total_alerts
            FROM chromebooks
            WHERE status = 'ACTIVE'
        """)

        result = db.execute(query).fetchone()
        data = {
            "devModeCount": result[0],
            "poorBatteryCount": result[1],
            "pendingRepairsCount": result[2],
            "totalAlerts": result[3],
            "timestamp": datetime.utcnow().isoformat()
        }

        cache.set(cache_key, data, ttl=43200)
        logger.info("Security alerts data calculated and cached")

        return data

    except Exception as e:
        logger.error(f"Dashboard security alerts error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch security alerts: {str(e)}")

@app.post("/api/dashboard/refresh-widgets")
async def refresh_dashboard_widgets(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Manually refresh all dashboard widget caches"""
    try:
        cache.delete(CacheKeys.dashboard_aue_expiration())
        cache.delete(CacheKeys.dashboard_security_alerts())

        logger.info(f"Dashboard widget caches invalidated by user: {user.get('email')}")

        return {
            "success": True,
            "message": "Dashboard widgets refreshed successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Dashboard widget refresh error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh widgets: {str(e)}")

@app.get("/api/devices/advanced-search")
async def advanced_device_search(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    status: str = None,
    model: str = None,
    location: str = None,
    org_unit: str = None,
    battery_min: int = None,
    battery_max: int = None,
    boot_mode: str = None,
    aue_year: int = None,
    repair_status: str = None,
    limit: int = 100,
    offset: int = 0
):
    """Advanced multi-criteria device search with pagination"""
    try:
        # Build dynamic WHERE clauses (use c. prefix for chromebooks table)
        conditions = ["1=1"]  # Always true base condition
        params = {}

        if status:
            conditions.append("c.status = :status")
            params["status"] = status

        if model:
            conditions.append("c.model ILIKE :model")
            params["model"] = f"%{model}%"

        if location:
            conditions.append("(c.iiq_location ILIKE :location OR c.annotated_location ILIKE :location)")
            params["location"] = f"%{location}%"

        if org_unit:
            conditions.append("c.org_unit_path LIKE :org_unit || '%'")
            params["org_unit"] = org_unit

        if battery_min is not None:
            conditions.append("c.battery_health >= :battery_min")
            params["battery_min"] = battery_min

        if battery_max is not None:
            conditions.append("c.battery_health <= :battery_max")
            params["battery_max"] = battery_max

        if boot_mode:
            conditions.append("c.boot_mode = :boot_mode")
            params["boot_mode"] = boot_mode

        if aue_year:
            conditions.append("EXTRACT(YEAR FROM c.auto_update_expiration::date) = :aue_year")
            params["aue_year"] = aue_year

        if repair_status:
            conditions.append("c.iiq_status = :repair_status")
            params["repair_status"] = repair_status

        # Add pagination params
        params["limit"] = limit
        params["offset"] = offset

        where_clause = " AND ".join(conditions)

        # Count total matching records
        count_query = text(f"""
            SELECT COUNT(*)
            FROM chromebooks c
            WHERE {where_clause}
        """)
        total_count = db.execute(count_query, params).fetchone()[0]

        # Fetch paginated results with JOIN to get IIQ asset tag and student ID
        data_query = text(f"""
            SELECT
                c.device_id, c.serial_number,
                COALESCE(a.asset_tag, SPLIT_PART(c.asset_tag, ' | ', 1)) as asset_tag,
                c.model, c.status,
                c.annotated_user, c.iiq_owner_email, c.iiq_owner_name,
                c.iiq_location, c.iiq_room, c.annotated_location,
                c.org_unit_path, c.battery_health, c.boot_mode,
                c.auto_update_expiration, c.iiq_status, c.iiq_notes,
                c.last_sync_status, c.updated_at,
                COALESCE(c.iiq_asset_id, a.asset_id) as iiq_asset_id,
                c.mac_address, c.ip_address, c.wan_ip_address, c.os_version, c.last_used_date,
                c.recent_users,
                COALESCE(u.student_id, a.owner_student_id) as student_id,
                COALESCE(u.student_grade, a.owner_student_grade) as student_grade,
                u.full_name as user_full_name
            FROM chromebooks c
            LEFT JOIN assets a ON c.serial_number = a.serial_number
            LEFT JOIN users u ON LOWER(COALESCE(c.iiq_owner_email, c.annotated_user)) = LOWER(u.email)
            WHERE {where_clause}
            ORDER BY COALESCE(a.asset_tag, SPLIT_PART(c.asset_tag, ' | ', 1)) NULLS LAST, c.serial_number
            LIMIT :limit OFFSET :offset
        """)

        results = db.execute(data_query, params).fetchall()

        devices = []
        for row in results:
            devices.append({
                "device_id": row[0],
                "serial_number": row[1],
                "asset_tag": row[2],
                "model": row[3],
                "status": row[4],
                "annotated_user": row[5],
                "iiq_owner_email": row[6],
                "iiq_owner_name": row[7],
                "iiq_location": row[8],
                "iiq_room": row[9],
                "annotated_location": row[10],
                "org_unit_path": row[11],
                "battery_health": row[12],
                "boot_mode": row[13],
                "auto_update_expiration": row[14],
                "iiq_status": row[15],
                "iiq_notes": row[16],
                "last_sync_status": row[17],
                "updated_at": row[18].isoformat() if row[18] else None,
                "iiq_asset_id": row[19],
                "mac_address": row[20],
                "ip_address": row[21],
                "wan_ip_address": row[22],
                "os_version": row[23],
                "last_used_date": row[24].isoformat() if row[24] else None,
                "recent_users": row[25],
                "iiqOwnerStudentId": row[26],
                "studentGrade": row[27],
                "userFullName": row[28]
            })

        logger.info(f"Advanced search: {total_count} devices matched, returning {len(devices)} (offset={offset})")

        return {
            "devices": devices,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "filters_applied": {
                "status": status,
                "model": model,
                "location": location,
                "org_unit": org_unit,
                "battery_min": battery_min,
                "battery_max": battery_max,
                "boot_mode": boot_mode,
                "aue_year": aue_year,
                "repair_status": repair_status
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Advanced search error: {e}")
        raise HTTPException(status_code=500, detail=f"Advanced search failed: {str(e)}")

@app.get("/api/combined/search")
async def combined_search(user: dict = Depends(get_current_user), query: str = "", db: Session = Depends(get_db)):
    """IIQ-first search - real-time data from IIQ API, merged with cached Google data for chromebooks"""
    try:
        if not query:
            return {"devices": [], "count": 0, "source": "none"}

        # STEP 1: Search IIQ API in real-time (all asset types)
        iiq_client = IncidentIQClient(INCIDENTIQ_SITE_ID, INCIDENTIQ_API_TOKEN, INCIDENTIQ_PRODUCT_ID)
        iiq_results = iiq_client.search_and_extract(query, limit=50)

        if not iiq_results:
            return {"devices": [], "count": 0, "source": "iiq"}

        # STEP 2: For chromebooks only, fetch cached Google data from database
        # Build list of serial numbers for chromebooks
        chromebook_serials = [
            asset['serialNumber'] for asset in iiq_results
            if asset.get('isChromebook') and asset.get('serialNumber') != 'N/A'
        ]

        # Query database for Google data (if any chromebooks found)
        google_data_lookup = {}
        if chromebook_serials:
            google_query = text("""
                SELECT
                    serial_number,
                    device_id,
                    status as google_status,
                    org_unit_path,
                    mac_address,
                    ip_address,
                    os_version,
                    last_used_date,
                    annotated_user,
                    recent_users,
                    meraki_ap_name,
                    meraki_network,
                    last_seen_meraki,
                    battery_health,
                    battery_cycle_count,
                    platform_version,
                    firmware_version,
                    wan_ip_address
                FROM chromebooks
                WHERE serial_number = ANY(:serials)
            """)

            google_results = db.execute(google_query, {"serials": chromebook_serials}).fetchall()
            google_data_lookup = {row[0]: row for row in google_results}

        # STEP 3: Merge IIQ data with Google data
        devices = []
        for iiq_asset in iiq_results:
            serial = iiq_asset.get('serialNumber', 'N/A')
            is_chromebook = iiq_asset.get('isChromebook', False)

            # Base device data from IIQ (real-time)
            device = {
                'assetId': iiq_asset.get('assetId', ''),
                'assetTag': iiq_asset.get('assetTag', 'N/A'),
                'serialNumber': serial,
                'model': iiq_asset.get('model', 'N/A'),
                'deviceType': iiq_asset.get('deviceType', 'Unknown'),
                'iiqStatus': iiq_asset.get('status', 'N/A'),
                'iiqOwnerEmail': iiq_asset.get('assignedUserEmail', ''),
                'iiqOwnerName': iiq_asset.get('assignedUser', 'Not assigned'),
                'iiqOwnerStudentId': iiq_asset.get('assignedUserStudentId', ''),
                'location': iiq_asset.get('location', 'N/A'),
                'source': 'iiq'
            }

            # If chromebook, merge with Google data from database (cached)
            if is_chromebook and serial in google_data_lookup:
                google_row = google_data_lookup[serial]

                # Parse recent_users JSON
                recent_users_json = google_row[9] if google_row[9] else []
                if isinstance(recent_users_json, str):
                    import json as json_lib
                    recent_users_json = json_lib.loads(recent_users_json)

                recent_user_emails = [u.get('email', '') for u in recent_users_json[:5]] if recent_users_json else []
                last_known_user = recent_user_emails[0] if recent_user_emails else device['iiqOwnerEmail'] or 'N/A'

                device.update({
                    'deviceId': google_row[1] or '',
                    'googleStatus': google_row[2] or 'N/A',
                    'orgUnitPath': google_row[3] or 'N/A',
                    'macAddress': format_mac_address(google_row[4]) if google_row[4] else 'N/A',
                    'ipAddress': google_row[5] or 'N/A',
                    'osVersion': google_row[6] or 'N/A',
                    'lastSync': google_row[7].isoformat() if google_row[7] else 'N/A',
                    'assignedUser': google_row[8] or device['iiqOwnerEmail'],
                    'recentUsers': recent_user_emails,
                    'merakiApName': google_row[10],
                    'merakiNetwork': google_row[11],
                    'merakiLastSeen': google_row[12].isoformat() if google_row[12] else None,
                    'batteryHealth': google_row[13],
                    'batteryCycleCount': google_row[14],
                    'platformVersion': google_row[15] or 'N/A',
                    'firmwareVersion': google_row[16] or 'N/A',
                    'wanIpAddress': google_row[17] or 'N/A',
                    'lastKnownUser': last_known_user,
                    'source': 'iiq+google'
                })
            else:
                # Non-chromebook or chromebook without Google data: set defaults
                device.update({
                    'deviceId': '',
                    'googleStatus': 'N/A',
                    'macAddress': 'N/A',
                    'ipAddress': 'N/A',
                    'wanIpAddress': 'N/A',
                    'osVersion': 'N/A',
                    'lastSync': 'N/A',
                    'orgUnitPath': 'N/A',
                    'assignedUser': device['iiqOwnerEmail'],
                    'recentUsers': [],
                    'lastKnownUser': device['iiqOwnerEmail'],
                    'merakiApName': None,
                    'merakiNetwork': None,
                    'merakiLastSeen': None,
                })

            devices.append(device)

        return {"devices": devices, "count": len(devices), "source": "iiq+google"}

    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get("/api/user/search")
async def user_search(user: dict = Depends(get_current_user), query: str = "", db: Session = Depends(get_db)):
    """
    Fast unified user search from database (no API calls).
    Supports email, name, and student ID queries. <200ms latency.
    Returns merged Google + IIQ user data with fee balances.
    """
    try:
        if not query:
            return {"users": [], "count": 0}

        # Database-only query with email, name, and student ID matching
        search_pattern = f"%{query.lower()}%"
        search_query = text("""
            SELECT
                u.id, u.user_id, u.iiq_user_id, u.email, u.full_name, u.first_name, u.last_name,
                u.org_unit_path, u.is_admin, u.is_suspended,
                u.username, u.is_active_iiq, u.iiq_location, u.iiq_role_name,
                u.student_id, u.student_grade, u.total_fee_balance, u.has_outstanding_fees,
                u.data_source, u.is_merged,
                COUNT(DISTINCT c.device_id) as device_count
            FROM users u
            LEFT JOIN chromebooks c ON LOWER(c.iiq_owner_email) = LOWER(u.email)
            WHERE LOWER(u.email) LIKE :query
               OR LOWER(u.full_name) LIKE :query
               OR u.student_id LIKE :query
            GROUP BY u.id
            ORDER BY
                CASE WHEN LOWER(u.email) LIKE :exact_query THEN 0 ELSE 1 END,
                u.full_name ASC
            LIMIT 20
        """)

        results = db.execute(search_query, {
            "query": search_pattern,
            "exact_query": f"%{query.lower()}%"
        }).fetchall()

        users_list = []
        for row in results:
            user_record = {
                'userId': row.user_id,
                'email': row.email,
                'fullName': row.full_name or '',
                'firstName': row.first_name or '',
                'lastName': row.last_name or '',
                'username': row.username,
                'isActive': row.is_active_iiq if row.iiq_user_id else not row.is_suspended,
                'studentId': row.student_id,
                'grade': row.student_grade or 'N/A',
                'location': row.iiq_location or 'N/A',
                'googleOrgUnit': row.org_unit_path or 'N/A',
                'feeBalance': float(row.total_fee_balance) if row.total_fee_balance else 0.0,
                'hasOutstandingFees': row.has_outstanding_fees or False,
                'deviceCount': row.device_count or 0,
                'dataSource': row.data_source,
                'isMerged': row.is_merged
            }
            users_list.append(user_record)

        logger.info(f"User search for '{query}' returned {len(users_list)} results from database")

        return {
            "users": users_list,
            "count": len(users_list)
        }

    except Exception as e:
        logger.error(f"User search error: {e}")
        raise HTTPException(status_code=500, detail=f"User search failed: {str(e)}")



@app.get("/")
async def root(request: Request, user: dict = Depends(get_current_user)):
    """Dashboard UI"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/preview")
async def preview(request: Request, user: dict = Depends(get_current_user)):
    """Design Preview - Test new card design before applying to production"""
    import time
    response = templates.TemplateResponse("preview.html", {
        "request": request,
        "cache_bust": int(time.time())
    })
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.get("/preview-test-dec25")
async def preview_test(request: Request, user: dict = Depends(get_current_user)):
    """TEMPORARY: Test endpoint to bypass ALL caching"""
    import time
    response = templates.TemplateResponse("preview.html", {
        "request": request,
        "cache_bust": int(time.time())
    })
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.get("/dashboard")
async def dashboard(request: Request, user: dict = Depends(get_current_user)):
    """Dashboard UI (alternate route)"""
    return templates.TemplateResponse("dashboard.html", {"request": request})
