# Web_Nanny Test Suite Guide

## Overview
The Web_Nanny application now includes a comprehensive test suite with **72 tests** covering all aspects of the application.

### Test Results Summary
```
✅ 72 TESTS PASSING
├── test_comprehensive.py: 51 tests (comprehensive suite)
├── test_endpoints.py:     17 tests (endpoint validation)
└── test_simple.py:         4 tests (basic functionality)
```

---

## Test Categories

### 1. HTTP Endpoints Tests (16 tests)
**File**: `test_comprehensive.py::TestHTTPEndpoints`

Tests HTML endpoints with language support:
- ✅ Homepage returns 200 OK
- ✅ Homepage contains language selector
- ✅ Sender endpoint with English/Polish language
- ✅ Listener endpoint with English/Polish language
- ✅ WebRTC setup code is present
- ✅ WebSocket signaling code is present
- ✅ Cry detection code is present
- ✅ HTML structure validation
- ✅ No Python errors in responses

**Key assertions**:
```python
# Language rendering
assert "Press to broadcast" in response.text  # English
assert "Elektroniczna Niania" in response.text  # Polish

# WebRTC presence
assert "RTCPeerConnection" in response.text
assert "mediaDevices.getUserMedia" in response.text

# HTML validity
assert "<!DOCTYPE" in response.text
assert "</html>" in response.text
```

### 2. WebSocket Signaling Tests (10 tests)
**File**: `test_comprehensive.py::TestWebSocketSignaling`

Tests WebSocket signaling protocol at `/signal` endpoint:
- ✅ Sender connection works
- ✅ Listener connection works
- ✅ Invalid role is rejected
- ✅ Ping/Pong heartbeat works
- ✅ Message relay between roles
- ✅ JSON parsing and validation
- ✅ Invalid JSON handling
- ✅ Multiple senders allowed (different sids)
- ✅ Session reconnection with same sid
- ✅ Session tracking

**Key features tested**:
```python
# Ping/Pong heartbeat
ws.send_text(json.dumps({"type": "ping"}))
response = ws.receive_text()  # {"type": "pong"}

# Session persistence
ws.send_text(json.dumps({"type": "offer", "sdp": {...}}))
# Message gets relayed to peer
```

### 3. Data Relay Tests (7 tests)
**File**: `test_comprehensive.py::TestWebSocketDataRelay`

Tests audio/data relay between sender and listener:
- ✅ Send endpoint basic connection
- ✅ Listen endpoint basic connection
- ✅ Only one sender allowed
- ✅ Only one listener allowed
- ✅ Send endpoint accepts bytes
- ✅ Send endpoint accepts text
- ✅ Listener receives from sender

**Test scenarios**:
```python
# Only one sender
with client.websocket_connect("/send") as sender1:
    with pytest.raises(Exception):
        with client.websocket_connect("/send") as sender2:
            pass  # Second connection rejected

# Data relay
with client.websocket_connect("/listen") as listener:
    with client.websocket_connect("/send") as sender:
        sender.send_bytes(b"test audio")
        # Listener receives data
```

### 4. Health and Metrics Tests (3 tests)
**File**: `test_comprehensive.py::TestHealthAndMetrics`

Tests monitoring endpoints:
- ✅ `/health` endpoint returns valid data
- ✅ `/metrics` endpoint returns valid data
- ✅ Uptime increases over time

**Response validation**:
```python
{
    "status": "ok",
    "uptime_seconds": 12.34,
    "active_sessions": 2,
    "sender_connected": true,
    "listener_connected": true
}
```

### 5. Error Handling Tests (5 tests)
**File**: `test_comprehensive.py::TestErrorHandling`

Stress tests and error scenarios:
- ✅ Missing endpoints return 404
- ✅ WebSocket disconnection cleanup
- ✅ Concurrent sessions stability
- ✅ Large message handling (100KB+)
- ✅ Rapid-fire message handling (100+ messages)

**Resilience verified**:
```python
# Handles 100KB messages
large_data = "x" * 100000
ws.send_text(json.dumps({"type": "data", "payload": large_data}))

# Rapid messaging
for i in range(100):
    ws.send_text(json.dumps({"type": "ping"}))
```

### 6. Language Rendering Tests (5 tests)
**File**: `test_comprehensive.py::TestLanguageRendering`

Validates Jinja2 template rendering:
- ✅ Language parameter in titles
- ✅ English text content
- ✅ Polish text content
- ✅ Conditional blocks render correctly
- ✅ Different content for different languages

**Template validation**:
```python
# English rendering
response = client.get("/listener?lang=en")
assert "Press to listen" in response.text

# Polish rendering
response = client.get("/listener?lang=pl")
assert "odsłuchiwać" in response.text  # Polish: "listen"

# Verify different
en = client.get("/sender?lang=en").text
pl = client.get("/sender?lang=pl").text
assert en != pl  # Content must be different
```

