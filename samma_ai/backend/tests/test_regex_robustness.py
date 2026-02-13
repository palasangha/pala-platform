import re

patterns = [
    (r'1\.\s+(?:[\*\#_>]*\s*)?Direct Definition', 'direct_definition'),
    (r'2\.\s+(?:[\*\#_>]*\s*)?Samma AI Interpretive Insight', 'interpretive_insight'),
    (r'3\.\s+(?:[\*\#_>]*\s*)?Canonical Teachings', 'canonical_teachings'),
    (r'4\.\s+(?:[\*\#_>]*\s*)?Aṭṭhakathā Commentary', 'commentary'),
    (r'5\.\s+(?:[\*\#_>]*\s*)?Ṭīkā Clarification', 'tika_clarification'),
    (r'6\.\s+(?:[\*\#_>]*\s*)?Lexical & Philological Analysis', 'lexical_analysis'),
    (r'7\.\s+(?:[\*\#_>]*\s*)?Doctrinal Function', 'doctrinal_function'),
    (r'8\.\s+(?:[\*\#_>]*\s*)?Final Teaching Summary', 'final_summary')
]

test_cases = [
    "1. Direct Definition",
    "1. **Direct Definition**",
    "**1. Direct Definition**",
    "## 1. Direct Definition",
    "1. _Direct Definition_",
    "1. > Direct Definition",
    "1.      Direct Definition"
]

print("Testing regex patterns...")
for text in test_cases:
    found = False
    for p, key in patterns:
        match = re.search(p, text, re.IGNORECASE)
        if match:
            print(f"[PASS] Matched '{text}' as {key}")
            found = True
            break
    if not found:
        print(f"[FAIL] Did not match '{text}'")
