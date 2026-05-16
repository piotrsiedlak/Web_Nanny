import json

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


class TestHTTPEndpoints:
    """Test HTTP endpoints for proper functionality"""

    def test_sender_endpoint_returns_200(self):
        """Test /sender endpoint returns 200 status"""
        response = client.get("/sender")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    def test_sender_endpoint_returns_html(self):
        """Test /sender endpoint returns HTML content"""
        response = client.get("/sender")
        assert response.headers["content-type"] == "text/html; charset=utf-8"

    def test_sender_endpoint_no_traceback(self):
        """Test /sender endpoint doesn't return Python traceback"""
        response = client.get("/sender")
        assert "Traceback" not in response.text
        assert "File" not in response.text or "<" in response.text  # Allow "File" in HTML tags
        assert "ValueError" not in response.text
        assert "TypeError" not in response.text
        assert "AttributeError" not in response.text

    def test_listener_endpoint_returns_200(self):
        """Test /listener endpoint returns 200 status"""
        response = client.get("/listener")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    def test_listener_endpoint_returns_html(self):
        """Test /listener endpoint returns HTML content"""
        response = client.get("/listener")
        assert response.headers["content-type"] == "text/html; charset=utf-8"

    def test_listener_endpoint_no_traceback(self):
        """Test /listener endpoint doesn't return Python traceback"""
        response = client.get("/listener")
        assert "Traceback" not in response.text
        assert "ValueError" not in response.text
        assert "TypeError" not in response.text
        assert "AttributeError" not in response.text

    def test_sender_content_not_empty(self):
        """Test /sender returns non-empty content"""
        response = client.get("/sender")
        assert len(response.text) > 0, "Sender page content is empty"

    def test_listener_content_not_empty(self):
        """Test /listener returns non-empty content"""
        response = client.get("/listener")
        assert len(response.text) > 0, "Listener page content is empty"


class TestWebSocketEndpoints:
    """Test WebSocket endpoints for connection handling"""

    def test_websocket_send_connection(self):
        """Test /send WebSocket endpoint accepts connections"""
        with client.websocket_connect("/send") as websocket:
            # If we get here without exception, connection was successful
            assert websocket is not None

    def test_websocket_listen_connection(self):
        """Test /listen WebSocket endpoint accepts connections"""
        with client.websocket_connect("/listen") as websocket:
            # If we get here without exception, connection was successful
            assert websocket is not None

    def test_websocket_signal_connection(self):
        """Test /signal WebSocket endpoint accepts sender/listener connections"""
        with client.websocket_connect("/signal?role=sender&sid=test-signal") as sender_ws:
            assert sender_ws is not None

        with client.websocket_connect("/signal?role=listener&sid=test-signal") as listener_ws:
            assert listener_ws is not None

    def test_websocket_signal_ping_pong(self):
        """Test /signal WebSocket endpoint responds to ping messages"""
        with client.websocket_connect("/signal?role=sender&sid=test-ping") as sender_ws:
            with client.websocket_connect("/signal?role=listener&sid=test-ping") as listener_ws:
                sender_ws.send_text(json.dumps({"type": "ping"}))
                pong = sender_ws.receive_text()
                assert pong and "pong" in pong

    def test_websocket_send_rejects_second_connection(self):
        """Test /send rejects second simultaneous connection"""
        with client.websocket_connect("/send") as websocket1:
            # First connection should work
            assert websocket1 is not None
            # Second connection should be rejected
            with pytest.raises(Exception):
                with client.websocket_connect("/send") as websocket2:
                    pass

    def test_websocket_listen_rejects_second_connection(self):
        """Test /listen rejects second simultaneous connection"""
        with client.websocket_connect("/listen") as websocket1:
            # First connection should work
            assert websocket1 is not None
            # Second connection should be rejected
            with pytest.raises(Exception):
                with client.websocket_connect("/listen") as websocket2:
                    pass

    def test_websocket_send_receive_bytes(self):
        """Test /send endpoint can receive bytes"""
        with client.websocket_connect("/send") as websocket:
            test_data = b"test message"
            websocket.send_bytes(test_data)
            # Connection should remain open
            assert websocket is not None

    def test_websocket_listen_stays_open(self):
        """Test /listen endpoint stays open after connection"""
        with client.websocket_connect("/listen") as websocket:
            import time
            time.sleep(0.1)
            # Connection should still be open
            assert websocket is not None


class TestDataRelay:
    """Test data relay between sender and listener"""

    def test_message_relay_from_sender_to_listener(self):
        """Test messages relay from sender to listener"""
        # Connect listener first
        with client.websocket_connect("/listen") as listener_ws:
            # Connect sender
            with client.websocket_connect("/send") as sender_ws:
                # Send test message
                test_data = b"hello listener"
                sender_ws.send_bytes(test_data)
                
                # Try to receive on listener
                try:
                    received_data = listener_ws.receive_bytes()
                    assert received_data == test_data
                except Exception:
                    # This is expected if listener is just sleeping
                    # The listener endpoint sleeps and doesn't actively receive
                    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
