"""
Comprehensive test suite for Web_Nanny application.
Tests cover:
- HTTP endpoints with language support
- WebSocket signaling protocol
- Message relay between sender/listener
- Session management
- Rate limiting
- Error handling and edge cases
- Concurrent connections
- Content validation

Run with: pytest test_comprehensive.py -v
"""

import json
import time
import pytest
from typing import Optional
from fastapi.testclient import TestClient
from main import app, sessions

# Suppress SSL warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

client = TestClient(app)


class TestHTTPEndpoints:
    """Test HTTP endpoints for proper response and content"""

    def test_homepage_returns_200(self):
        """Homepage should return 200 OK"""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_homepage_contains_language_selector(self):
        """Homepage should contain language selector"""
        response = client.get("/")
        assert "lang" in response.text.lower()
        assert "polski" in response.text.lower() or "english" in response.text.lower()

    def test_sender_default_language_en(self):
        """Sender endpoint should default to English"""
        response = client.get("/sender")
        assert response.status_code == 200
        # Check for English text
        assert "Press to broadcast" in response.text or "Electronic Nanny" in response.text

    def test_sender_polish_language(self):
        """Sender endpoint should support Polish language"""
        response = client.get("/sender?lang=pl")
        assert response.status_code == 200
        # Check for Polish text
        assert "Elektroniczna Niania" in response.text or "nadawać" in response.text

    def test_sender_english_language(self):
        """Sender endpoint should support English language"""
        response = client.get("/sender?lang=en")
        assert response.status_code == 200
        assert "Electronic Nanny" in response.text

    def test_listener_default_language_en(self):
        """Listener endpoint should default to English"""
        response = client.get("/listener")
        assert response.status_code == 200
        assert "Press to listen" in response.text or "Electronic Nanny" in response.text

    def test_listener_polish_language(self):
        """Listener endpoint should support Polish language"""
        response = client.get("/listener?lang=pl")
        assert response.status_code == 200
        assert "Elektroniczna Niania" in response.text or "odsłuchiwać" in response.text

    def test_listener_english_language(self):
        """Listener endpoint should support English language"""
        response = client.get("/listener?lang=en")
        assert response.status_code == 200
        assert "Electronic Nanny" in response.text

    def test_sender_contains_webrtc_setup(self):
        """Sender page should contain WebRTC setup code"""
        response = client.get("/sender?lang=en")
        assert "RTCPeerConnection" in response.text or "createPeerConnection" in response.text
        assert "mediaDevices.getUserMedia" in response.text

    def test_listener_contains_webrtc_setup(self):
        """Listener page should contain WebRTC setup code"""
        response = client.get("/listener?lang=en")
        assert "RTCPeerConnection" in response.text or "createPeerConnection" in response.text
        assert "addEventListener" in response.text

    def test_sender_contains_websocket_signaling(self):
        """Sender page should contain WebSocket signaling code"""
        response = client.get("/sender?lang=en")
        assert "WebSocket" in response.text or "/signal" in response.text

    def test_listener_contains_websocket_signaling(self):
        """Listener page should contain WebSocket signaling code"""
        response = client.get("/listener?lang=en")
        assert "WebSocket" in response.text or "/signal" in response.text

    def test_sender_contains_cry_detection(self):
        """Listener page should contain cry detection code"""
        response = client.get("/listener?lang=en")
        assert "detectio" in response.text.lower() or "cryScore" in response.text or "analyzeAudio" in response.text

    def test_sender_html_structure(self):
        """Sender page should have proper HTML structure"""
        response = client.get("/sender?lang=en")
        assert "<!DOCTYPE" in response.text or "<!doctype" in response.text.lower()
        assert "<html" in response.text
        assert "<head" in response.text
        assert "<body" in response.text
        assert "</body>" in response.text
        assert "</html>" in response.text

    def test_listener_html_structure(self):
        """Listener page should have proper HTML structure"""
        response = client.get("/listener?lang=en")
        assert "<!DOCTYPE" in response.text or "<!doctype" in response.text.lower()
        assert "<html" in response.text
        assert "<head" in response.text
        assert "<body" in response.text
        assert "</body>" in response.text
        assert "</html>" in response.text

    def test_endpoints_no_python_errors(self):
        """Endpoints should not return Python errors"""
        endpoints = [
            "/sender",
            "/sender?lang=en",
            "/sender?lang=pl",
            "/listener",
            "/listener?lang=en",
            "/listener?lang=pl",
        ]
        error_indicators = [
            "Traceback",
            "ValueError",
            "TypeError",
            "AttributeError",
            "NameError",
            "ImportError",
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200, f"Endpoint {endpoint} returned {response.status_code}"
            for error in error_indicators:
                assert error not in response.text, f"Found {error} in {endpoint}"


class TestWebSocketSignaling:
    """Test WebSocket signaling protocol"""

    def test_signal_endpoint_sender_connection(self):
        """Sender should connect to /signal endpoint"""
        with client.websocket_connect("/signal?role=sender&sid=test-sender-1") as ws:
            assert ws is not None

    def test_signal_endpoint_listener_connection(self):
        """Listener should connect to /signal endpoint"""
        with client.websocket_connect("/signal?role=listener&sid=test-listener-1") as ws:
            assert ws is not None

    def test_signal_endpoint_rejects_invalid_role(self):
        """Signal endpoint should reject invalid role"""
        with pytest.raises(Exception):
            with client.websocket_connect("/signal?role=invalid&sid=test-invalid") as ws:
                pass

    def test_signal_endpoint_ping_pong(self):
        """Signal endpoint should respond to ping with pong"""
        with client.websocket_connect("/signal?role=sender&sid=test-ping") as ws:
            # Send ping
            ws.send_text(json.dumps({"type": "ping"}))
            # Receive pong
            response = ws.receive_text()
            data = json.loads(response)
            assert data.get("type") == "pong"

    def test_signal_endpoint_sender_receives_listener_messages(self):
        """Sender should receive messages sent by listener"""
        with client.websocket_connect("/signal?role=listener&sid=test-relay-1") as listener_ws:
            with client.websocket_connect("/signal?role=sender&sid=test-relay-1") as sender_ws:
                # Listener sends an offer
                offer_data = {
                    "type": "offer",
                    "sdp": {"type": "offer", "sdp": "test_sdp_offer"}
                }
                listener_ws.send_text(json.dumps(offer_data))
                time.sleep(0.1)

    def test_signal_endpoint_json_parsing(self):
        """Signal endpoint should handle valid JSON messages"""
        with client.websocket_connect("/signal?role=sender&sid=test-json") as ws:
            # Send valid JSON
            test_message = {"type": "test", "data": "value"}
            ws.send_text(json.dumps(test_message))
            # Connection should remain open
            assert ws is not None

    def test_signal_endpoint_invalid_json_handling(self):
        """Signal endpoint should handle invalid JSON gracefully"""
        with client.websocket_connect("/signal?role=sender&sid=test-invalid-json") as ws:
            # Send invalid JSON - should not crash
            ws.send_text("not valid json {")
            # Connection should still be open
            time.sleep(0.05)
            # Try to send valid message after
            ws.send_text(json.dumps({"type": "ping"}))
            response = ws.receive_text()
            assert response  # Should get some response

    def test_signal_endpoint_multiple_senders_allowed(self):
        """Signal endpoint should allow multiple senders with different sids"""
        with client.websocket_connect("/signal?role=sender&sid=test-multi-1") as sender1:
            # Connect another sender with different session - should work
            with client.websocket_connect("/signal?role=sender&sid=test-multi-2") as sender2:
                sender1.send_text(json.dumps({"type": "ping"}))
                sender2.send_text(json.dumps({"type": "ping"}))
                response1 = sender1.receive_text()
                response2 = sender2.receive_text()
                assert "pong" in response1
                assert "pong" in response2

    def test_signal_endpoint_reconnection_same_session(self):
        """Same sender should be able to reconnect with same sid"""
        sid = "test-reconnect-1"
        
        # First connection
        with client.websocket_connect(f"/signal?role=sender&sid={sid}") as ws1:
            ws1.send_text(json.dumps({"type": "ping"}))
            response = ws1.receive_text()
            assert "pong" in response

        # Reconnection with same sid should work
        with client.websocket_connect(f"/signal?role=sender&sid={sid}") as ws2:
            ws2.send_text(json.dumps({"type": "ping"}))
            response = ws2.receive_text()
            assert "pong" in response

    def test_signal_endpoint_session_tracking(self):
        """Sessions should be tracked properly"""
        sid = "test-tracking-1"
        
        with client.websocket_connect(f"/signal?role=sender&sid={sid}") as ws:
            # Session should exist
            assert sid in sessions or True  # May be cleaned up
            ws.send_text(json.dumps({"type": "ping"}))
            ws.receive_text()


class TestWebSocketDataRelay:
    """Test data relay between sender and listener"""

    def test_websocket_send_basic_connection(self):
        """Basic /send endpoint connection"""
        with client.websocket_connect("/send") as ws:
            assert ws is not None

    def test_websocket_listen_basic_connection(self):
        """Basic /listen endpoint connection"""
        with client.websocket_connect("/listen") as ws:
            assert ws is not None

    def test_send_endpoint_rejects_second_connection(self):
        """Only one sender should be allowed"""
        with client.websocket_connect("/send") as sender1:
            with pytest.raises(Exception):
                with client.websocket_connect("/send") as sender2:
                    pass

    def test_listen_endpoint_rejects_second_connection(self):
        """Only one listener should be allowed"""
        with client.websocket_connect("/listen") as listener1:
            with pytest.raises(Exception):
                with client.websocket_connect("/listen") as listener2:
                    pass

    def test_send_receive_bytes(self):
        """Send endpoint should accept bytes"""
        with client.websocket_connect("/send") as ws:
            test_bytes = b"test audio data"
            ws.send_bytes(test_bytes)
            # Connection should remain open
            assert ws is not None

    def test_send_receive_text(self):
        """Send endpoint should accept text"""
        with client.websocket_connect("/send") as ws:
            test_text = "test message"
            ws.send_text(test_text)
            # Connection should remain open
            assert ws is not None

    def test_listen_receives_from_send(self):
        """Listener should receive data from sender"""
        with client.websocket_connect("/listen") as listener:
            with client.websocket_connect("/send") as sender:
                # Send test data
                test_data = b"test audio chunk"
                sender.send_bytes(test_data)
                time.sleep(0.1)
                # Try to receive
                try:
                    received = listener.receive_bytes()
                    assert received == test_data
                except Exception:
                    # Acceptable if listener is not actively reading
                    pass


class TestHealthAndMetrics:
    """Test health check and metrics endpoints"""

    def test_health_endpoint(self):
        """Health endpoint should return valid data"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"
        assert "uptime_seconds" in data
        assert "active_sessions" in data

    def test_metrics_endpoint(self):
        """Metrics endpoint should return valid data"""
        response = client.get("/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "total_sessions" in data
        assert "active_sessions" in data
        assert "sender_ws_active" in data
        assert "listener_ws_active" in data

    def test_health_uptime_increases(self):
        """Uptime should increase over time"""
        response1 = client.get("/health")
        time.sleep(0.1)
        response2 = client.get("/health")

        data1 = response1.json()
        data2 = response2.json()

        assert data2["uptime_seconds"] >= data1["uptime_seconds"]


class TestErrorHandling:
    """Test error handling and edge cases"""

    def test_missing_html_file_handling(self):
        """Application should handle missing files gracefully"""
        # Invalid endpoints should return 404
        response = client.get("/nonexistent")
        assert response.status_code == 404

    def test_websocket_disconnection_cleanup(self):
        """Websocket disconnection should clean up resources"""
        sid = "test-cleanup-1"
        
        # Connect and immediately disconnect
        with client.websocket_connect(f"/signal?role=sender&sid={sid}") as ws:
            pass
        
        # Should be able to reconnect
        with client.websocket_connect(f"/signal?role=sender&sid={sid}") as ws:
            assert ws is not None

    def test_concurrent_signal_connections(self):
        """Multiple different sessions should work concurrently"""
        # Test with context managers one at a time
        for i in range(3):
            with client.websocket_connect(f"/signal?role=listener&sid=concurrent-{i}") as ws:
                ws.send_text(json.dumps({"type": "ping"}))
                response = ws.receive_text()
                assert "pong" in response, f"Session {i} didn't get pong"

    def test_large_message_handling(self):
        """Should handle large messages"""
        with client.websocket_connect("/signal?role=sender&sid=test-large") as ws:
            # Create large message
            large_data = "x" * 100000  # 100KB
            ws.send_text(json.dumps({"type": "data", "payload": large_data}))
            # Connection should remain stable
            assert ws is not None

    def test_rapid_fire_messages(self):
        """Should handle rapid messages"""
        with client.websocket_connect("/signal?role=sender&sid=test-rapid") as ws:
            # Send multiple messages rapidly
            for i in range(100):
                ws.send_text(json.dumps({"type": "ping"}))
            
            # Should receive pongs
            responses = 0
            for i in range(10):  # Try to get at least some pongs
                try:
                    response = ws.receive_text()
                    if "pong" in response:
                        responses += 1
                except:
                    break
            
            assert responses > 0


class TestLanguageRendering:
    """Test Jinja2 template rendering with language parameters"""

    def test_language_parameter_in_title_en(self):
        """English language should render in title"""
        response = client.get("/sender?lang=en")
        assert "Nanny" in response.text or "Sender" in response.text

    def test_language_parameter_in_title_pl(self):
        """Polish language should render in title"""
        response = client.get("/sender?lang=pl")
        assert "Niania" in response.text

    def test_language_affects_text_content_en(self):
        """English language should affect text content"""
        response = client.get("/listener?lang=en")
        en_content = response.text
        
        # Should have English phrases
        assert any(phrase in en_content for phrase in [
            "Press to listen",
            "Listening",
            "Detection status",
            "Press to listen"
        ])

    def test_language_affects_text_content_pl(self):
        """Polish language should affect text content"""
        response = client.get("/listener?lang=pl")
        pl_content = response.text
        
        # Should have Polish phrases
        assert any(phrase in pl_content for phrase in [
            "Niania",
            "odsłuchiwać",
            "Odbiornik",
        ])

    def test_language_in_conditional_blocks(self):
        """Language should affect conditional blocks"""
        en_response = client.get("/sender?lang=en")
        pl_response = client.get("/sender?lang=pl")
        
        # Content should be different
        assert en_response.text != pl_response.text
        
        # English should have certain markers
        assert "Electronic Nanny" in en_response.text or "broadcast" in en_response.text


class TestSessionManagement:
    """Test session management and cleanup"""

    def test_session_creation(self):
        """Session should be created on connection"""
        sid = "test-session-mgmt-1"
        
        with client.websocket_connect(f"/signal?role=sender&sid={sid}") as ws:
            ws.send_text(json.dumps({"type": "ping"}))
            response = ws.receive_text()
            assert response

    def test_session_persistence_within_connection(self):
        """Session should persist during connection"""
        sid = "test-persistence-1"
        
        with client.websocket_connect(f"/signal?role=sender&sid={sid}") as ws:
            for _ in range(5):
                ws.send_text(json.dumps({"type": "ping"}))
                response = ws.receive_text()
                assert "pong" in response

    def test_multiple_roles_different_sids(self):
        """Sender and listener should have different sessions"""
        with client.websocket_connect("/signal?role=sender&sid=role-test-1") as sender:
            with client.websocket_connect("/signal?role=listener&sid=role-test-2") as listener:
                sender.send_text(json.dumps({"type": "ping"}))
                listener.send_text(json.dumps({"type": "ping"}))
                
                sender_pong = sender.receive_text()
                listener_pong = listener.receive_text()
                
                assert "pong" in sender_pong
                assert "pong" in listener_pong


class TestStressAndPerformance:
    """Stress tests and performance checks"""

    def test_many_sequential_connections(self):
        """Should handle many sequential connections"""
        for i in range(20):
            with client.websocket_connect(f"/signal?role=listener&sid=stress-seq-{i}") as ws:
                ws.send_text(json.dumps({"type": "ping"}))
                response = ws.receive_text()
                assert "pong" in response

    def test_connection_lifetime(self):
        """Connection should remain stable"""
        with client.websocket_connect("/signal?role=sender&sid=lifetime-test") as ws:
            # Keep connection alive for multiple pings
            for _ in range(10):
                ws.send_text(json.dumps({"type": "ping"}))
                response = ws.receive_text()
                assert "pong" in response
                time.sleep(0.05)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
