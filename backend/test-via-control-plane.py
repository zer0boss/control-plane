"""
Test sending message through Control Plane's AO Plugin connection
"""
import asyncio
import websockets
import json

AO_PLUGIN_HOST = "127.0.0.1"
AO_PLUGIN_PORT = 18080

async def test_via_control_plane():
    """
    Connect to AO Plugin and send a message.
    Control Plane should receive the reply and store it in the database.
    """
    uri = f"ws://{AO_PLUGIN_HOST}:{AO_PLUGIN_PORT}"
    print(f"Connecting to {uri}...")

    async with websockets.connect(uri) as ws:
        # 1. Receive welcome
        welcome = await ws.recv()
        print(f"1. Received: {json.loads(welcome)['type']}")

        # 2. Send auth (same key as Control Plane)
        auth = {
            "type": "auth",
            "id": "test-via-cp",
            "timestamp": int(asyncio.get_event_loop().time() * 1000),
            "payload": {
                "apiKey": "openclaw-ao-v2-server-key-change-me-in-production",
                "controlPlaneId": "test-via-control-plane",
                "version": "2.0.0"
            }
        }
        await ws.send(json.dumps(auth))
        print("2. Sent auth")

        # 3. Receive auth response
        auth_response = await ws.recv()
        auth_data = json.loads(auth_response)
        print(f"3. Auth success: {auth_data['payload']['success']}")

        # 4. Send chat message
        chat = {
            "type": "chat",
            "id": "test-chat-cp-flow",
            "sessionId": "test-session-cp-flow",
            "content": "测试消息，请简单回复",
            "from": {
                "id": "test-via-cp",
                "name": "Test Via CP",
                "type": "user"
            },
            "metadata": {"channel": "ao"}
        }
        await ws.send(json.dumps(chat))
        print(f"4. Sent chat: {chat['content']}")

        # 5. Wait for reply (up to 60 seconds)
        print("5. Waiting for reply (60 seconds)...")
        reply_received = False

        for i in range(60):
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                msg_data = json.loads(msg)
                msg_type = msg_data.get('type')

                if msg_type == 'ping':
                    # Send pong response
                    pong = {
                        "type": "pong",
                        "inReplyTo": msg_data.get('id'),
                        "timestamp": int(asyncio.get_event_loop().time() * 1000)
                    }
                    await ws.send(json.dumps(pong))
                    print(f"   Sent pong for ping")
                elif msg_type == 'reply':
                    print(f"\n   *** SUCCESS! Received reply ***")
                    print(f"   Content: {msg_data.get('content', '')[:200]}...")
                    print(f"   Full data: {json.dumps(msg_data, indent=2, ensure_ascii=False)}")
                    reply_received = True
                    break
                else:
                    print(f"   Received: type={msg_type}")
            except asyncio.TimeoutError:
                if (i + 1) % 10 == 0:
                    print(f"   ... waiting ({i+1}s)")

        print(f"\nResult: {'SUCCESS' if reply_received else 'FAILED - No reply received'}")
        return reply_received

if __name__ == "__main__":
    result = asyncio.run(test_via_control_plane())
    exit(0 if result else 1)
