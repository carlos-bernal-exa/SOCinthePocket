#!/usr/bin/env python3

import asyncio
import json
import sys
import os

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from adapters.redis_store import RedisStore

async def test_redis_case_retrieval():
    """Test if we can retrieve the case data from Redis"""
    
    case_id = "94331c9d-336a-49fd-9210-97b3c6ee2624"
    
    # Initialize RedisStore
    redis_store = RedisStore()
    
    try:
        # Test get_summary method
        print(f"Testing case retrieval for: {case_id}")
        
        case_data = await redis_store.get_summary(case_id)
        
        if case_data and case_data.get("case_id") != "unknown":
            print("✅ SUCCESS: Real case data retrieved!")
            print("\n📋 Case Summary:")
            print(f"Case ID: {case_data.get('case_id')}")
            print(f"Title: {case_data.get('title')}")
            print(f"Description: {case_data.get('description')[:100]}...")
            print(f"Severity: {case_data.get('severity')}")
            print(f"Status: {case_data.get('status')}")
            
            print(f"\n🔍 Entities Found:")
            entities = case_data.get('entities', {})
            for entity_type, entity_list in entities.items():
                if entity_list:
                    print(f"  {entity_type}: {entity_list}")
            
            print(f"\n📊 Detections:")
            detections = case_data.get('detections', [])
            for i, detection in enumerate(detections, 1):
                print(f"  {i}. {detection.get('description', 'No description')}")
                
            return True
        else:
            print("❌ FAILED: Still returning mock data")
            print(f"Case data: {case_data}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False
    finally:
        if redis_store.client:
            await redis_store.client.close()

if __name__ == "__main__":
    success = asyncio.run(test_redis_case_retrieval())
    sys.exit(0 if success else 1)