"""
Test Control Plane message receiving
"""
import asyncio
import json
import websockets

AO_PLUGIN_HOST = "127.0.0.1"
AO_PLUGIN_PORT = 18080

async def test_receive_reply():
    """Test if Control Plane can receive reply messages from AO Plugin."""
    uri = f"ws://{AO_PLUGIN_HOST}:{AO_PLUGIN_PORT}"
    print(f"Connecting to {uri}...")

    async with websockets.connect(uri) as ws:
        # Receive welcome
        welcome = await ws.recv()
        print(f"1. Received welcome: {welcome}")

        # Send auth (simulate Control Plane)
        auth = {
            "type": "auth",
            "id": "test-cp-auth",
            "timestamp": 1773600000000,
            "payload": {
                "apiKey": "openclaw-ao-v2-server-key-change-me-in-production",
                "controlPlaneId": "test-control-plane",
                "version": "2.0.0"
            }
        }
        await ws.send(json.dumps(auth))
        print(f"2. Sent auth")

        # Receive auth response
        auth_response = await ws.recv()
        print(f"3. Received auth_response: {auth_response}")

        # Send chat message
        chat = {
            "type": "chat",
            "id": "test-chat-msg",
            "sessionId": "test-session-123",
            "content": "hello from test",
            "from": {
                "id": "test-cp",
                "name": "Test CP",
                "type": "user"
            },
            "metadata": {"channel": "ao"}
        }
        await ws.send(json.dumps(chat))
        print(f"4. Sent chat message")

        # Wait for reply (with longer timeout)
        print("5. Waiting for reply (10 seconds)...")
        try:
            reply = await asyncio.wait_for(ws.recv(), timeout=10.0)
            print(f"6. Received reply: {reply}")
        except asyncio.TimeoutError:
            print("6. TIMEOUT: No reply received")

        # Keep connection alive to check for delayed reply
        print("7. Keeping connection open for 5 more seconds...")
        await asyncio.sleep(5)
        try:
            ws.send(json.dumps({"type": "ping", "id": "keepalive"}))
            pong = await asyncio.wait_for(ws.recv(), timeout=2.0)
            print(f"8. Received: {pong}")
        except:
            pass

if __name__ == "__main__":
    asyncio.run(test_receive_reply())
