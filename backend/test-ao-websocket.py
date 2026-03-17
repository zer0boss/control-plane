"""
Test AO Plugin WebSocket connection directly
"""
import asyncio
import json
import websockets

AO_PLUGIN_HOST = "127.0.0.1"
AO_PLUGIN_PORT = 18080

async def test_ao_plugin():
    uri = f"ws://{AO_PLUGIN_HOST}:{AO_PLUGIN_PORT}"
    print(f"Connecting to {uri}...")

    try:
        async with websockets.connect(uri) as ws:
            # Receive welcome message
            welcome = await ws.recv()
            print(f"Received: {welcome}")

            # Send auth
            auth = {
                "type": "auth",
                "id": "test-auth-123",
                "timestamp": 1773600000000,
                "payload": {
                    "apiKey": "openclaw-ao-v2-server-key-change-me-in-production",
                    "controlPlaneId": "test-client",
                    "version": "2.0.0"
                }
            }
            await ws.send(json.dumps(auth))
            print(f"Sent auth: {json.dumps(auth, indent=2)}")

            # Receive auth response
            auth_response = await ws.recv()
            print(f"Received: {auth_response}")

            # Send a chat message
            chat = {
                "type": "chat",
                "id": "test-chat-123",
                "sessionId": "test-session",
                "content": "hello from test script",
                "from": {
                    "id": "test-client",
                    "name": "Test Client",
                    "type": "user"
                },
                "metadata": {
                    "channel": "ao"
                }
            }
            await ws.send(json.dumps(chat))
            print(f"Sent chat: {json.dumps(chat, indent=2)}")

            # Wait for reply (with timeout)
            print("\nWaiting for reply (5 seconds timeout)...")
            try:
                reply = await asyncio.wait_for(ws.recv(), timeout=5.0)
                print(f"Received reply: {reply}")
            except asyncio.TimeoutError:
                print("Timeout: No reply received from AO Plugin")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_ao_plugin())