### 7. Session Management Tests (3 tests)
**File**: `test_comprehensive.py::TestSessionManagement`

Tests session lifecycle:
- ✅ Session creation on connect
- ✅ Session persistence during connection
- ✅ Multiple roles with different sids

### 8. Stress and Performance Tests (2 tests)
**File**: `test_comprehensive.py::TestStressAndPerformance`

Tests application resilience:
- ✅ 20 sequential connections
- ✅ Connection stability (10+ pings)

---

## Running the Tests

### Run All Tests
```bash
pytest -v
```

### Run Specific Test Suite
```bash
# Comprehensive tests only
pytest test_comprehensive.py -v

# Endpoint tests
pytest test_endpoints.py -v

# Simple tests
pytest test_simple.py -v
```

### Run Specific Test Class
```bash
pytest test_comprehensive.py::TestHTTPEndpoints -v
```

### Run Single Test
```bash
pytest test_comprehensive.py::TestHTTPEndpoints::test_sender_default_language_en -v
```

### Run with Detailed Output
```bash
pytest -v --tb=short
pytest -v --tb=long  # Very detailed
```

### Run Quietly (Summary Only)
```bash
pytest --tb=no -q
```

### Generate HTML Report
```bash
pytest --html=report.html
```

---

## Test Output Example

```
test_comprehensive.py::TestHTTPEndpoints::test_sender_default_language_en PASSED [  5%]
test_comprehensive.py::TestHTTPEndpoints::test_sender_polish_language PASSED [  7%]
test_comprehensive.py::TestWebSocketSignaling::test_signal_endpoint_ping_pong PASSED [ 39%]
...
============================== 72 passed in 2.01s =============================
```

---

## Key Testing Patterns

### 1. HTTP Endpoint Testing
```python
def test_endpoint_response():
    response = client.get("/sender?lang=en")
    assert response.status_code == 200
    assert "HTML_CONTENT" in response.text
```

### 2. WebSocket Connection Testing
```python
def test_websocket():
    with client.websocket_connect("/signal?role=sender&sid=test") as ws:
        ws.send_text(json.dumps({"type": "ping"}))
        response = ws.receive_text()
        assert "pong" in response
```

### 3. Concurrent Operations
```python
def test_concurrent():
    with client.websocket_connect("/listen") as listener:
        with client.websocket_connect("/send") as sender:
            sender.send_bytes(b"test")
            # listener can receive
```

### 4. Error Handling
```python
def test_error():
    with pytest.raises(Exception):
        with client.websocket_connect("/send") as ws1:
            with client.websocket_connect("/send") as ws2:
                pass  # Should fail
```

---

## Coverage

The test suite covers:

| Area | Tests | Coverage |
|------|-------|----------|
| HTTP Endpoints | 16 | Homepage, Sender, Listener with language variants |
| WebSocket Signaling | 10 | Protocol, heartbeat, JSON, reconnection |
| Data Relay | 7 | Send/Listen connections, message passing |
| Health/Metrics | 3 | Monitoring endpoints, uptime |
| Error Handling | 5 | 404s, disconnects, stress, large messages |
| Language Rendering | 5 | Template rendering, Jinja2 variables |
| Session Management | 3 | Creation, persistence, multi-role |
| Performance | 2 | Sequential connections, stability |
| **TOTAL** | **51** | **Comprehensive** |

---

## Important Test Dependencies

The tests require:
- `pytest` - Test framework
- `fastapi` - Web framework
- `httpx` - HTTP client
- `websockets` - WebSocket support

All are in `requirements.txt`:
```
pytest
fastapi
httpx
...
```

---

## Continuous Integration

Run tests before deployment:
```bash
# Full validation
pytest -v --tb=short

# Quick check
pytest --tb=no -q

# With coverage
pytest --cov=main test_*.py
```

---

## Troubleshooting

### Test Timeouts
If tests timeout, increase the timeout in test:
```python
timeout=120000  # milliseconds
```

### SSL/Certificate Warnings
Tests automatically suppress SSL warnings for self-signed certificates used in development.

### WebSocket Test Failures
Ensure the FastAPI server is NOT running when running WebSocket tests (they use TestClient which is synchronous).

---

## Notes

- All 72 tests pass ✅
- Tests use FastAPI's TestClient (no live server needed)
- Tests are isolated (no shared state between tests)
- Language rendering tested with both English and Polish
- WebSocket protocol fully validated
- Performance and stress tested
- Error scenarios covered

---

**Last Updated**: May 31, 2026
**Test Version**: 1.0
**Status**: ✅ All Tests Passing
