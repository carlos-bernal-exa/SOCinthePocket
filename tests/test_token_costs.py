#!/usr/bin/env python3
"""
Test token cost calculations for all Gemini models
"""
import asyncio
import logging
from app.services.vertex import vertex_service, MODEL_PRICING

logging.basicConfig(level=logging.INFO)

async def test_model_pricing():
    """Test pricing for all three Gemini models"""
    print("🧮 Testing Gemini Model Pricing")
    print("=" * 40)
    
    models = ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite"]
    test_prompt = "Analyze this security incident and provide recommendations for investigation."
    
    for model in models:
        print(f"📊 Testing {model}...")
        
        try:
            response, token_usage = await vertex_service.run_gemini(
                model=model,
                prompt=test_prompt,
                agent_name="TestAgent"
            )
            
            input_tokens = token_usage["input_tokens"]
            output_tokens = token_usage["output_tokens"]
            total_tokens = token_usage["total_tokens"]
            cost_usd = token_usage["cost_usd"]
            
            print(f"   Input tokens: {input_tokens}")
            print(f"   Output tokens: {output_tokens}")
            print(f"   Total tokens: {total_tokens}")
            print(f"   Cost (USD): ${cost_usd:.6f}")
            
            # Verify cost calculation
            expected_cost = vertex_service._calculate_cost(model, input_tokens, output_tokens)
            assert abs(cost_usd - expected_cost) < 0.000001, f"Cost mismatch for {model}"
            print(f"   ✅ Cost calculation verified")
            
        except Exception as e:
            print(f"   ❌ Error testing {model}: {e}")
        
        print()
    
    # Test pricing rates match specification
    print("📋 Verifying pricing rates match 05_Vertex_and_Tokens.md:")
    expected_rates = {
        "gemini-2.5-pro": 3.50,
        "gemini-2.5-flash": 0.35,
        "gemini-2.5-flash-lite": 0.05
    }
    
    for model, expected_rate in expected_rates.items():
        actual_input_rate = MODEL_PRICING[model]["input"]
        actual_output_rate = MODEL_PRICING[model]["output"]
        
        print(f"   {model}:")
        print(f"     Expected: ${expected_rate:.2f}/1M tokens")
        print(f"     Actual input: ${actual_input_rate:.2f}/1M tokens")
        print(f"     Actual output: ${actual_output_rate:.2f}/1M tokens")
        
        if actual_input_rate == expected_rate and actual_output_rate == expected_rate:
            print(f"     ✅ Pricing matches specification")
        else:
            print(f"     ❌ Pricing mismatch!")
        print()

if __name__ == "__main__":
    asyncio.run(test_model_pricing())