#!/usr/bin/env python3
"""
Test Neo4j integration with the SOC platform
"""
import asyncio
import logging
import json
from app.adapters.neo4j_store import neo4j_store
from app.agents.triage import TriageAgent
from app.agents.enrichment import EnrichmentAgent
from app.agents.knowledge import KnowledgeAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_neo4j_templates():
    """Test all Neo4j Cypher templates"""
    print("🔍 Testing Neo4j Templates")
    print("=" * 50)
    
    try:
        # Test 1: Case + Rule relationship
        print("📊 Test 1: Creating Case-Rule relationship...")
        case_id = "test-case-neo4j-001"
        rule_id = "fact_suspicious_login_001"
        
        result = await neo4j_store.create_case_rule_relationship(case_id, rule_id)
        if result:
            print(f"   ✅ Case-Rule relationship created: {case_id} -> {rule_id}")
        else:
            print("   ❌ Failed to create Case-Rule relationship")
        
        # Test 2: Observed entities
        print("📊 Test 2: Creating observed entities...")
        entities = [
            ("ip", "192.168.1.100"),
            ("user", "suspicious_user"),
            ("domain", "malicious.example.com"),
            ("hash", "d41d8cd98f00b204e9800998ecf8427e")
        ]
        
        for entity_type, entity_value in entities:
            result = await neo4j_store.create_observed_entity(case_id, entity_type, entity_value)
            if result:
                print(f"   ✅ Observed entity created: {entity_type}:{entity_value}")
            else:
                print(f"   ❌ Failed to create entity: {entity_type}:{entity_value}")
        
        # Test 3: Related cases
        print("📊 Test 3: Creating related cases...")
        related_cases = [
            {"id": "CASE-2023-001", "score": 0.85},
            {"id": "CASE-2023-045", "score": 0.72}
        ]
        
        result = await neo4j_store.create_related_cases(case_id, related_cases)
        if result:
            print(f"   ✅ Related cases created: {len(result)} relationships")
        else:
            print("   ❌ Failed to create related cases")
        
        # Test 4: Knowledge items
        print("📊 Test 4: Creating knowledge item...")
        knowledge_id = "know_test_neo4j"
        result = await neo4j_store.create_knowledge_item(
            knowledge_id=knowledge_id,
            kind="test_knowledge",
            author="neo4j_test",
            created_at="2025-08-30T18:00:00Z",
            text="Test knowledge item for Neo4j integration",
            tags=["test", "neo4j", "integration"],
            trust="high"
        )
        
        if result:
            print(f"   ✅ Knowledge item created: {knowledge_id}")
        else:
            print("   ❌ Failed to create knowledge item")
        
        print("\n🎉 Neo4j template tests completed!")
        return True
        
    except Exception as e:
        print(f"❌ Neo4j test failed: {e}")
        return False

async def test_agent_neo4j_integration():
    """Test agents with Neo4j integration"""
    print("\n🤖 Testing Agent-Neo4j Integration")
    print("=" * 50)
    
    try:
        case_id = "test-agent-neo4j-002"
        
        # Test TriageAgent with Neo4j
        print("📊 Test 1: TriageAgent with Neo4j...")
        triage_agent = TriageAgent()
        triage_inputs = {
            "case_id": case_id,
            "case_data": {
                "severity": "high",
                "description": "Suspicious login activity detected",
                "rule_id": "fact_suspicious_login_002"
            }
        }
        
        triage_result = await triage_agent.execute(case_id, triage_inputs, "L1_SUGGEST")
        if triage_result and not triage_result.get("error"):
            print("   ✅ TriageAgent executed with Neo4j integration")
        else:
            print(f"   ❌ TriageAgent failed: {triage_result.get('error', 'Unknown error')}")
        
        # Test EnrichmentAgent with Neo4j
        print("📊 Test 2: EnrichmentAgent with Neo4j...")
        enrichment_agent = EnrichmentAgent()
        enrichment_inputs = {
            "case_id": case_id,
            "entities": [
                {"type": "ip", "value": "10.0.0.50", "confidence": 0.9},
                {"type": "user", "value": "test_user", "confidence": 0.8}
            ],
            "case_data": {
                "rule_id": "fact_lateral_movement_002"
            }
        }
        
        enrichment_result = await enrichment_agent.execute(case_id, enrichment_inputs, "L1_SUGGEST")
        if enrichment_result and not enrichment_result.get("error"):
            print("   ✅ EnrichmentAgent executed with Neo4j integration")
        else:
            print(f"   ❌ EnrichmentAgent failed: {enrichment_result.get('error', 'Unknown error')}")
        
        # Test KnowledgeAgent with Neo4j
        print("📊 Test 3: KnowledgeAgent with Neo4j...")
        knowledge_agent = KnowledgeAgent()
        knowledge_inputs = {
            "case_id": case_id,
            "operation": "ingest",
            "knowledge_data": {
                "type": "investigation",
                "author": "test_analyst",
                "content": "Test investigation findings for Neo4j integration",
                "tags": ["test", "investigation", "neo4j"]
            }
        }
        
        knowledge_result = await knowledge_agent.execute(case_id, knowledge_inputs, "L1_SUGGEST")
        if knowledge_result and not knowledge_result.get("error"):
            print("   ✅ KnowledgeAgent executed with Neo4j integration")
        else:
            print(f"   ❌ KnowledgeAgent failed: {knowledge_result.get('error', 'Unknown error')}")
        
        print("\n🎉 Agent-Neo4j integration tests completed!")
        return True
        
    except Exception as e:
        print(f"❌ Agent-Neo4j integration test failed: {e}")
        return False

async def main():
    """Main test function"""
    print("🚀 SOC Platform Neo4j Integration Testing")
    print("=" * 60)
    
    # Test Neo4j connection
    print("🔌 Testing Neo4j connection...")
    try:
        await neo4j_store.connect()
        print("   ✅ Neo4j connection established")
    except Exception as e:
        print(f"   ❌ Neo4j connection failed: {e}")
        print("   ℹ️  Make sure Neo4j is running with docker-compose up")
        return
    
    # Run template tests
    template_success = await test_neo4j_templates()
    
    # Run agent integration tests
    agent_success = await test_agent_neo4j_integration()
    
    # Close connection
    await neo4j_store.close()
    
    # Summary
    print("\n📊 Test Results Summary:")
    print(f"   Neo4j Templates: {'✅ PASS' if template_success else '❌ FAIL'}")
    print(f"   Agent Integration: {'✅ PASS' if agent_success else '❌ FAIL'}")
    
    if template_success and agent_success:
        print("\n🎉 All Neo4j integration tests passed!")
    else:
        print("\n❌ Some tests failed. Check Neo4j configuration and logs.")

if __name__ == "__main__":
    asyncio.run(main())