#!/usr/bin/env python3
"""Test Samma AI API with sample query"""

import requests
import json
import time

BASE_URL = "http://localhost:5001/api"

def test_chat_api():
    """Test the chat API with a sample Dhamma question"""
    
    print("=" * 70)
    print("🧪 Testing Samma AI Chat API")
    print("=" * 70)
    
    # Test 1: Health check
    print("\n1️⃣  Testing API Health...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        if response.status_code == 200:
            print("   ✅ API is healthy")
        else:
            print("   ❌ API health check failed")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Test 2: Chat API with sample query
    print("\n2️⃣  Testing Chat API with sample query...")
    query = "What is dukkha in Buddhism?"
    
    payload = {
        "message": query,
        "conversation_id": "test-conv-001"
    }
    
    print(f"   Query: {query}")
    print(f"   Payload: {json.dumps(payload, indent=2)}")
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/chat",
            json=payload,
            timeout=30
        )
        elapsed = time.time() - start_time
        
        print(f"\n   Status: {response.status_code}")
        print(f"   Response time: {elapsed:.2f}s")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n   ✅ Chat API successful")
            
            # Check response structure
            print(f"\n   Response structure:")
            if 'response' in data:
                resp = data['response']
                print(f"   - Database Summary: {len(resp.get('database_summary', ''))} chars")
                print(f"   - Interpretive Summary: {len(resp.get('interpretive_summary', ''))} chars")
                teachings = resp.get('teachings', [])
                print(f"   - Teachings: {len(teachings)} passages")
                print(f"   - Final Summary: {len(resp.get('final_summary', ''))} chars")
                
                # Print first teaching as sample
                if teachings:
                    print(f"\n   First teaching sample:")
                    t = teachings[0]
                    print(f"      Pali: {t.get('pali_text', '')[:100]}...")
                    print(f"      English: {t.get('english_translation', '')[:100]}...")
            
            # Print full response for debugging
            print(f"\n   Full response:")
            print(json.dumps(data, indent=2)[:500])
            
            return True
        else:
            print(f"   ❌ API Error: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"   ❌ Request timeout after 30 seconds")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 70)
    print("✅ All tests completed")
    print("=" * 70)

if __name__ == "__main__":
    success = test_chat_api()
    exit(0 if success else 1)
