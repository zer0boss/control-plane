"""
Test full message flow: Control Plane -> AO Plugin -> OpenClaw -> Reply -> Control Plane
"""
import asyncio
import json
import websockets
import requests

AO_PLUGIN_HOST = "127.0.0.1"
AO_PLUGIN_PORT = 18080
CONTROL_PLANE_URL = "http://localhost:8000"

async def test_message_flow():
    # Step 1: Check current messages in Control Plane
    print("=" * 60)
    print("Step 1: Check current messages")
    print("=" * 60)

    r = requests.get(f"{CONTROL_PLANE_URL}/api/v1/messages?limit=3", timeout=5)
    if r.status_code == 200:
        messages = r.json()
        print(f"Current messages count: {messages.get('total', 0)}")
        for msg in messages.get('items', [])[:3]:
            print(f"  - {msg['role']}: {msg['content'][:50]}...")

    # Step 2: Connect to AO Plugin and send a message
    print("\n" + "=" * 60)
    print("Step 2: Connect to AO Plugin and send message")
    print("=" * 60)

    uri = f"ws://{AO_PLUGIN_HOST}:{AO_PLUGIN_PORT}"
    async with websockets.connect(uri) as ws:
        # Receive welcome
        welcome = await ws.recv()
        print(f"Received welcome: {json.loads(welcome)['type']}")

        # Send auth
        auth = {
            "type": "auth",
            "id": "test-flow-auth",
            "timestamp": 1773600000000,
            "payload": {
                "apiKey": "openclaw-ao-v2-server-key-change-me-in-production",
                "controlPlaneId": "test-flow-cp",
                "version": "2.0.0"
            }
        }
        await ws.send(json.dumps(auth))
        print("Sent auth")

        # Receive auth response
        auth_response = await ws.recv()
        auth_data = json.loads(auth_response)
        print(f"Auth response: success={auth_data.get('payload', {}).get('success')}")

        # Send chat message with unique ID
        test_id = f"test-chat-{asyncio.get_event_loop().time()}"
        chat = {
            "type": "chat",
            "id": test_id,
            "sessionId": f"test-session-{asyncio.get_event_loop().time()}",
            "content": f"Test message at {asyncio.get_event_loop().time()}",
            "from": {
                "id": "test-flow-cp",
                "name": "Test Flow CP",
                "type": "user"
            },
            "metadata": {"channel": "ao"}
        }
        await ws.send(json.dumps(chat))
        print(f"Sent chat message: {test_id}")

        # Wait for reply
        print("\nWaiting for reply (15 seconds)...")
        try:
            reply = await asyncio.wait_for(ws.recv(), timeout=15.0)
            reply_data = json.loads(reply)
            print(f"Received reply: type={reply_data.get('type')}, content={reply_data.get('content', '')[:100]}...")
        except asyncio.TimeoutError:
            print("TIMEOUT: No reply received from AO Plugin")

    # Step 3: Check messages again
    print("\n" + "=" * 60)
    print("Step 3: Check messages after test")
    print("=" * 60)

    r = requests.get(f"{CONTROL_PLANE_URL}/api/v1/messages?limit=5", timeout=5)
    if r.status_code == 200:
        messages = r.json()
        print(f"Total messages: {messages.get('total', 0)}")
        for msg in messages.get('items', [])[:5]:
            print(f"  - {msg['role']}: {msg['content'][:50]}...")

if __name__ == "__main__":
    asyncio.run(test_message_flow())
