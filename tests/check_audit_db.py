#!/usr/bin/env python3
"""
Check audit database for any entries
"""
import asyncio
import asyncpg
import os

async def check_audit_database():
    """Check what's in the audit database"""
    print("🔍 Checking Audit Database")
    print("=" * 40)
    
    db_url = os.getenv("POSTGRES_URL", "postgresql://soc_user:soc_password@localhost:5432/soc_platform")
    
    try:
        # Connect to database
        conn = await asyncpg.connect(db_url)
        print("✅ Connected to audit database")
        
        # Check if table exists
        table_exists = await conn.fetchval(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'audit_steps')"
        )
        print(f"Table exists: {table_exists}")
        
        if table_exists:
            # Count total rows
            total_rows = await conn.fetchval("SELECT COUNT(*) FROM audit_steps")
            print(f"Total audit steps: {total_rows}")
            
            if total_rows > 0:
                # Show recent entries
                print("\n📊 Recent audit steps:")
                rows = await conn.fetch(
                    "SELECT case_id, step_id, agent_name, timestamp FROM audit_steps ORDER BY timestamp DESC LIMIT 10"
                )
                
                for row in rows:
                    print(f"  {row['timestamp']} | {row['case_id'][:8]}... | {row['agent_name']} | {row['step_id']}")
                
                # Check for our specific case
                our_case_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM audit_steps WHERE case_id = $1",
                    "6c7a11e3-5fbd-4cf9-8eee-e826aa40f9dc"
                )
                print(f"\nSteps for case 6c7a11e3-5fbd-4cf9-8eee-e826aa40f9dc: {our_case_count}")
                
                if our_case_count > 0:
                    case_rows = await conn.fetch(
                        "SELECT step_id, agent_name, timestamp, hash FROM audit_steps WHERE case_id = $1 ORDER BY timestamp",
                        "6c7a11e3-5fbd-4cf9-8eee-e826aa40f9dc"
                    )
                    
                    print(f"Case steps:")
                    for row in case_rows:
                        print(f"  {row['timestamp']} | {row['agent_name']} | {row['step_id']} | {row['hash'][:16]}...")
            
        await conn.close()
        
    except Exception as e:
        print(f"❌ Database check failed: {e}")

if __name__ == "__main__":
    asyncio.run(check_audit_database())