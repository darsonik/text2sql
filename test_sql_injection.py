#!/usr/bin/env python3
"""
Quick test to verify SQL injection patterns work correctly.
"""

import re

# Test the current patterns from agent_tools.py
SQL_INJECTION_PATTERNS = [
    r"(\b(union|select|insert|update|delete|drop|create|alter|exec|execute|script|declare|truncate)\b.*){2,}",
    r"(--|#|/\*|\*/)",
    r"(\b(or|and)\b.*=.*=)",
    r"(\bunion\b.*\bselect\b)",
    r"(\bdrop\b.*\btable\b)",
    r"(\bexec\b.*\b\()",
    r"(\bxp_cmdshell\b)",
    r"(\bsp_executesql\b)",
    r"(\'|\")\s*(or|and)\s*(\'|\")\s*=",
    r"\'\s*(or|and)\s*\'\s*=",
    r"\'\s*or\s*\'.*=.*\'\s*=",
    r"\'.*or.*\'.*=.*\'.*=",
    r"\b1\s*=\s*1\b"
]

def detect_sql_injection(query: str):
    """Detect potential SQL injection attempts."""
    query_lower = query.lower()
    
    for pattern in SQL_INJECTION_PATTERNS:
        if re.search(pattern, query_lower, re.IGNORECASE):
            return f"Potential SQL injection detected: matches pattern '{pattern}'"
    
    return None

# Test cases
test_cases = [
    ("' OR '1'='1", True),
    ('" OR "1"="1', True),
    ("' OR 'x'='x", True),
    ("1=1", True),
    ("1 = 1", True),
    ("' OR 1=1", True),
    ("SELECT * FROM users; DROP TABLE users;", True),
    ("Show me all organizations", False),
    ("List users", False),
    ("What products are available?", False),
]

print("Testing SQL Injection Detection Patterns:")
print("=" * 50)

all_passed = True
for query, should_detect in test_cases:
    result = detect_sql_injection(query)
    detected = result is not None
    
    if detected == should_detect:
        status = "✅ PASS"
    else:
        status = "❌ FAIL"
        all_passed = False
    
    expected = "DETECT" if should_detect else "ALLOW"
    actual = "DETECTED" if detected else "ALLOWED"
    
    print(f"{status} '{query}' -> Expected: {expected}, Got: {actual}")
    if detected:
        print(f"     Reason: {result[:60]}...")

print("\n" + "=" * 50)
if all_passed:
    print("🎉 All SQL injection detection tests PASSED!")
else:
    print("⚠️  Some SQL injection detection tests FAILED!")

# Additional test for the specific failing pattern
print("\n" + "=" * 30)
print("Testing specific failing pattern:")
problem_query = "' OR '1'='1"
result = detect_sql_injection(problem_query)
if result:
    print(f"✅ '{problem_query}' correctly detected: {result}")
else:
    print(f"❌ '{problem_query}' not detected - needs pattern fix")
    
    # Test individual patterns
    print("\nTesting individual patterns:")
    for i, pattern in enumerate(SQL_INJECTION_PATTERNS):
        if re.search(pattern, problem_query.lower(), re.IGNORECASE):
            print(f"✅ Pattern {i+1}: {pattern[:40]}... MATCHES")
        else:
            print(f"❌ Pattern {i+1}: {pattern[:40]}... no match")