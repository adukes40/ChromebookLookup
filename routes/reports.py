from fastapi import APIRouter
from typing import Dict, Any, List
from datetime import datetime, timedelta
import redis
import json
from sqlalchemy import func, and_
from dateutil import parser as date_parser
from database.connection import db
from database.models import Chromebook
from cache.redis_manager import cache, CacheKeys

router = APIRouter()

# 12-hour cache TTL in seconds
REPORT_CACHE_TTL = 43200


@router.get("/devices/ghost")
async def ghost_devices_report():
    """
    Ghost Device Report - Devices that haven't synced in 90+ days
    but are not marked as lost/deprovisioned
    """
    # Check cache first
    cache_key = CacheKeys.report_ghost()
    cached = cache.get(cache_key)
    if cached:
        cached['from_cache'] = True
        return cached

    try:
        cutoff_date = datetime.now() - timedelta(days=90)

        with db.get_session() as session:
            # Get all ACTIVE devices
            ghost_devices = session.query(Chromebook).filter(
                Chromebook.status == 'ACTIVE',
                Chromebook.last_sync_status.isnot(None)
            ).all()

            results = []
            for device in ghost_devices:
                try:
                    # Parse last_sync and remove timezone info
                    last_sync_dt = date_parser.parse(device.last_sync_status).replace(tzinfo=None)
                    days_since_sync = (datetime.now() - last_sync_dt).days

                    # Only include if older than 90 days
                    if days_since_sync >= 90:
                        results.append({
                            'serial_number': device.serial_number,
                            'asset_tag': device.asset_tag,
                            'model': device.model,
                            'user': device.annotated_user,
                            'location': device.annotated_location,
                            'org_unit': device.org_unit_path,
                            'last_sync': device.last_sync_status,
                            'days_since_sync': days_since_sync,
                            'status': device.status
                        })
                except Exception as e:
                    # Skip devices with bad date formats
                    continue

            result = {
                'success': True,
                'total': len(results),
                'cutoff_days': 90,
                'devices': sorted(results, key=lambda x: x['days_since_sync'], reverse=True),
                'from_cache': False
            }

            # Cache the result
            cache.set(cache_key, result, ttl=REPORT_CACHE_TTL)
            return result
    except Exception as e:
        return {'success': False, 'error': str(e)}

@router.get("/devices/os-compliance")
async def os_compliance_report():
    """
    OS Version Compliance Report
    Breakdown by OS version and AUE dates
    """
    # Check cache first
    cache_key = CacheKeys.report_os_compliance()
    cached = cache.get(cache_key)
    if cached:
        cached['from_cache'] = True
        return cached

    try:
        with db.get_session() as session:
            # Group by OS version
            os_versions = session.query(
                Chromebook.os_version,
                func.count(Chromebook.device_id).label('count')
            ).filter(
                Chromebook.os_version.isnot(None)
            ).group_by(Chromebook.os_version).order_by(func.count(Chromebook.device_id).desc()).all()

            # Group by model for AUE tracking
            model_breakdown = session.query(
                Chromebook.model,
                func.count(Chromebook.device_id).label('count')
            ).filter(
                Chromebook.model.isnot(None)
            ).group_by(Chromebook.model).order_by(func.count(Chromebook.device_id).desc()).all()

            models_with_aue = []
            for model, count in model_breakdown:
                # Get one device of this model that has an AUE date
                sample_device = session.query(Chromebook).filter(
                    Chromebook.model == model,
                    Chromebook.aue_date.isnot(None)
                ).first()

                aue_date = sample_device.aue_date if sample_device else None

                # Check if expired (compare YYYY-MM-DD to today)
                is_expired = None
                if aue_date:
                    try:
                        aue_dt = datetime.strptime(aue_date, '%Y-%m-%d')
                        is_expired = aue_dt < datetime.now()
                    except:
                        is_expired = None

                # Format as YYYY-MM for display
                display_date = aue_date[:7] if aue_date else None

                models_with_aue.append({
                    'model': model,
                    'count': count,
                    'aue_date': display_date,
                    'is_expired': is_expired
                })

            result = {
                'success': True,
                'os_versions': [{'version': v, 'count': c} for v, c in os_versions],
                'models': models_with_aue,
                'total_devices': sum([c for _, c in os_versions]),
                'from_cache': False
            }

            # Cache the result
            cache.set(cache_key, result, ttl=REPORT_CACHE_TTL)
            return result
    except Exception as e:
        return {'success': False, 'error': str(e)}

