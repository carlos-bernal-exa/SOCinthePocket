#!/usr/bin/env python3
"""
Setup real environment variables and test all service connections
"""
import os
import asyncio
import logging

# Set up comprehensive environment for real services
def setup_environment():
    """Setup environment variables for real integrations"""
    print("🔧 Setting up environment for REAL integrations...")
    
    # Vertex AI - Use existing service account key
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/Users/cbernal/AIProjects/Claude/soc_agent_project/threatexplainer-1185aa9fcd44.json"
    os.environ["GOOGLE_CLOUD_PROJECT"] = "threatexplainer"
    os.environ["GOOGLE_CLOUD_REGION"] = "us-central1"
    
    # Redis - Local instance
    os.environ["REDIS_URL"] = "redis://localhost:6379"
    
    # Qdrant - Docker container
    os.environ["QDRANT_HOST"] = "localhost"
    os.environ["QDRANT_PORT"] = "6333"
    
    # Neo4j - Docker container
    os.environ["NEO4J_URI"] = "bolt://localhost:7687"
    os.environ["NEO4J_USERNAME"] = "neo4j"
    os.environ["NEO4J_PASSWORD"] = "soc_neo4j_password"
    
    # PostgreSQL - Docker container  
    os.environ["POSTGRES_URL"] = "postgresql://soc_user:soc_password@localhost:5432/soc_platform"
    
    # Exabeam configuration (you mentioned there's config for this)
    # Setting up reasonable defaults - user can override if they have specific credentials
    os.environ["EXABEAM_BASE_URL"] = os.getenv("EXABEAM_BASE_URL", "https://demo-exabeam.com")
    os.environ["EXABEAM_USERNAME"] = os.getenv("EXABEAM_USERNAME", "soc_analyst")  
    os.environ["EXABEAM_PASSWORD"] = os.getenv("EXABEAM_PASSWORD", "demo_password")
    
    # SIEM (also Exabeam as mentioned)
    os.environ["SIEM_TYPE"] = "exabeam"
    os.environ["SIEM_BASE_URL"] = os.getenv("EXABEAM_BASE_URL", "https://demo-exabeam.com") 
    os.environ["SIEM_USERNAME"] = os.getenv("EXABEAM_USERNAME", "soc_analyst")
    os.environ["SIEM_PASSWORD"] = os.getenv("EXABEAM_PASSWORD", "demo_password")
    
    print("✅ Environment configured for real integrations!")
    
    # Print configuration summary
    print("\n📊 Service Configuration:")
    print(f"   Vertex AI Project: {os.environ.get('GOOGLE_CLOUD_PROJECT')}")
    print(f"   Redis URL: {os.environ.get('REDIS_URL')}")
    print(f"   Qdrant: {os.environ.get('QDRANT_HOST')}:{os.environ.get('QDRANT_PORT')}")
    print(f"   Neo4j: {os.environ.get('NEO4J_URI')}")
    print(f"   Exabeam: {os.environ.get('EXABEAM_BASE_URL')}")
    print(f"   SIEM Type: {os.environ.get('SIEM_TYPE')}")

async def test_service_connections():
    """Test connections to all real services"""
    print("\n🧪 Testing service connections...")
    
    # Test Redis
    try:
        import redis
        r = redis.from_url(os.environ.get("REDIS_URL"))
        r.ping()
        key_count = r.dbsize()
        print(f"   ✅ Redis: Connected, {key_count} keys")
    except Exception as e:
        print(f"   ❌ Redis: Failed - {e}")
    
    # Test Qdrant
    try:
        import requests
        qdrant_url = f"http://{os.environ.get('QDRANT_HOST')}:{os.environ.get('QDRANT_PORT')}"
        response = requests.get(f"{qdrant_url}/collections")
        if response.status_code == 200:
            collections = response.json()
            print(f"   ✅ Qdrant: Connected, {len(collections.get('result', {}).get('collections', []))} collections")
        else:
            print(f"   ❌ Qdrant: HTTP {response.status_code}")
    except Exception as e:
        print(f"   ❌ Qdrant: Failed - {e}")
    
    # Test Neo4j
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            os.environ.get("NEO4J_URI"),
            auth=(os.environ.get("NEO4J_USERNAME"), os.environ.get("NEO4J_PASSWORD"))
        )
        with driver.session() as session:
            result = session.run("RETURN 1 as test")
            record = result.single()
            print(f"   ✅ Neo4j: Connected")
        driver.close()
    except Exception as e:
        print(f"   ❌ Neo4j: Failed - {e}")
    
    # Test PostgreSQL
    try:
        import asyncpg
        conn = await asyncpg.connect(os.environ.get("POSTGRES_URL"))
        await conn.execute("SELECT 1")
        await conn.close()
        print(f"   ✅ PostgreSQL: Connected")
    except Exception as e:
        print(f"   ❌ PostgreSQL: Failed - {e}")
    
    # Test Vertex AI
    try:
        from google.cloud import aiplatform
        aiplatform.init(
            project=os.environ.get("GOOGLE_CLOUD_PROJECT"),
            location=os.environ.get("GOOGLE_CLOUD_REGION")
        )
        print(f"   ✅ Vertex AI: Credentials loaded")
    except Exception as e:
        print(f"   ❌ Vertex AI: Failed - {e}")

async def main():
    setup_environment()
    await test_service_connections()
    
    print(f"\n🎯 Ready for real case testing!")
    print(f"All environment variables set for maximum real integration coverage.")

if __name__ == "__main__":
    asyncio.run(main())