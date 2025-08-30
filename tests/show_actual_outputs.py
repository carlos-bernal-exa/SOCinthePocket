#!/usr/bin/env python3
"""
Show actual agent outputs for case 6c7a11e3-5fbd-4cf9-8eee-e826aa40f9dc
"""
import asyncio
import asyncpg
import json

async def show_actual_outputs():
    conn = await asyncpg.connect('postgresql://soc_user:soc_password@localhost:5432/soc_platform')
    
    case_id = '6c7a11e3-5fbd-4cf9-8eee-e826aa40f9dc'
    
    steps = await conn.fetch('''
        SELECT agent_name, outputs, timestamp FROM audit_steps 
        WHERE case_id = $1
        ORDER BY timestamp
    ''', case_id)
    
    print("🎯 ACTUAL AGENT OUTPUTS FOR CASE", case_id)
    print("=" * 80)
    
    for step in steps:
        agent_name = step['agent_name']
        timestamp = step['timestamp']
        
        if not step['outputs']:
            continue
            
        try:
            outputs = json.loads(step['outputs'])
            
            print(f"\n🤖 {agent_name} - {timestamp}")
            print("-" * 50)
            
            # Show structured response if available
            if 'response' in outputs:
                response = outputs['response']
                
                if isinstance(response, str) and response.startswith('```json'):
                    # Extract JSON from markdown
                    json_start = response.find('{')
                    json_end = response.rfind('}') + 1
                    if json_start != -1 and json_end != -1:
                        try:
                            json_content = response[json_start:json_end]
                            parsed_response = json.loads(json_content)
                            
                            # Show agent-specific structured output
                            if agent_name == 'TriageAgent':
                                entities = parsed_response.get('entities', [])
                                severity = parsed_response.get('severity', 'unknown')
                                print(f"📊 Entities found: {len(entities)}")
                                print(f"📊 Severity: {severity}")
                                if entities:
                                    for i, entity in enumerate(entities[:3]):
                                        print(f"   {i+1}. {entity.get('type', 'N/A')}: {entity.get('value', 'N/A')}")
                            
                            elif agent_name == 'EnrichmentAgent':
                                related_items = parsed_response.get('related_items', [])
                                kept_cases = parsed_response.get('kept_cases', [])
                                skipped_cases = parsed_response.get('skipped_cases', [])
                                print(f"📊 Similar cases found: {len(related_items)}")
                                print(f"📊 Cases kept (fact*/profile*): {len(kept_cases)}")
                                print(f"📊 Cases skipped: {len(skipped_cases)}")
                                
                                if kept_cases:
                                    print("   Kept cases:")
                                    for case in kept_cases[:3]:
                                        print(f"   - {case.get('case_id', 'N/A')}: {case.get('rule_id', 'N/A')}")
                            
                            elif agent_name == 'InvestigationAgent':
                                siem_results = parsed_response.get('siem_results', [])
                                timeline_events = parsed_response.get('timeline_events', [])
                                ioc_set = parsed_response.get('ioc_set', {})
                                attack_patterns = parsed_response.get('attack_patterns', [])
                                
                                print(f"📊 SIEM events found: {len(siem_results)}")
                                print(f"📊 Timeline events: {len(timeline_events)}")
                                print(f"📊 Attack patterns: {len(attack_patterns)}")
                                
                                total_iocs = sum(len(v) if isinstance(v, list) else 0 for v in ioc_set.values())
                                print(f"📊 Total IOCs: {total_iocs}")
                                
                                if siem_results:
                                    print("   Sample SIEM events:")
                                    for i, event in enumerate(siem_results[:3]):
                                        print(f"   {i+1}. {event.get('rule_name', 'N/A')} ({event.get('severity', 'N/A')})")
                                
                                if timeline_events:
                                    print("   Sample timeline:")
                                    for i, event in enumerate(timeline_events[:3]):
                                        print(f"   {i+1}. {event.get('timestamp', 'N/A')}: {event.get('event_type', 'N/A')}")
                            
                            elif agent_name == 'CorrelationAgent':
                                attack_chain = parsed_response.get('attack_chain', [])
                                mitre_tactics = parsed_response.get('mitre_tactics', [])
                                threat_actor = parsed_response.get('threat_actor', 'unknown')
                                print(f"📊 Attack chain steps: {len(attack_chain)}")
                                print(f"📊 MITRE tactics: {len(mitre_tactics)}")
                                print(f"📊 Threat actor: {threat_actor}")
                            
                            elif agent_name == 'ResponseAgent':
                                recommendations = parsed_response.get('recommendations', [])
                                containment_actions = parsed_response.get('containment_actions', [])
                                print(f"📊 Recommendations: {len(recommendations)}")
                                print(f"📊 Containment actions: {len(containment_actions)}")
                                
                                if recommendations:
                                    print("   Top recommendations:")
                                    for i, rec in enumerate(recommendations[:3]):
                                        print(f"   {i+1}. {rec.get('action', 'N/A')} (priority: {rec.get('priority', 'N/A')})")
                            
                            elif agent_name == 'ControllerAgent':
                                if 'execution_plan' in parsed_response:
                                    plan = parsed_response['execution_plan']
                                    print(f"📊 Execution plan created with {len(plan.get('agents', []))} agents")
                                else:
                                    print("📊 Generated phishing investigation workflow")
                        
                        except json.JSONDecodeError:
                            print(f"📄 Response: {response[:200]}...")
                    else:
                        print(f"📄 Response: {response[:200]}...")
                else:
                    print(f"📄 Response: {str(response)[:200]}...")
            
            # Show other output keys
            other_keys = [k for k in outputs.keys() if k != 'response']
            if other_keys:
                print(f"📋 Other outputs: {other_keys}")
                
        except Exception as e:
            print(f"❌ Error parsing outputs: {e}")
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(show_actual_outputs())