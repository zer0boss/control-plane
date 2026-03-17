"""
Test: Direct send to Control Plane's WebSocket connection
"""
import asyncio
import json
import websockets
import requests

AO_PLUGIN_HOST = "127.0.0.1"
AO_PLUGIN_PORT = 18080

async def test_direct_send():
    """
    Connect to AO Plugin and send a reply message to the Control Plane.
    """
    uri = f"ws://{AO_PLUGIN_HOST}:{AO_PLUGIN_PORT}"
    print(f"Connecting to {uri}...")

    async with websockets.connect(uri) as ws:
        # 1. Receive welcome
        welcome = await ws.recv()
        print(f"1. Received: {json.loads(welcome)['type']}")

        # 2. Send auth (same key as Control Plane uses)
        auth = {
            "type": "auth",
            "id": "test-direct-send",
            "timestamp": int(asyncio.get_event_loop().time() * 1000),
            "payload": {
                "apiKey": "openclaw-ao-v2-server-key-change-me-in-production",
                "controlPlaneId": "test-direct-send-cp",
                "version": "2.0.0"
            }
        }
        await ws.send(json.dumps(auth))
        print("2. Sent auth")

        # 3. Receive auth response
        auth_response = await ws.recv()
        auth_data = json.loads(auth_response)
        print(f"3. Auth success: {auth_data['payload']['success']}, connectionId={auth_data['payload'].get('connectionId')}")

        # 4. Send reply message (this is what AO Plugin sends when LLM replies)
        print("\n4. Sending reply message to Control Plane...")
        reply_message = {
            "type": "reply",
            "inReplyTo": "test-message-123",
            "id": "ao-reply-direct",
            "sessionId": "test-session-direct",
            "content": "This is a direct test reply from simulated AO Plugin",
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
        await ws.send(json.dumps(reply_message))
        print(f"   Sent reply: {json.dumps(reply_message, ensure_ascii=False)}")

        # 5. Wait to see if there's any acknowledgment
        print("\n5. Waiting for any response (3 seconds)...")
        try:
            for i in range(3):
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    msg_data = json.loads(msg)
                    print(f"   Received: type={msg_data.get('type')}, data={json.dumps(msg_data, ensure_ascii=False)[:200]}")
                except asyncio.TimeoutError:
                    print("   No response (expected - Control Plane doesn't send ack)")
                    break
        except Exception as e:
            print(f"   Error: {e}")

        print("\nTest complete! Check Control Plane logs to see if it received the reply.")

if __name__ == "__main__":
    asyncio.run(test_direct_send())