@router.get("/devices/ou-breakdown")
async def ou_breakdown_report():
    """
    OU Breakdown Report
    Shows device counts per OU with model breakdown
    """
    # Check cache first
    cache_key = CacheKeys.report_ou_breakdown()
    cached = cache.get(cache_key)
    if cached:
        cached['from_cache'] = True
        return cached

    try:
        with db.get_session() as session:
            # Get all OUs with device counts
            ou_counts = session.query(
                Chromebook.org_unit_path,
                func.count(Chromebook.device_id).label('total_count')
            ).filter(
                Chromebook.org_unit_path.isnot(None)
            ).group_by(Chromebook.org_unit_path).order_by(func.count(Chromebook.device_id).desc()).all()

            results = []
            for ou, total_count in ou_counts:
                # Get model breakdown for this OU
                models = session.query(
                    Chromebook.model,
                    func.count(Chromebook.device_id).label('count')
                ).filter(
                    Chromebook.org_unit_path == ou,
                    Chromebook.model.isnot(None)
                ).group_by(Chromebook.model).order_by(func.count(Chromebook.device_id).desc()).all()

                model_breakdown = [{'model': m, 'count': c} for m, c in models]

                results.append({
                    'org_unit': ou,
                    'total_count': total_count,
                    'models': model_breakdown
                })

            result = {
                'success': True,
                'total_ous': len(results),
                'org_units': results,
                'from_cache': False
            }

            # Cache the result
            cache.set(cache_key, result, ttl=REPORT_CACHE_TTL)
            return result
    except Exception as e:
        return {'success': False, 'error': str(e)}

@router.get("/devices/summary")
async def devices_summary():
    """
    Dashboard summary with key metrics (cached for 12 hours)
    """
    # Check cache first
    cache_key = CacheKeys.report_summary()
    cached = cache.get(cache_key)
    if cached:
        cached['from_cache'] = True
        return cached

    try:
        with db.get_session() as session:
            # Total active devices
            total_active = session.query(func.count(Chromebook.device_id)).filter(
                Chromebook.status == 'ACTIVE'
            ).scalar()

            # Total devices (all statuses)
            total_devices = session.query(func.count(Chromebook.device_id)).scalar()

            # Ghost devices (90+ days)
            cutoff_date = datetime.now() - timedelta(days=90)
            ghost_devices = session.query(Chromebook).filter(
                Chromebook.status == 'ACTIVE',
                Chromebook.last_sync_status.isnot(None)
            ).all()

            ghost_count = 0
            for device in ghost_devices:
                try:
                    last_sync_dt = date_parser.parse(device.last_sync_status).replace(tzinfo=None)
                    if (datetime.now() - last_sync_dt).days >= 90:
                        ghost_count += 1
                except:
                    continue

            # Devices by status
            status_breakdown = session.query(
                Chromebook.status,
                func.count(Chromebook.device_id).label('count')
            ).group_by(Chromebook.status).all()

            # Top 5 OUs
            top_ous = session.query(
                Chromebook.org_unit_path,
                func.count(Chromebook.device_id).label('count')
            ).filter(
                Chromebook.org_unit_path.isnot(None)
            ).group_by(Chromebook.org_unit_path).order_by(
                func.count(Chromebook.device_id).desc()
            ).limit(5).all()

            # Devices needing updates (old OS versions)
            # Consider anything not on the latest 2 versions as needing updates
            os_versions = session.query(
                Chromebook.os_version,
                func.count(Chromebook.device_id).label('count')
            ).filter(
                Chromebook.os_version.isnot(None)
            ).group_by(Chromebook.os_version).order_by(
                func.count(Chromebook.device_id).desc()
            ).all()

            # Get the top 2 versions
            latest_versions = [v[0] for v in os_versions[:2]] if len(os_versions) >= 2 else []

            needs_update = session.query(func.count(Chromebook.device_id)).filter(
                Chromebook.os_version.notin_(latest_versions) if latest_versions else True,
                Chromebook.status == 'ACTIVE'
            ).scalar()

            # Poor battery health (30% or below)
            poor_battery_count = session.query(func.count(Chromebook.device_id)).filter(
                Chromebook.battery_health.isnot(None),
                Chromebook.battery_health <= 30,
                Chromebook.status == 'ACTIVE'
            ).scalar()

            result = {
                'success': True,
                'total_devices': total_devices,
                'total_active': total_active,
                'ghost_count': ghost_count,
                'needs_update': needs_update,
                'poor_battery_count': poor_battery_count,
                'status_breakdown': [{'status': s, 'count': c} for s, c in status_breakdown],
                'top_ous': [{'ou': ou, 'count': c} for ou, c in top_ous],
                'latest_os_versions': latest_versions,
                'from_cache': False
            }

            # Cache the result
            cache.set(cache_key, result, ttl=REPORT_CACHE_TTL)
            return result
    except Exception as e:
        return {'success': False, 'error': str(e)}


