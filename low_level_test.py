"""
底层 WebSocket 测试 - 检查是否真的收到了数据
"""
import asyncio
import json
import websockets
import sys
import time

async def low_level_test():
    url = "ws://127.0.0.1:18080"
    api_key = "openclaw-ao-v2-server-key-change-me-in-production"

    print(f"[Low] Connecting...", flush=True)

    async with websockets.connect(
        url,
        ping_interval=20,
        ping_timeout=10,
    ) as ws:
        print(f"[Low] Connected!", flush=True)

        # 等待 welcome
        msg = await ws.recv()
        print(f"[Low] Got: {json.loads(msg).get('type')}", flush=True)

        # 发送 auth
        await ws.send(json.dumps({
            "id": "low-auth",
            "type": "auth",
            "timestamp": int(time.time() * 1000),
            "payload": {"apiKey": api_key, "controlPlaneId": "low-test"}
        }))

        # 等待 auth_response
        msg = await ws.recv()
        data = json.loads(msg)
        conn_id = data.get('payload', {}).get('connectionId')
        print(f"[Low] Auth OK, connectionId={conn_id}", flush=True)

        # 发送 chat 消息
        await ws.send(json.dumps({
            "id": "low-chat",
            "type": "chat",
            "timestamp": int(time.time() * 1000),
            "sessionId": "low-session",
            "content": "low level test",
            "from": {"id": "low-test", "name": "Low Test"}
        }))
        print(f"[Low] Sent chat", flush=True)

        # 接收所有消息
        print(f"[Low] Waiting for messages...", flush=True)
        received_messages = []

        async def receive_loop():
            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=15)
                    data = json.loads(msg)
                    msg_type = data.get("type")
                    received_messages.append((time.time(), msg_type, data))
                    print(f"[Low] [{time.time():.3f}] Received: {msg_type}", flush=True)

                    if msg_type == "reply":
                        print(f"[Low] *** REPLY FOUND! ***", flush=True)
                        return True
                except asyncio.TimeoutError:
                    print(f"[Low] Timeout", flush=True)
                    return False
                except Exception as e:
                    print(f"[Low] Error: {e}", flush=True)
                    return False

        got_reply = await receive_loop()

        print(f"\n[Low] === Summary ===", flush=True)
        print(f"[Low] Total messages received: {len(received_messages)}", flush=True)
        for ts, msg_type, _ in received_messages:
            print(f"[Low]   {ts:.3f}: {msg_type}", flush=True)
        print(f"[Low] Reply received: {got_reply}", flush=True)

if __name__ == "__main__":
    asyncio.run(low_level_test())