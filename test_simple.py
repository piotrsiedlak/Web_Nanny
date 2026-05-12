"""
Simple test script to verify endpoints don't return Python tracebacks.
Run this with: python test_simple.py
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from fastapi.testclient import TestClient
from main import app

# Suppress SSL warnings for self-signed certificates
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

client = TestClient(app)


def test_sender_endpoint():
    """Test /sender endpoint"""
    print("\n[TEST] GET /sender endpoint...")
    try:
        response = client.get("/sender")
        
        # Check status code
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"  ✓ Status code: {response.status_code}")
        
        # Check for HTML
        assert "<!DOCTYPE" in response.text or "<html" in response.text or "<!doctype" in response.text.lower(), \
            "Response doesn't contain HTML"
        print(f"  ✓ Returns HTML content")
        
        # Check for Python tracebacks
        error_strings = ["Traceback", "ValueError", "TypeError", "AttributeError", "FileNotFoundError"]
        traceback_found = any(err in response.text for err in error_strings)
        assert not traceback_found, f"Response contains Python error/traceback"
        print(f"  ✓ No Python errors/tracebacks")
        
        # Check content is not empty
        assert len(response.text) > 0, "Response is empty"
        print(f"  ✓ Content length: {len(response.text)} bytes")
        
        print("  ✅ PASSED: /sender endpoint working correctly")
        return True
        
    except AssertionError as e:
        print(f"  ❌ FAILED: {e}")
        return False
    except Exception as e:
        print(f"  ❌ ERROR: {type(e).__name__}: {e}")
        return False


def test_listener_endpoint():
    """Test /listener endpoint"""
    print("\n[TEST] GET /listener endpoint...")
    try:
        response = client.get("/listener")
        
        # Check status code
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"  ✓ Status code: {response.status_code}")
        
        # Check for HTML
        assert "<!DOCTYPE" in response.text or "<html" in response.text or "<!doctype" in response.text.lower(), \
            "Response doesn't contain HTML"
        print(f"  ✓ Returns HTML content")
        
        # Check for Python tracebacks
        error_strings = ["Traceback", "ValueError", "TypeError", "AttributeError", "FileNotFoundError"]
        traceback_found = any(err in response.text for err in error_strings)
        assert not traceback_found, f"Response contains Python error/traceback"
        print(f"  ✓ No Python errors/tracebacks")
        
        # Check content is not empty
        assert len(response.text) > 0, "Response is empty"
        print(f"  ✓ Content length: {len(response.text)} bytes")
        
        print("  ✅ PASSED: /listener endpoint working correctly")
        return True
        
    except AssertionError as e:
        print(f"  ❌ FAILED: {e}")
        return False
    except Exception as e:
        print(f"  ❌ ERROR: {type(e).__name__}: {e}")
        return False


def test_websocket_send():
    """Test /send WebSocket endpoint"""
    print("\n[TEST] WebSocket /send endpoint...")
    try:
        with client.websocket_connect("/send") as websocket:
            print(f"  ✓ WebSocket connection established")
            websocket.send_bytes(b"test message")
            print(f"  ✓ Successfully sent bytes")
        
        print("  ✅ PASSED: /send WebSocket endpoint working correctly")
        return True
        
    except Exception as e:
        print(f"  ❌ ERROR: {type(e).__name__}: {e}")
        return False


def test_websocket_listen():
    """Test /listen WebSocket endpoint"""
    print("\n[TEST] WebSocket /listen endpoint...")
    try:
        with client.websocket_connect("/listen") as websocket:
            print(f"  ✓ WebSocket connection established")
            # Just verify connection stays open briefly
            import time
            time.sleep(0.1)
            print(f"  ✓ WebSocket connection remains open")
        
        print("  ✅ PASSED: /listen WebSocket endpoint working correctly")
        return True
        
    except Exception as e:
        print(f"  ❌ ERROR: {type(e).__name__}: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 70)
    print("Web_Nanny Endpoint Tests")
    print("=" * 70)
    
    results = []
    
    # Run HTTP endpoint tests
    results.append(("GET /sender", test_sender_endpoint()))
    results.append(("GET /listener", test_listener_endpoint()))
    
    # Run WebSocket tests
    results.append(("WebSocket /send", test_websocket_send()))
    results.append(("WebSocket /listen", test_websocket_listen()))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:8} | {name}")
    
    print("=" * 70)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Endpoints are working correctly.")
        return 0
    else:
        print(f"⚠️  {total - passed} test(s) failed.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
