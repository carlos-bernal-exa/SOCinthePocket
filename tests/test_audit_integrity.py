#!/usr/bin/env python3
"""
Test audit system integrity with hash chains and signatures
"""
import asyncio
import logging
from app.services.audit import audit_logger

logging.basicConfig(level=logging.INFO)

async def test_audit_integrity():
    """Test audit system hash chains and Ed25519 signatures"""
    print("🔒 Testing Audit System Integrity")
    print("=" * 50)
    
    try:
        case_id = "test-audit-integrity-001"
        
        # Create a sequence of audit steps
        steps = [
            {
                "version": "1.0",
                "case_id": case_id,
                "agent": {"name": "TestAgent", "role": "test", "model": "gemini-2.5-flash"},
                "prompt_version": "TestAgent_v1.0",
                "autonomy_level": "L1_SUGGEST",
                "inputs": {"test": "data1"},
                "plan": ["step1", "step2"],
                "observations": ["obs1"],
                "outputs": {"result": "output1"},
                "token_usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150, "cost_usd": 0.001}
            },
            {
                "version": "1.0",
                "case_id": case_id,
                "agent": {"name": "TestAgent2", "role": "test", "model": "gemini-2.5-pro"},
                "prompt_version": "TestAgent2_v1.1", 
                "autonomy_level": "L2_APPROVE",
                "inputs": {"test": "data2"},
                "plan": ["step3", "step4"],
                "observations": ["obs2", "obs3"],
                "outputs": {"result": "output2"},
                "token_usage": {"input_tokens": 200, "output_tokens": 75, "total_tokens": 275, "cost_usd": 0.002}
            },
            {
                "version": "1.0",
                "case_id": case_id,
                "agent": {"name": "TestAgent3", "role": "test", "model": "gemini-2.5-flash-lite"},
                "prompt_version": "TestAgent3_v2.0",
                "autonomy_level": "L3_AUTO", 
                "inputs": {"test": "data3"},
                "plan": ["step5"],
                "observations": ["obs4", "obs5", "obs6"],
                "outputs": {"result": "output3"},
                "token_usage": {"input_tokens": 50, "output_tokens": 25, "total_tokens": 75, "cost_usd": 0.0005}
            }
        ]
        
        print("📊 Creating audit steps...")
        created_steps = []
        for i, step_data in enumerate(steps):
            print(f"   Step {i+1}: {step_data['agent']['name']}")
            step = await audit_logger.append(step_data)
            created_steps.append(step)
            
            print(f"     Step ID: {step.step_id}")
            print(f"     Hash: {step.hash[:16]}...")
            print(f"     Prev Hash: {step.prev_hash[:16] + '...' if step.prev_hash else 'None'}")
            print(f"     Signature: {'Yes' if step.signature else 'No'}")
        
        print(f"\n✅ Created {len(created_steps)} audit steps")
        
        # Verify integrity
        print("\n🔍 Verifying audit chain integrity...")
        integrity_result = await audit_logger.verify_integrity(case_id)
        
        print(f"   Valid: {integrity_result['valid']}")
        print(f"   Total steps: {integrity_result['total_steps']}")
        print(f"   Verified steps: {integrity_result['verified_steps']}")
        
        if integrity_result['errors']:
            print("   Errors:")
            for error in integrity_result['errors']:
                print(f"     - {error}")
        else:
            print("   ✅ No errors found")
        
        # Test case summary
        print(f"\n📈 Getting case summary...")
        summary = await audit_logger.get_case_summary(case_id)
        
        print(f"   Case ID: {summary['case_id']}")
        print(f"   Total steps: {summary['total_steps']}")
        print(f"   Total cost: ${summary['total_cost_usd']:.6f}")
        print(f"   Total tokens: {summary['total_tokens']}")
        print(f"   Agents used: {summary['agents_used']}")
        print(f"   Duration: {summary.get('first_step')} -> {summary.get('last_step')}")
        
        # Demonstrate hash chain properties
        print(f"\n🔗 Hash Chain Analysis:")
        for i, step in enumerate(created_steps):
            print(f"   Step {i+1}: {step.agent.name}")
            print(f"     Current hash: {step.hash}")
            print(f"     Previous hash: {step.prev_hash or 'Genesis'}")
            
            if i > 0:
                expected_prev = created_steps[i-1].hash
                if step.prev_hash == expected_prev:
                    print(f"     ✅ Hash chain intact")
                else:
                    print(f"     ❌ Hash chain broken!")
        
        print(f"\n🎉 Audit integrity test completed!")
        return integrity_result['valid']
        
    except Exception as e:
        print(f"❌ Audit integrity test failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_audit_integrity())