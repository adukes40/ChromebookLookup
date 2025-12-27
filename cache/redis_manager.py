"""
Redis cache manager for fast lookups
"""
import redis
import json
import os
from typing import Optional, Any, Dict
from datetime import timedelta


class RedisCache:
    """Redis cache manager with automatic JSON serialization"""
    
    def __init__(self, host: str = None, port: int = None, db: int = 0):
        """
        Initialize Redis connection
        
        Args:
            host: Redis host (default: localhost or REDIS_HOST env var)
            port: Redis port (default: 6379 or REDIS_PORT env var)
            db: Redis database number (default: 0)
        """
        self.host = host or os.getenv('REDIS_HOST', 'localhost')
        self.port = int(port or os.getenv('REDIS_PORT', 6379))
        self.db = db
        
        # Create Redis client
        self.client = redis.Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            decode_responses=True,  # Automatically decode bytes to strings
            socket_connect_timeout=5,
            socket_keepalive=True,
            health_check_interval=30
        )
        
        # Test connection
        try:
            self.client.ping()
            print(f"✓ Redis connected: {self.host}:{self.port}")
        except redis.ConnectionError as e:
            print(f"✗ Redis connection failed: {e}")
            raise
    
    def set(self, key: str, value: Any, ttl: int = 900) -> bool:
        """
        Set a value in cache with TTL
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds (default: 15 minutes)
        
        Returns:
            True if successful
        """
        try:
            serialized = json.dumps(value)
            return self.client.setex(key, ttl, serialized)
        except Exception as e:
            print(f"Redis SET error for key '{key}': {e}")
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache
        
        Args:
            key: Cache key
        
        Returns:
            Cached value (JSON deserialized) or None if not found
        """
        try:
            value = self.client.get(key)
            if value is None:
                return None
            return json.loads(value)
        except Exception as e:
            print(f"Redis GET error for key '{key}': {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """
        Delete a key from cache
        
        Args:
            key: Cache key
        
        Returns:
            True if key was deleted
        """
        try:
            return self.client.delete(key) > 0
        except Exception as e:
            print(f"Redis DELETE error for key '{key}': {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern
        
        Args:
            pattern: Key pattern (e.g., 'chromebook:*')
        
        Returns:
            Number of keys deleted
        """
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            print(f"Redis DELETE PATTERN error for pattern '{pattern}': {e}")
            return 0
    
    def exists(self, key: str) -> bool:
        """
        Check if a key exists in cache
        
        Args:
            key: Cache key
        
        Returns:
            True if key exists
        """
        try:
            return self.client.exists(key) > 0
        except Exception as e:
            print(f"Redis EXISTS error for key '{key}': {e}")
            return False
    
    def get_ttl(self, key: str) -> int:
        """
        Get remaining TTL for a key
        
        Args:
            key: Cache key
        
        Returns:
            Remaining seconds (-2 if key doesn't exist, -1 if no expiry)
        """
        try:
            return self.client.ttl(key)
        except Exception as e:
            print(f"Redis TTL error for key '{key}': {e}")
            return -2
    
    def increment(self, key: str, amount: int = 1) -> int:
        """
        Increment a counter
        
        Args:
            key: Cache key
            amount: Amount to increment by
        
        Returns:
            New value after increment
        """
        try:
            return self.client.incrby(key, amount)
        except Exception as e:
            print(f"Redis INCR error for key '{key}': {e}")
            return 0
    
    def set_hash(self, hash_key: str, field: str, value: Any, ttl: int = None) -> bool:
        """
        Set a field in a Redis hash
        
        Args:
            hash_key: Hash key
            field: Field name
            value: Value to set
            ttl: Optional TTL for the entire hash
        
        Returns:
            True if successful
        """
        try:
            serialized = json.dumps(value)
            result = self.client.hset(hash_key, field, serialized)
            if ttl:
                self.client.expire(hash_key, ttl)
            return result
        except Exception as e:
            print(f"Redis HSET error for hash '{hash_key}' field '{field}': {e}")
            return False
    
    def get_hash(self, hash_key: str, field: str) -> Optional[Any]:
        """
        Get a field from a Redis hash
        
        Args:
            hash_key: Hash key
            field: Field name
        
        Returns:
            Field value (JSON deserialized) or None
        """
        try:
            value = self.client.hget(hash_key, field)
            if value is None:
                return None
            return json.loads(value)
        except Exception as e:
            print(f"Redis HGET error for hash '{hash_key}' field '{field}': {e}")
            return None
    
    def get_all_hash(self, hash_key: str) -> Dict[str, Any]:
        """
        Get all fields from a Redis hash
        
        Args:
            hash_key: Hash key
        
        Returns:
            Dictionary of all fields (values JSON deserialized)
        """
        try:
            hash_data = self.client.hgetall(hash_key)
            return {k: json.loads(v) for k, v in hash_data.items()}
        except Exception as e:
            print(f"Redis HGETALL error for hash '{hash_key}': {e}")
            return {}
    
    def clear_all(self) -> bool:
        """
        Clear all keys in the current database (USE WITH CAUTION!)
        
        Returns:
            True if successful
        """
        try:
            self.client.flushdb()
            print(f"✓ Redis database {self.db} cleared")
            return True
        except Exception as e:
            print(f"Redis FLUSHDB error: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get Redis statistics
        
        Returns:
            Dictionary with Redis info
        """
        try:
            info = self.client.info()
            return {
                'connected_clients': info.get('connected_clients', 0),
                'used_memory_human': info.get('used_memory_human', '0'),
                'total_keys': self.client.dbsize(),
                'uptime_seconds': info.get('uptime_in_seconds', 0),
                'hit_rate': self._calculate_hit_rate(info)
            }
        except Exception as e:
            print(f"Redis INFO error: {e}")
            return {}
    
    def _calculate_hit_rate(self, info: Dict) -> float:
        """Calculate cache hit rate percentage"""
        hits = info.get('keyspace_hits', 0)
        misses = info.get('keyspace_misses', 0)
        total = hits + misses
        if total == 0:
            return 0.0
        return round((hits / total) * 100, 2)
    
    def close(self):
        """Close Redis connection"""
        try:
            self.client.close()
            print("✓ Redis connection closed")
        except Exception as e:
            print(f"Redis close error: {e}")


# Global Redis instance
cache = RedisCache()


# Cache key generators
class CacheKeys:
    """Cache key naming conventions"""
    
    @staticmethod
    def chromebook_by_serial(serial: str) -> str:
        return f"chromebook:serial:{serial.upper()}"
    
    @staticmethod
    def chromebook_by_asset(asset: str) -> str:
        return f"chromebook:asset:{asset.upper()}"
    
    @staticmethod
    def user_by_email(email: str) -> str:
        return f"user:email:{email.lower()}"
    
    @staticmethod
    def user_devices(email: str) -> str:
        return f"user:devices:{email.lower()}"
    
    @staticmethod
    def search_results(query: str) -> str:
        return f"search:{query.lower()}"
    
    @staticmethod
    def sync_status() -> str:
        return "sync:status"

    @staticmethod
    def sync_lock(sync_type: str) -> str:
        return f"sync:lock:{sync_type}"

    # Report cache keys
    @staticmethod
    def report_summary() -> str:
        return "report:summary"

    @staticmethod
    def report_ghost() -> str:
        return "report:ghost"

    @staticmethod
    def report_os_compliance() -> str:
        return "report:os_compliance"

    @staticmethod
    def report_ou_breakdown() -> str:
        return "report:ou_breakdown"

    @staticmethod
    def report_battery_health(threshold: int = 30) -> str:
        return f"report:battery_health:{threshold}"

    @staticmethod
    def report_aue_status() -> str:
        return "report:aue_status"

    @staticmethod
    def dashboard_aue_expiration() -> str:
        return "dashboard:aue_expiration"

    @staticmethod
    def dashboard_security_alerts() -> str:
        return "dashboard:security_alerts"

    @staticmethod
    def report_aue_year(year: str) -> str:
        return f"report:aue_year:{year}"

    @staticmethod
    def report_model_details(model: str) -> str:
        return f"report:model:{model}"

    @staticmethod
    def invalidate_all_reports() -> str:
        return "report:*"

    # IIQ (IncidentIQ) cache keys
    @staticmethod
    def iiq_asset_dump() -> str:
        """Full asset dump cache (updated every 24 hours)"""
        return "iiq:assets:dump"

    @staticmethod
    def iiq_asset_search(query: str) -> str:
        """Asset search query cache (5-minute dedup)"""
        return f"iiq:assets:search:{query.lower()}"

    @staticmethod
    def iiq_fee_endpoint() -> str:
        """Cached successful fee endpoint URL"""
        return "iiq:fee:endpoint"

    @staticmethod
    def iiq_user_fees(user_id: str) -> str:
        """User fee balance cache (5-minute dedup)"""
        return f"iiq:fees:user:{user_id}"
