"""
Check AO Plugin configuration and status
"""
import asyncio
import requests
import json

AO_PLUGIN_HOST = "127.0.0.1"
AO_PLUGIN_PORT = 18080

async def check_ao_plugin():
    # Check if AO Plugin WebSocket server is reachable
    try:
        # Try to connect to WebSocket
        import websockets
        uri = f"ws://{AO_PLUGIN_HOST}:{AO_PLUGIN_PORT}"
        async with websockets.connect(uri) as ws:
            # Receive welcome message
            welcome = await ws.recv()
            print(f"Welcome: {welcome}")

            # Send auth with test key
            auth = {
                "type": "auth",
                "id": "test-123",
                "timestamp": 1773600000000,
                "payload": {
                    "apiKey": "openclaw-ao-v2-server-key-change-me-in-production",
                    "controlPlaneId": "test-client",
                    "version": "2.0.0"
                }
            }
            await ws.send(json.dumps(auth))
            print(f"Sent auth: {auth}")

            # Receive auth response
            auth_response = await ws.recv()
            print(f"Auth response: {auth_response}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_ao_plugin())
