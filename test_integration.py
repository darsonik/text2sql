#!/usr/bin/env python3
"""
Simple integration test for production database and agent tools.
This test verifies the database integration works without external dependencies.
"""

import sys
import os
import sqlite3
from pathlib import Path

# Add src to path
sys.path.insert(0, '/home/tuhinkarmakar/Repositories/text2sql/src')

def test_database_connection():
    """Test basic database connection and table structure."""
    print("=== Database Connection Test ===")
    
    db_path = "/home/tuhinkarmakar/Repositories/text2sql/src/text2sql/database/production.db"
    
    if not Path(db_path).exists():
        print(f"❌ Database not found at {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Test 1: Check tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        expected_tables = ['organizations', 'users', 'categories', 'products', 'orders', 'order_items', 'payments', 'audit_logs']
        
        missing_tables = set(expected_tables) - set(tables)
        if missing_tables:
            print(f"❌ Missing tables: {missing_tables}")
            return False
        
        print(f"✅ All expected tables found: {len(expected_tables)}")
        
        # Test 2: Check data exists
        for table in expected_tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            if count == 0:
                print(f"⚠️  Table {table} has no data")
            else:
                print(f"✅ Table {table} has {count} rows")
        
        # Test 3: Check relationships
        cursor.execute("""
            SELECT u.id, u.full_name, o.name as organization
            FROM users u
            JOIN organizations o ON u.organization_id = o.id
            LIMIT 3
        """)
        user_org_data = cursor.fetchall()
        if user_org_data:
            print(f"✅ User-Organization relationships working: {len(user_org_data)} users with orgs")
        else:
            print("⚠️  No user-organization relationships found")
        
        # Test 4: Check complex query
        cursor.execute("""
            SELECT 
                o.name as org_name,
                COUNT(DISTINCT u.id) as user_count,
                COUNT(DISTINCT p.id) as product_count,
                COUNT(DISTINCT ord.id) as order_count
            FROM organizations o
            LEFT JOIN users u ON o.id = u.organization_id
            LEFT JOIN products p ON o.id = p.organization_id
            LEFT JOIN orders ord ON o.id = ord.organization_id
            GROUP BY o.id, o.name
        """)
        org_stats = cursor.fetchall()
        print(f"✅ Complex multi-table query working: {len(org_stats)} organizations with stats")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_production_engine():
    """Test the production engine creation without external dependencies."""
    print("\n=== Production Engine Test ===")
    
    try:
        # Import our production engine function
        from text2sql.agents.agent_tools import get_engine, PRODUCTION_TABLES
        
        print(f"Expected tables: {PRODUCTION_TABLES}")
        
        # Test engine creation (this will initialize if needed)
        engine = get_engine()
        print("✅ Production engine created successfully")
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            result.fetchone()
            print("✅ Database connection test passed")
        
        return True
        
    except Exception as e:
        print(f"❌ Production engine test failed: {e}")
        return False

def test_query_validator():
    """Test query validation functionality."""
    print("\n=== Query Validator Test ===")
    
    try:
        from text2sql.agents.agent_tools import QueryValidator
        
        # Test valid queries
        valid_queries = [
            "Show me all organizations",
            "List users in Tech Corp",
            "What products are available?"
        ]
        
        for query in valid_queries:
            result = QueryValidator.validate_query(query)
            if result["valid"]:
                print(f"✅ Valid query accepted: '{query[:30]}...'")
            else:
                print(f"❌ Valid query rejected: '{query[:30]}...' - {result['errors']}")
                return False
        
        # Test invalid queries
        invalid_queries = [
            "SELECT * FROM users; DROP TABLE users;",
            "' OR '1'='1",
            "UNION SELECT password FROM users"
        ]
        
        for query in invalid_queries:
            result = QueryValidator.validate_query(query)
            if not result["valid"]:
                print(f"✅ Invalid query rejected: '{query[:30]}...'")
            else:
                print(f"❌ Invalid query accepted: '{query[:30]}...'")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Query validator test failed: {e}")
        return False

def main():
    """Run all integration tests."""
    print("🚀 Starting Production Database Integration Tests")
    print("=" * 60)
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Production Engine", test_production_engine),
        ("Query Validator", test_query_validator)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"\n✅ {test_name} test PASSED")
            else:
                print(f"\n❌ {test_name} test FAILED")
        except Exception as e:
            print(f"\n❌ {test_name} test ERROR: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All integration tests PASSED!")
        return True
    else:
        print("⚠️  Some tests FAILED!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)