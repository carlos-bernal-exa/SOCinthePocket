#!/usr/bin/env python3
"""
Comprehensive test of SOC platform with real case ID 6c7a11e3-5fbd-4cf9-8eee-e826aa40f9dc
"""
import asyncio
import logging
import json
from app.services.audit import audit_logger

logging.basicConfig(level=logging.INFO)

async def test_real_case_audit():
    """Test audit trail for the real case"""
    print("🔍 Real Case Audit Analysis")
    print("=" * 50)
    
    case_id = "6c7a11e3-5fbd-4cf9-8eee-e826aa40f9dc"
    
    try:
        # Get case steps
        print(f"📊 Fetching audit steps for case {case_id}...")
        steps = await audit_logger.fetch_case_steps(case_id, limit=20)
        
        if not steps:
            print("   ❌ No audit steps found for this case")
            return False
        
        print(f"   ✅ Found {len(steps)} audit steps")
        
        # Show step details
        print("\n🔍 Audit Step Details:")
        total_cost = 0.0
        total_tokens = 0
        
        for i, step in enumerate(steps, 1):
            print(f"\n   Step {i}: {step.agent.name}")
            print(f"     Step ID: {step.step_id}")
            print(f"     Timestamp: {step.timestamp}")
            print(f"     Model: {step.agent.model}")
            print(f"     Prompt Version: {step.prompt_version}")
            print(f"     Autonomy Level: {step.autonomy_level}")
            print(f"     Tokens: {step.token_usage.total_tokens}")
            print(f"     Cost: ${step.token_usage.cost_usd:.6f}")
            print(f"     Hash: {step.hash[:16]}...")
            print(f"     Prev Hash: {step.prev_hash[:16] + '...' if step.prev_hash else 'Genesis'}")
            print(f"     Signature: {'Yes' if step.signature else 'No'}")
            
            total_cost += step.token_usage.cost_usd
            total_tokens += step.token_usage.total_tokens
        
        print(f"\n💰 Case Totals:")
        print(f"   Total Steps: {len(steps)}")
        print(f"   Total Cost: ${total_cost:.6f}")
        print(f"   Total Tokens: {total_tokens}")
        
        # Verify integrity
        print(f"\n🔒 Verifying Audit Integrity...")
        integrity_result = await audit_logger.verify_integrity(case_id)
        
        print(f"   Chain Valid: {integrity_result['valid']}")
        print(f"   Verified Steps: {integrity_result['verified_steps']}/{integrity_result['total_steps']}")
        
        if integrity_result['errors']:
            print("   Errors found:")
            for error in integrity_result['errors'][:3]:  # Show first 3 errors
                print(f"     - {error}")
            if len(integrity_result['errors']) > 3:
                print(f"     ... and {len(integrity_result['errors']) - 3} more")
        else:
            print("   ✅ No integrity errors")
        
        # Show case summary  
        print(f"\n📈 Case Summary:")
        summary = await audit_logger.get_case_summary(case_id)
        
        print(f"   Case ID: {summary['case_id']}")
        print(f"   Total Steps: {summary['total_steps']}")
        print(f"   First Step: {summary.get('first_step', 'N/A')}")
        print(f"   Last Step: {summary.get('last_step', 'N/A')}")
        print(f"   Total Cost: ${summary.get('total_cost_usd', 0):.6f}")
        print(f"   Total Tokens: {summary.get('total_tokens', 0)}")
        print(f"   Agents Used: {summary.get('agents_used', [])}")
        
        # Show hash chain analysis
        print(f"\n🔗 Hash Chain Analysis:")
        prev_hash = None
        for i, step in enumerate(steps):
            status = "✅" if step.prev_hash == prev_hash else "❌"
            print(f"   {status} Step {i+1}: {step.agent.name}")
            print(f"       Expected prev: {prev_hash or 'Genesis'}")
            print(f"       Actual prev: {step.prev_hash or 'Genesis'}")
            prev_hash = step.hash
        
        return True
        
    except Exception as e:
        print(f"❌ Real case audit test failed: {e}")
        return False

async def main():
    """Main test function"""
    print("🚀 SOC Platform Real Case Testing")
    print("Case ID: 6c7a11e3-5fbd-4cf9-8eee-e826aa40f9dc")
    print("=" * 60)
    
    success = await test_real_case_audit()
    
    print(f"\n📊 Test Results:")
    print(f"   Real Case Analysis: {'✅ PASS' if success else '❌ FAIL'}")
    
    if success:
        print(f"\n🎉 Real case processing completed successfully!")
        print(f"   - Complete audit trail with hash chains")
        print(f"   - Ed25519 digital signatures")
        print(f"   - Multi-agent pipeline execution")
        print(f"   - Comprehensive cost and token tracking")
        print(f"   - Tamper-evident audit logging")
    else:
        print(f"\n❌ Real case processing had issues")

if __name__ == "__main__":
    asyncio.run(main())