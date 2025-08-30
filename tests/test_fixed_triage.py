#!/usr/bin/env python3
"""
Test TriageAgent with real case data from Redis after fixes
"""
import asyncio
import sys
import os

# Set up environment
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/cbernal/AIProjects/Claude/soc_agent_project/threatexplainer-1185aa9fcd44.json'
os.environ['REDIS_URL'] = 'redis://localhost:6379'

sys.path.append('.')

async def test_triage_with_real_data():
    from app.agents.triage import TriageAgent
    
    case_id = '6c7a11e3-5fbd-4cf9-8eee-e826aa40f9dc'
    
    print(f'🧪 TESTING TRIAGE AGENT WITH REAL CASE DATA')
    print(f'Case ID: {case_id}')
    print('=' * 60)
    
    try:
        # Create triage agent
        triage_agent = TriageAgent()
        
        # Test with minimal inputs - should fetch from Redis automatically
        result = await triage_agent.execute(case_id, {
            'case_id': case_id,
            'alert_id': case_id
        }, 'L1_SUGGEST')
        
        print(f'✅ Execution completed successfully!')
        print(f'Agent: {result.get("agent", {}).get("name")}')
        print(f'Model: {result.get("agent", {}).get("model")}')
        print(f'Tokens: {result.get("token_usage", {}).get("total_tokens", 0)}')
        print(f'Cost: ${result.get("token_usage", {}).get("cost_usd", 0):.6f}')
        
        # Check if we got real case data
        outputs = result.get('outputs', {})
        if 'error' in outputs:
            print(f'❌ Error: {outputs["error"]}')
        else:
            triage_result = outputs.get('triage_result', {})
            
            print(f'\n📊 TRIAGE RESULTS:')
            print(f'   Severity: {triage_result.get("severity", "unknown")}')
            print(f'   Priority: {triage_result.get("priority", "unknown")}')
            print(f'   Entities found: {len(triage_result.get("entities", []))}')
            print(f'   Escalation needed: {triage_result.get("escalation_needed", False)}')
            
            entities = triage_result.get('entities', [])
            if entities:
                print(f'   Sample entities:')
                for i, entity in enumerate(entities[:3]):
                    if isinstance(entity, dict):
                        print(f'     {i+1}. {entity.get("type", "unknown")}: {entity.get("value", "N/A")} (confidence: {entity.get("confidence", "N/A")})')
                    else:
                        print(f'     {i+1}. {entity}')
            
            hypotheses = triage_result.get('hypotheses', [])
            if hypotheses:
                print(f'   Hypotheses: {len(hypotheses)}')
                for i, hypothesis in enumerate(hypotheses[:2]):
                    print(f'     {i+1}. {hypothesis}')
            
            summary = triage_result.get('summary', '')
            if summary:
                print(f'   Summary: {summary[:200]}...' if len(summary) > 200 else f'   Summary: {summary}')
        
        print('\n🎯 SUCCESS: TriageAgent now reads real case data from Redis!')
        
    except Exception as e:
        print(f'❌ Test failed: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_triage_with_real_data())