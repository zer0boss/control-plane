"""
Test AO Plugin with detailed logging
"""
import asyncio
import json
import websockets

AO_PLUGIN_HOST = "127.0.0.1"
AO_PLUGIN_PORT = 18080

async def test_ao_detailed():
    uri = f"ws://{AO_PLUGIN_HOST}:{AO_PLUGIN_PORT}"
    print(f"Connecting to {uri}...")
    print("=" * 70)

    try:
        async with websockets.connect(uri) as ws:
            # 1. Receive welcome message
            welcome = await ws.recv()
            welcome_data = json.loads(welcome)
            print(f"1. Received welcome:")
            print(f"   type: {welcome_data.get('type')}")
            print(f"   payload: {welcome_data.get('payload')}")
            print()

            # 2. Send auth
            auth = {
                "type": "auth",
                "id": "test-auth-detailed",
                "timestamp": 1773600000000,
                "payload": {
                    "apiKey": "openclaw-ao-v2-server-key-change-me-in-production",
                    "controlPlaneId": "test-detailed-client",
                    "version": "2.0.0"
                }
            }
            await ws.send(json.dumps(auth))
            print(f"2. Sent auth:")
            print(f"   apiKey: {auth['payload']['apiKey']}")
            print(f"   controlPlaneId: {auth['payload']['controlPlaneId']}")
            print()

            # 3. Receive auth response
            auth_response = await ws.recv()
            auth_data = json.loads(auth_response)
            print(f"3. Received auth response:")
            print(f"   type: {auth_data.get('type')}")
            print(f"   inReplyTo: {auth_data.get('inReplyTo')}")
            print(f"   success: {auth_data.get('payload', {}).get('success')}")
            print(f"   connectionId: {auth_data.get('payload', {}).get('connectionId')}")
            print()

            # 4. Send chat message
            chat = {
                "type": "chat",
                "id": "test-chat-detailed",
                "sessionId": "test-session-detailed",
                "content": "你好，请回复",
                "from": {
                    "id": "test-detailed-client",
                    "name": "Test Detailed Client",
                    "type": "user"
                },
                "metadata": {
                    "channel": "ao"
                }
            }
            await ws.send(json.dumps(chat))
            print(f"4. Sent chat message:")
            print(f"   id: {chat['id']}")
            print(f"   sessionId: {chat['sessionId']}")
            print(f"   content: {chat['content']}")
            print(f"   from: {chat['from']}")
            print()

            # 5. Wait for reply with longer timeout and progress indication
            print(f"5. Waiting for reply (30 seconds)...")
            print(f"   Listening on WebSocket...")

            reply_received = False
            for i in range(30):
                try:
                    reply = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    reply_data = json.loads(reply)
                    print(f"\n   *** Received message ***")
                    print(f"   type: {reply_data.get('type')}")
                    print(f"   inReplyTo: {reply_data.get('inReplyTo')}")
                    print(f"   content: {reply_data.get('content', '')[:200]}...")
                    print(f"   full data: {json.dumps(reply_data, indent=2)}")
                    reply_received = True
                    break
                except asyncio.TimeoutError:
                    if (i + 1) % 5 == 0:
                        print(f"   ... still waiting ({i+1}s)")

            if not reply_received:
                print(f"\n   TIMEOUT: No reply received after 30 seconds")

            print()
            print("=" * 70)
            print(f"Result: {'SUCCESS - Reply received' if reply_received else 'FAILED - No reply received'}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_ao_detailed())
