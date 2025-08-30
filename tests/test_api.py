#!/usr/bin/env python3
"""
Test script for SOC Platform API endpoints
"""

import requests
import json
import time
from typing import Dict, Any

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("🔍 Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200

def test_case_enrichment():
    """Test case enrichment endpoint with sample data"""
    print("\n🔍 Testing case enrichment...")
    
    payload = {
        "case_id": "test-case-123",
        "autonomy_level": "supervised",
        "max_depth": 2,
        "include_raw_logs": True
    }
    
    print(f"Sending request to: {BASE_URL}/cases/test-case-123/enrich")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/cases/test-case-123/enrich",
            json=payload,
            timeout=60
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Case enrichment successful!")
            print(f"   - Case ID: {result.get('case_id')}")
            print(f"   - Status: {result.get('status')}")
            print(f"   - Entities found: {len(result.get('entities', []))}")
            print(f"   - Related cases: {len(result.get('related_cases', []))}")
            print(f"   - Total cost: ${result.get('total_cost_usd', 0):.6f}")
            print(f"   - Total tokens: {result.get('total_tokens', 0)}")
            print(f"   - Audit steps: {len(result.get('audit_trail', []))}")
            return True
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False

def test_audit_endpoints():
    """Test audit-related endpoints"""
    print("\n🔍 Testing audit endpoints...")
    success = True
    
    # Test getting case audit
    response = requests.get(f"{BASE_URL}/audit/test-case-123")
    print(f"Get audit status: {response.status_code}")
    if response.status_code != 200:
        success = False
    
    # Test integrity verification
    response = requests.get(f"{BASE_URL}/audit/verify/test-case-123")
    print(f"Verify integrity status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"   - Integrity valid: {result.get('integrity_valid')}")
    else:
        success = False
    
    return success

def test_knowledge_endpoints():
    """Test knowledge management endpoints"""
    print("\n🔍 Testing knowledge endpoints...")
    success = True
    
    # Test knowledge ingestion
    knowledge_data = {
        "title": "Test Threat Intelligence",
        "content": "Sample threat intelligence about APT group tactics",
        "type": "threat_intel",
        "tags": ["apt", "malware", "c2"]
    }
    
    response = requests.post(f"{BASE_URL}/knowledge/ingest", json=knowledge_data)
    print(f"Knowledge ingest status: {response.status_code}")
    if response.status_code != 200:
        success = False
    
    # Test knowledge search
    response = requests.get(f"{BASE_URL}/knowledge/search?query=apt&limit=5")
    print(f"Knowledge search status: {response.status_code}")
    if response.status_code != 200:
        success = False
    
    return success

def test_prompt_endpoints():
    """Test prompt management endpoints"""
    print("\n🔍 Testing prompt endpoints...")
    
    # Test getting a prompt
    response = requests.get(f"{BASE_URL}/prompts/TriageAgent")
    print(f"Get prompt status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"   - Agent: {result.get('agent')}")
        print(f"   - Prompt length: {len(result.get('prompt', {}).get('content', ''))}")
        return True
    else:
        return False

def test_stats():
    """Test platform statistics"""
    print("\n🔍 Testing platform stats...")
    response = requests.get(f"{BASE_URL}/stats")
    print(f"Stats status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"   - Platform statistics retrieved")
        return True
    else:
        return False

def wait_for_service(max_attempts=30):
    """Wait for the service to be ready"""
    print(f"⏳ Waiting for SOC platform to be ready...")
    
    for attempt in range(max_attempts):
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            if response.status_code == 200:
                print(f"✅ SOC platform is ready!")
                return True
        except requests.exceptions.RequestException:
            pass
        
        print(f"   Attempt {attempt + 1}/{max_attempts} - waiting...")
        time.sleep(2)
    
    print(f"❌ SOC platform not ready after {max_attempts} attempts")
    return False

def main():
    """Run all tests"""
    print("🚀 SOC Platform API Testing Suite")
    print("=" * 50)
    
    if not wait_for_service():
        print("❌ Service not available, exiting...")
        return False
    
    tests = [
        ("Health Check", test_health),
        ("Case Enrichment", test_case_enrichment),
        ("Audit Endpoints", test_audit_endpoints),
        ("Knowledge Endpoints", test_knowledge_endpoints),
        ("Prompt Endpoints", test_prompt_endpoints),
        ("Platform Stats", test_stats),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with error: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} - {test_name}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! SOC platform is ready for use.")
        return True
    else:
        print("⚠️  Some tests failed. Check the logs for details.")
        return False

if __name__ == "__main__":
    main()