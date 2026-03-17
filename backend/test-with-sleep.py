"""
Test AO Plugin with sleep to keep connection alive
"""
import asyncio
import json
import websockets

AO_PLUGIN_HOST = "127.0.0.1"
AO_PLUGIN_PORT = 18080

async def test_with_sleep():
    uri = f"ws://{AO_PLUGIN_HOST}:{AO_PLUGIN_PORT}"
    print(f"Connecting to {uri}...")

    try:
        async with websockets.connect(uri) as ws:
            # 1. Receive welcome message
            welcome = await ws.recv()
            print(f"1. Welcome: {json.loads(welcome)['type']}")

            # 2. Send auth
            auth = {
                "type": "auth",
                "id": "test-auth-sleep",
                "timestamp": 1773600000000,
                "payload": {
                    "apiKey": "openclaw-ao-v2-server-key-change-me-in-production",
                    "controlPlaneId": "test-sleep-client",
                    "version": "2.0.0"
                }
            }
            await ws.send(json.dumps(auth))
            print(f"2. Sent auth")

            # 3. Receive auth response
            auth_response = await ws.recv()
            auth_data = json.loads(auth_response)
            print(f"3. Auth response: success={auth_data.get('payload', {}).get('success')}, connectionId={auth_data.get('payload', {}).get('connectionId')}")

            # 4. Send chat message
            chat = {
                "type": "chat",
                "id": "test-chat-sleep",
                "sessionId": "test-session-sleep",
                "content": "你好，请回复",
                "from": {
                    "id": "test-sleep-client",
                    "name": "Test Sleep Client",
                    "type": "user"
                },
                "metadata": {
                    "channel": "ao"
                }
            }
            await ws.send(json.dumps(chat))
            print(f"4. Sent chat message: {chat['content']}")

            # 5. Wait for reply with longer timeout
            print(f"5. Waiting for reply (60 seconds)...")
            reply_received = False

            for i in range(60):
                try:
                    reply = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    reply_data = json.loads(reply)
                    print(f"\n   *** Received: type={reply_data.get('type')}, content={reply_data.get('content', '')[:100]}...")
                    reply_received = True
                    break
                except asyncio.TimeoutError:
                    if (i + 1) % 10 == 0:
                        print(f"   ... still waiting ({i+1}s)")

            # 6. If no reply, keep connection alive and wait more
            if not reply_received:
                print(f"\n   No reply received. Sending ping to keep connection alive...")
                ping = {"type": "ping", "id": "keepalive-1"}
                await ws.send(json.dumps(ping))

                # Wait for pong
                try:
                    pong = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    print(f"   Received pong: {json.loads(pong)}")
                except:
                    print(f"   No pong received")

                # Continue waiting for reply
                print(f"   Continuing to wait for reply (30 more seconds)...")
                for i in range(30):
                    try:
                        reply = await asyncio.wait_for(ws.recv(), timeout=1.0)
                        reply_data = json.loads(reply)
                        print(f"\n   *** Received: type={reply_data.get('type')}, content={reply_data.get('content', '')[:100]}...")
                        reply_received = True
                        break
                    except asyncio.TimeoutError:
                        pass

            print(f"\nResult: {'SUCCESS' if reply_received else 'FAILED - No reply received'}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_with_sleep())
