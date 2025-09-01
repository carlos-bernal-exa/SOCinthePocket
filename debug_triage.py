#!/usr/bin/env python3

import asyncio
import json
import sys
import os

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from agents.triage import TriageAgent

async def debug_triage():
    """Debug what happens in TriageAgent"""
    
    case_id = "94331c9d-336a-49fd-9210-97b3c6ee2624"
    
    # Initialize TriageAgent
    agent = TriageAgent()
    
    try:
        print(f"Testing TriageAgent execution for: {case_id}")
        
        # Test with empty case_data (should trigger Redis fetch)
        inputs = {
            "case_id": case_id,
            "case_data": {},
            "autonomy_level": "supervised"
        }
        
        result = await agent.execute(case_id, inputs, "supervised")
        
        print("✅ Agent execution completed")
        print(f"📊 Result keys: {list(result.keys())}")
        
        if "outputs" in result:
            outputs = result["outputs"]
            print(f"📋 Outputs keys: {list(outputs.keys())}")
            
            if "triage_result" in outputs:
                triage = outputs["triage_result"]
                print(f"🎯 Triage result: {triage}")
                
            if "raw_analysis" in outputs:
                analysis = outputs["raw_analysis"]
                print(f"📄 Raw analysis: {analysis[:200]}...")
        
        # Check if it was mock mode
        if result.get("outputs", {}).get("raw_response", {}).get("mock_mode"):
            print("❌ STILL IN MOCK MODE")
        else:
            print("✅ REAL DATA PROCESSING")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if hasattr(agent, 'redis_store') and hasattr(agent.redis_store, 'client') and agent.redis_store.client:
            await agent.redis_store.client.aclose()

if __name__ == "__main__":
    asyncio.run(debug_triage())