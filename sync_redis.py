#!/usr/bin/env python3
"""
Redis Data Sync Script
Syncs case data from remote Redis (34.66.128.83) to local Redis
"""

import redis
import json
import logging
import time
from typing import List, Dict
import argparse
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RedisSync:
    def __init__(self, remote_host='34.66.128.83', local_host='localhost', 
                 remote_port=6379, local_port=6379):
        """Initialize Redis connections"""
        self.remote_redis = redis.Redis(
            host=remote_host, 
            port=remote_port, 
            decode_responses=True,
            socket_connect_timeout=10,
            socket_timeout=10
        )
        self.local_redis = redis.Redis(
            host=local_host, 
            port=local_port, 
            decode_responses=True
        )
        
    def test_connections(self) -> bool:
        """Test both Redis connections"""
        try:
            remote_ping = self.remote_redis.ping()
            local_ping = self.local_redis.ping()
            logger.info(f"Remote Redis: {'✅ Connected' if remote_ping else '❌ Failed'}")
            logger.info(f"Local Redis: {'✅ Connected' if local_ping else '❌ Failed'}")
            return remote_ping and local_ping
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def get_case_keys(self) -> List[str]:
        """Get all case-related keys from remote Redis"""
        try:
            patterns = [
                'case_id:*',
                'case:*', 
                'investigation:*',
                'alert_id:*'
            ]
            
            all_keys = []
            for pattern in patterns:
                keys = self.remote_redis.keys(pattern)
                all_keys.extend(keys)
                logger.info(f"Found {len(keys)} keys matching pattern: {pattern}")
            
            # Remove duplicates
            unique_keys = list(set(all_keys))
            logger.info(f"Total unique case keys: {len(unique_keys)}")
            return unique_keys
            
        except Exception as e:
            logger.error(f"Failed to get case keys: {e}")
            return []
    
    def sync_key(self, key: str) -> bool:
        """Sync a single key from remote to local"""
        try:
            # Get data from remote
            data = self.remote_redis.get(key)
            if data is None:
                logger.warning(f"Key {key} not found in remote Redis")
                return False
            
            # Set data in local Redis
            self.local_redis.set(key, data)
            
            # Verify the sync
            local_data = self.local_redis.get(key)
            if local_data == data:
                logger.debug(f"✅ Synced key: {key}")
                return True
            else:
                logger.error(f"❌ Sync verification failed for key: {key}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to sync key {key}: {e}")
            return False
    
    def sync_all_cases(self) -> Dict[str, int]:
        """Sync all case data from remote to local"""
        logger.info("Starting Redis sync operation...")
        start_time = time.time()
        
        # Get all case keys
        case_keys = self.get_case_keys()
        if not case_keys:
            logger.warning("No case keys found to sync")
            return {"total": 0, "success": 0, "failed": 0}
        
        # Sync each key
        success_count = 0
        failed_count = 0
        
        for key in case_keys:
            if self.sync_key(key):
                success_count += 1
            else:
                failed_count += 1
        
        duration = time.time() - start_time
        
        result = {
            "total": len(case_keys),
            "success": success_count,
            "failed": failed_count,
            "duration_seconds": duration
        }
        
        logger.info(f"Sync completed: {success_count}/{len(case_keys)} keys synced in {duration:.2f}s")
        
        if failed_count > 0:
            logger.warning(f"Failed to sync {failed_count} keys")
        
        return result
    
    def get_sync_stats(self) -> Dict:
        """Get statistics about local Redis case data"""
        try:
            case_patterns = ['case_id:*', 'case:*', 'investigation:*', 'alert_id:*']
            stats = {}
            
            for pattern in case_patterns:
                keys = self.local_redis.keys(pattern)
                stats[pattern] = len(keys)
            
            stats['total_keys'] = sum(stats.values())
            stats['timestamp'] = datetime.now().isoformat()
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get sync stats: {e}")
            return {}
    
    def continuous_sync(self, interval_seconds: int = 300):
        """Run continuous sync every interval_seconds"""
        logger.info(f"Starting continuous sync every {interval_seconds} seconds...")
        
        while True:
            try:
                result = self.sync_all_cases()
                logger.info(f"Periodic sync: {result['success']}/{result['total']} keys synced")
                
                # Log stats
                stats = self.get_sync_stats()
                logger.info(f"Local Redis stats: {stats}")
                
            except KeyboardInterrupt:
                logger.info("Sync interrupted by user")
                break
            except Exception as e:
                logger.error(f"Sync error: {e}")
            
            logger.info(f"Waiting {interval_seconds} seconds until next sync...")
            time.sleep(interval_seconds)

def main():
    parser = argparse.ArgumentParser(description='Sync Redis case data')
    parser.add_argument('--remote-host', default='34.66.128.83', 
                       help='Remote Redis host')
    parser.add_argument('--local-host', default='localhost', 
                       help='Local Redis host')
    parser.add_argument('--continuous', action='store_true',
                       help='Run continuous sync')
    parser.add_argument('--interval', type=int, default=300,
                       help='Sync interval in seconds (default: 300)')
    parser.add_argument('--test', action='store_true',
                       help='Test connections only')
    
    args = parser.parse_args()
    
    # Initialize sync
    sync = RedisSync(
        remote_host=args.remote_host,
        local_host=args.local_host
    )
    
    # Test connections
    if not sync.test_connections():
        logger.error("Connection test failed, exiting")
        return 1
    
    if args.test:
        logger.info("Connection test passed")
        return 0
    
    if args.continuous:
        sync.continuous_sync(args.interval)
    else:
        result = sync.sync_all_cases()
        logger.info(f"One-time sync completed: {result}")
        
        # Show local stats
        stats = sync.get_sync_stats()
        logger.info(f"Local Redis case data: {stats}")
    
    return 0

if __name__ == "__main__":
    exit(main())