@router.get("/devices/aue-status")
async def aue_status_report():
    """
    AUE Status Report - breakdown by active, expired, and unknown
    """
    # Check cache first
    cache_key = CacheKeys.report_aue_status()
    cached = cache.get(cache_key)
    if cached:
        cached['from_cache'] = True
        return cached

    try:
        with db.get_session() as session:
            # Get all models with counts and AUE dates
            models = session.query(
                Chromebook.model,
                Chromebook.aue_date,
                func.count(Chromebook.device_id).label('count')
            ).filter(
                Chromebook.model.isnot(None)
            ).group_by(Chromebook.model, Chromebook.aue_date).order_by(
                func.count(Chromebook.device_id).desc()
            ).all()

            # Categorize
            active_models = []
            expired_models = []
            unknown_models = []

            for model, aue_date, count in models:
                if aue_date:
                    try:
                        aue_dt = datetime.strptime(aue_date, '%Y-%m-%d')
                        is_expired = aue_dt < datetime.now()
                        aue_display = aue_date[:7]  # YYYY-MM format

                        if is_expired:
                            expired_models.append({'model': model, 'aue_date': aue_display, 'count': count})
                        else:
                            active_models.append({'model': model, 'aue_date': aue_display, 'count': count})
                    except:
                        unknown_models.append({'model': model, 'aue_date': aue_date[:7] if aue_date else None, 'count': count})
                else:
                    unknown_models.append({'model': model, 'aue_date': None, 'count': count})

            result = {
                'success': True,
                'active': {
                    'models': active_models,
                    'total_models': len(active_models),
                    'total_devices': sum(m['count'] for m in active_models)
                },
                'expired': {
                    'models': expired_models,
                    'total_models': len(expired_models),
                    'total_devices': sum(m['count'] for m in expired_models)
                },
                'unknown': {
                    'models': unknown_models,
                    'total_models': len(unknown_models),
                    'total_devices': sum(m['count'] for m in unknown_models)
                },
                'from_cache': False
            }

            # Cache the result
            cache.set(cache_key, result, ttl=REPORT_CACHE_TTL)
            return result
    except Exception as e:
        return {'success': False, 'error': str(e)}

