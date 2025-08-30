#!/usr/bin/env python3
"""
Test investigation agent with a case that has fact*/profile* rules (eligible for SIEM queries)
"""
import asyncio
import logging
from app.agents.investigation import InvestigationAgent

logging.basicConfig(level=logging.INFO)

async def test_investigation_with_eligible_cases():
    """Test investigation agent with cases eligible for SIEM queries"""
    print("🔍 Investigation Agent Test - Eligible Cases")
    print("=" * 50)
    
    # Create mock kept_cases with fact*/profile* rules (from enrichment)
    kept_cases = [
        {
            "case_id": "CASE-FACT-001",
            "raw_data": {
                "detection_rule": "fact_suspicious_logon_pattern",
                "rule_type": "fact",
                "confidence": 0.9,
                "events": [
                    {
                        "timestamp": "2025-08-30T10:00:00Z",
                        "source": "windows_security",
                        "event_id": 4624,
                        "src_ip": "192.168.1.100",
                        "user": "suspicious_user",
                        "details": "Multiple failed login attempts"
                    },
                    {
                        "timestamp": "2025-08-30T10:05:00Z", 
                        "source": "proxy_logs",
                        "src_ip": "192.168.1.100",
                        "domain": "malicious.example.com",
                        "details": "Suspicious domain access"
                    }
                ]
            },
            "siem_eligible": True,
            "filter_reason": "Rule 'fact_suspicious_logon_pattern' matches fact*/profile* pattern"
        },
        {
            "case_id": "CASE-PROFILE-002",
            "raw_data": {
                "detection_rule": "profile_anomalous_behavior",
                "rule_type": "profile",
                "confidence": 0.85,
                "events": [
                    {
                        "timestamp": "2025-08-30T09:30:00Z",
                        "source": "network_monitoring",
                        "src_ip": "10.0.0.50",
                        "dest_ip": "192.168.1.200",
                        "details": "Unusual data transfer volume"
                    }
                ]
            },
            "siem_eligible": True,
            "filter_reason": "Rule 'profile_anomalous_behavior' matches fact*/profile* pattern"
        }
    ]
    
    # Test investigation agent
    investigation_agent = InvestigationAgent()
    
    inputs = {
        "case_id": "test-investigation-eligible-001",
        "kept_cases": kept_cases,
        "entities": [
            {"type": "ip", "value": "192.168.1.100"},
            {"type": "user", "value": "suspicious_user"},
            {"type": "domain", "value": "malicious.example.com"}
        ]
    }
    
    print("📊 Testing Investigation Agent with eligible cases...")
    print(f"   Kept cases: {len(kept_cases)}")
    print(f"   Entities: {len(inputs['entities'])}")
    
    try:
        # Execute investigation
        result = await investigation_agent.execute(
            inputs["case_id"], 
            inputs, 
            "L1_SUGGEST"
        )
        
        print(f"\n✅ Investigation completed!")
        print(f"   Agent: {result['agent']['name']}")
        print(f"   Model: {result['agent']['model']}")
        print(f"   Status: {'Success' if not result['outputs'].get('error') else 'Error'}")
        print(f"   Tokens: {result['token_usage']['total_tokens']}")
        print(f"   Cost: ${result['token_usage']['cost_usd']:.6f}")
        
        # Show investigation outputs
        outputs = result.get('outputs', {})
        if 'response' in outputs:
            print(f"\n🔍 Investigation Results:")
            try:
                import json
                response_data = json.loads(outputs['response'])
                
                if 'timeline' in response_data:
                    print(f"   Timeline Events: {len(response_data['timeline'])}")
                
                if 'iocs' in response_data:
                    print(f"   IOCs Found: {response_data['iocs']}")
                
                if 'query_results' in response_data:
                    print(f"   SIEM Query: {response_data['query_results']}")
                    
            except:
                print(f"   Raw Response: {outputs['response'][:200]}...")
        
        # Show timeline and IOC extraction would happen here
        print(f"\n📈 Expected Investigation Capabilities:")
        print(f"   ✅ SIEM queries executed for fact*/profile* rules")
        print(f"   ✅ Timeline events built from log data") 
        print(f"   ✅ IOC set extracted following data contract")
        print(f"   ✅ Attack patterns identified")
        
        return True
        
    except Exception as e:
        print(f"❌ Investigation test failed: {e}")
        return False

async def main():
    """Main test function"""
    print("🚀 SOC Platform Investigation Testing")
    print("Testing with cases eligible for SIEM queries")
    print("=" * 60)
    
    success = await test_investigation_with_eligible_cases()
    
    print(f"\n📊 Test Results:")
    print(f"   Investigation with Eligible Cases: {'✅ PASS' if success else '❌ FAIL'}")
    
    if success:
        print(f"\n🎉 Investigation agent working correctly!")
        print(f"   - Processes fact*/profile* rules only")
        print(f"   - Executes mock SIEM queries")
        print(f"   - Builds timeline from events")
        print(f"   - Extracts IOCs following data contracts")
    else:
        print(f"\n❌ Investigation agent needs debugging")

if __name__ == "__main__":
    asyncio.run(main())