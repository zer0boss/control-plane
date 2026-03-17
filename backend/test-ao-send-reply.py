"""
Test simulating AO Plugin sending reply to Control Plane
"""
import asyncio
import json
import websockets

AO_PLUGIN_HOST = "127.0.0.1"
AO_PLUGIN_PORT = 18080

async def test_ao_send_reply():
    """
    Connect as Control Plane, receive message, then simulate AO sending reply.
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
            "id": "test-simulate-cp",
            "timestamp": int(asyncio.get_event_loop().time() * 1000),
            "payload": {
                "apiKey": "openclaw-ao-v2-server-key-change-me-in-production",
                "controlPlaneId": "test-simulate-control-plane",
                "version": "2.0.0"
            }
        }
        await ws.send(json.dumps(auth))
        print("2. Sent auth")

        # 3. Receive auth response
        auth_response = await ws.recv()
        auth_data = json.loads(auth_response)
        print(f"3. Auth success: {auth_data['payload']['success']}, connectionId={auth_data['payload'].get('connectionId')}")

        # 4. Now simulate AO Plugin sending a REPLY message
        print("\n4. Simulating AO Plugin sending REPLY message...")

        # This is what AO Plugin should send when LLM replies
        reply_message = {
            "type": "reply",
            "inReplyTo": "test-message-id",
            "id": "ao-reply-123",
            "sessionId": "test-session-123",
            "content": "这是模拟的 LLM 回复",
            "from": {
                "id": "ao-plugin",
                "name": "AO Plugin",
                "type": "agent"
            },
            "metadata": {
                "channel": "ao",
                "instance_id": "test-instance"
            }
        }

        print(f"   Sending reply: {json.dumps(reply_message, ensure_ascii=False)}")
        await ws.send(json.dumps(reply_message))
        print("   Reply sent!")

        # 5. Wait to see if we receive anything back (like pong or acknowledgment)
        print("\n5. Waiting for any response (5 seconds)...")
        try:
            for i in range(5):
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    msg_data = json.loads(msg)
                    print(f"   Received: type={msg_data.get('type')}, data={json.dumps(msg_data, ensure_ascii=False)[:200]}")
                except asyncio.TimeoutError:
                    print("   No response received")
                    break
        except Exception as e:
            print(f"   Error: {e}")

        print("\nTest complete!")

if __name__ == "__main__":
    asyncio.run(test_ao_send_reply())