@router.get("/devices/model-details/{model}")
async def model_details_report(model: str):
    """
    Get all devices for a specific model
    """
    # Check cache first
    cache_key = CacheKeys.report_model_details(model)
    cached = cache.get(cache_key)
    if cached:
        cached['from_cache'] = True
        return cached

    try:
        with db.get_session() as session:
            devices = session.query(Chromebook).filter(
                Chromebook.model == model
            ).order_by(Chromebook.asset_tag).all()

            device_list = []
            for device in devices:
                device_list.append({
                    'serial_number': device.serial_number,
                    'asset_tag': device.asset_tag,
                    'user': device.annotated_user,
                    'location': device.annotated_location,
                    'status': device.status,
                    'org_unit': device.org_unit_path,
                    'os_version': device.os_version,
                    'last_sync': device.last_sync_status,
                    'aue_date': device.aue_date
                })

            result = {
                'success': True,
                'model': model,
                'total': len(device_list),
                'devices': device_list,
                'from_cache': False
            }

            # Cache the result
            cache.set(cache_key, result, ttl=REPORT_CACHE_TTL)
            return result
    except Exception as e:
        return {'success': False, 'error': str(e)}


@router.get("/devices/aue-year/{year}")
async def aue_year_report(year: str):
    """
    AUE Year Report - All devices with AUE in a specific year
    """
    # Check cache first
    cache_key = CacheKeys.report_aue_year(year)
    cached = cache.get(cache_key)
    if cached:
        cached['from_cache'] = True
        return cached

    try:
        with db.get_session() as session:
            # Filter devices where aue_date starts with the year
            devices = session.query(Chromebook).filter(
                Chromebook.aue_date.isnot(None),
                Chromebook.aue_date.like(f"{year}%")
            ).order_by(Chromebook.aue_date, Chromebook.model).all()

            # Check if year is expired
            is_expired = int(year) < datetime.now().year

            device_list = []
            for device in devices:
                device_list.append({
                    'serial_number': device.serial_number,
                    'asset_tag': device.asset_tag,
                    'model': device.model,
                    'aue_date': device.aue_date,
                    'user': device.annotated_user,
                    'location': device.annotated_location,
                    'status': device.status,
                    'org_unit': device.org_unit_path
                })

            result = {
                'success': True,
                'year': year,
                'is_expired': is_expired,
                'total': len(device_list),
                'devices': device_list,
                'from_cache': False
            }

            # Cache the result
            cache.set(cache_key, result, ttl=REPORT_CACHE_TTL)
            return result
    except Exception as e:
        return {'success': False, 'error': str(e)}


@router.get("/devices/battery-health")
async def battery_health_report(threshold: int = 30):
    """
    Poor Battery Health Report - Devices with battery health below threshold
    Default threshold is 30%
    """
    # Check cache first
    cache_key = CacheKeys.report_battery_health(threshold)
    cached = cache.get(cache_key)
    if cached:
        cached['from_cache'] = True
        return cached

    try:
        with db.get_session() as session:
            devices = session.query(Chromebook).filter(
                Chromebook.battery_health.isnot(None),
                Chromebook.battery_health <= threshold,
                Chromebook.status == 'ACTIVE'
            ).order_by(Chromebook.battery_health.asc()).all()

            device_list = []
            for device in devices:
                device_list.append({
                    'serial_number': device.serial_number,
                    'asset_tag': device.asset_tag,
                    'battery_health': device.battery_health,
                    'battery_cycle_count': device.battery_cycle_count,
                    'model': device.model,
                    'user': device.annotated_user,
                    'location': device.annotated_location,
                    'org_unit': device.org_unit_path,
                    'status': device.status
                })

            result = {
                'success': True,
                'total': len(device_list),
                'threshold': threshold,
                'devices': device_list,
                'from_cache': False
            }

            # Cache the result
            cache.set(cache_key, result, ttl=REPORT_CACHE_TTL)
            return result
    except Exception as e:
        return {'success': False, 'error': str(e)}


def invalidate_report_cache():
    """
    Invalidate all report caches - call this after sync completes
    """
    try:
        deleted = cache.delete_pattern("report:*")
        print(f"Invalidated {deleted} report cache keys")
        return deleted
    except Exception as e:
        print(f"Error invalidating report cache: {e}")
        return 0
