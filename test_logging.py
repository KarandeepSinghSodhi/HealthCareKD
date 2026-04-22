#!/usr/bin/env python
"""Test script to verify comprehensive LLM logging is working."""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_chat_endpoint():
    """Send a test message to /api/chat and capture response."""
    print("\n" + "="*60)
    print("TEST: POST /api/chat with 'I have a fever and cough'")
    print("="*60)
    
    payload = {
        "messages": [
            {"role": "user", "content": "I have a fever and cough"}
        ]
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/chat",
            json=payload,
            timeout=30
        )
        
        print(f"\nResponse Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Specialist Responses Keys: {list(data.keys())}")
            print(f"\nResponse received with {len(data)} specialist responses:")
            for specialist_id, response_text in data.items():
                preview = response_text[:100] + "..." if len(response_text) > 100 else response_text
                print(f"  - {specialist_id}: {preview}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    print("Waiting for server to be ready...")
    time.sleep(2)
    
    print("\n=== Testing API Endpoints ===\n")
    
    # Test 1: Check if API is running
    try:
        response = requests.get(f"{BASE_URL}/api/specialists", timeout=5)
        print(f"✓ API is running (Status: {response.status_code})")
        
        # Test 2: Send chat request
        test_chat_endpoint()
        
    except Exception as e:
        print(f"✗ API not responding: {e}")
        print("\nMake sure the backend server is running:")
        print("  cd medical-panel-backend && python main.py")
