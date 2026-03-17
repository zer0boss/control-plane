"""
实时测试 - 发送消息并监控 WebSocket
"""
import asyncio
import json
import websockets
import sys

async def test():
    url = "ws://127.0.0.1:18080"
    api_key = "openclaw-ao-v2-server-key-change-me-in-production"

    print(f"[Test] Connecting to {url}...", flush=True)

    async with websockets.connect(
        url,
        ping_interval=20,
        ping_timeout=10,
    ) as ws:
        print("[Test] Connected!", flush=True)

        # 等待 welcome
        msg = await ws.recv()
        data = json.loads(msg)
        print(f"[Test] Got: {data.get('type')}", flush=True)

        # 发送 auth
        auth_msg = {
            "id": "live-test-auth",
            "type": "auth",
            "timestamp": int(asyncio.get_event_loop().time() * 1000),
            "payload": {
                "apiKey": api_key,
                "controlPlaneId": "live-monitor"
            }
        }
        await ws.send(json.dumps(auth_msg))
        print("[Test] Sent auth", flush=True)

        # 等待 auth_response
        msg = await ws.recv()
        data = json.loads(msg)
        conn_id = data.get('payload', {}).get('connectionId')
        print(f"[Test] Auth OK, connectionId={conn_id}", flush=True)

        # 发送 chat
        chat_msg = {
            "id": "live-test-chat",
            "type": "chat",
            "timestamp": int(asyncio.get_event_loop().time() * 1000),
            "sessionId": "live-test-session",
            "content": "live monitor test",
            "from": {"id": "live-monitor", "name": "Live Monitor"}
        }
        await ws.send(json.dumps(chat_msg))
        print(f"[Test] Sent chat message", flush=True)

        # 等待消息
        print("[Test] Waiting for messages...", flush=True)
        while True:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=30)
                data = json.loads(msg)
                msg_type = data.get("type")
                print(f"[Test] Received: type={msg_type}", flush=True)

                if msg_type == "reply":
                    print(f"[Test] *** REPLY CONTENT: {data.get('content', '')[:50]} ***", flush=True)
                    break
            except asyncio.TimeoutError:
                print("[Test] Timeout!", flush=True)
                break

if __name__ == "__main__":
    asyncio.run(test())