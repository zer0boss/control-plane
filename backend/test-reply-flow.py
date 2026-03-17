"""
Test: Send message through Control Plane and verify reply is received
"""
import asyncio
import json
import requests
import websockets

CONTROL_PLANE_HOST = "http://localhost:8000"
AO_PLUGIN_HOST = "127.0.0.1"
AO_PLUGIN_PORT = 18080

def test_send_via_api():
    """Send a message through Control Plane API."""
    print("=== Step 1: Create session ===")
    # Get instance ID first
    response = requests.get(f"{CONTROL_PLANE_HOST}/api/v1/instances")
    instances = response.json()
    instance_id = instances['items'][0]['id'] if instances.get('items') else None
    print(f"Using instance: {instance_id}")

    response = requests.post(f"{CONTROL_PLANE_HOST}/api/v1/sessions", json={
        "instance_id": instance_id,
        "target": "test-session-reply-flow",
        "metadata": {"test": "reply-flow"}
    })
    session = response.json()
    session_id = session.get('id')
    print(f"Created session: {session_id}")

    print("\n=== Step 2: Get instances ===")
    response = requests.get(f"{CONTROL_PLANE_HOST}/api/v1/instances")
    instances = response.json()
    print(f"Instances: {json.dumps(instances, indent=2)}")

    for item in instances.get('items', []):
        print(f"\nInstance: {item['name']} ({item['id']})")
        print(f"  Status: {item['status']}")
        health = item.get('health', {})
        print(f"  Health: {health}")

    if not session_id:
        print("ERROR: Failed to create session")
        return None

    return session_id

async def test_listen_for_reply(session_id):
    """Connect to AO Plugin and listen for reply."""
    uri = f"ws://{AO_PLUGIN_HOST}:{AO_PLUGIN_PORT}"
    print(f"\n=== Step 3: Connecting to AO Plugin ===")

    async with websockets.connect(uri) as ws:
        # Receive welcome
        welcome = await ws.recv()
        print(f"Received: {json.loads(welcome)['type']}")

        # Send auth
        auth = {
            "type": "auth",
            "id": "test-reply-flow",
            "timestamp": int(asyncio.get_event_loop().time() * 1000),
            "payload": {
                "apiKey": "openclaw-ao-v2-server-key-change-me-in-production",
                "controlPlaneId": "test-reply-flow-cp",
                "version": "2.0.0"
            }
        }
        await ws.send(json.dumps(auth))
        print("Sent auth")

        # Receive auth response
        auth_response = await ws.recv()
        auth_data = json.loads(auth_response)
        print(f"Auth success: {auth_data['payload']['success']}, connectionId={auth_data['payload'].get('connectionId')}")

        print("\n=== Step 4: Waiting for reply messages (10 seconds) ===")
        print("(Now send a message through Control Plane API...)")

        reply_received = False
        try:
            for i in range(10):
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    msg_data = json.loads(msg)
                    msg_type = msg_data.get('type')
                    print(f"   Received: type={msg_type}")
                    if msg_type == 'reply':
                        content = msg_data.get('content', '')
                        in_reply_to = msg_data.get('inReplyTo', 'N/A')
                        session_id = msg_data.get('sessionId', 'N/A')
                        print(f"   REPLY content: {content.encode('utf-8', errors='replace').decode('gbk', errors='replace')}")
                        print(f"   REPLY inReplyTo: {in_reply_to}")
                        print(f"   REPLY sessionId: {session_id}")
                        reply_received = True
                except asyncio.TimeoutError:
                    print("   (waiting...)")
                except UnicodeEncodeError as e:
                    print(f"   Encoding error (continuing): {e}")
                    reply_received = True
        except Exception as e:
            print(f"   Error: {e}")

        return reply_received

if __name__ == "__main__":
    session_id = test_send_via_api()
    if session_id:
        print(f"\nSession created: {session_id}")
        print(f"Now sending message to session...")

        # Send a message to the session
        response = requests.post(
            f"{CONTROL_PLANE_HOST}/api/v1/sessions/{session_id}/messages",
            json={
                "content": "test message",
                "from": {"id": "test", "name": "Test", "type": "user"}
            }
        )
        print(f"Send message result: {response.status_code} - {response.text}")

        # Listen for replies
        reply_received = asyncio.run(test_listen_for_reply(session_id))
        print(f"\n=== Result: Reply {'RECEIVED' if reply_received else 'NOT received'} ===")
