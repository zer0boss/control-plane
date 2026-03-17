"""
测试 Python websockets 能否收到 AO Plugin 的 reply
"""
import asyncio
import json
import websockets

async def test():
    url = "ws://127.0.0.1:18080"
    api_key = "openclaw-ao-v2-server-key-change-me-in-production"

    print(f"[Python] Connecting to {url}...")

    try:
        async with websockets.connect(
            url,
            ping_interval=20,
            ping_timeout=10,
        ) as ws:
            print("[Python] Connected!")

            # 等待 welcome
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=5)
                data = json.loads(msg)
                print(f"[Python] Received: type={data.get('type')}")
            except asyncio.TimeoutError:
                print("[Python] No welcome message, continuing...")

            # 发送 auth
            auth_msg = {
                "id": "python-test-auth",
                "type": "auth",
                "timestamp": 1773678607805,
                "payload": {
                    "apiKey": api_key,
                    "controlPlaneId": "python-test"
                }
            }
            print("[Python] Sending auth...")
            await ws.send(json.dumps(auth_msg))

            # 等待 auth_response
            msg = await ws.recv()
            data = json.loads(msg)
            print(f"[Python] Received: type={data.get('type')}, connectionId={data.get('payload', {}).get('connectionId')}")

            # 发送 chat 消息
            chat_msg = {
                "id": "python-test-chat",
                "type": "chat",
                "timestamp": 1773678607805,
                "sessionId": "python-test-session",
                "content": "hello from python",
                "from": {"id": "python-tester", "name": "Python Tester"}
            }
            print("[Python] Sending chat message...")
            await ws.send(json.dumps(chat_msg))

            # 等待消息循环
            print("[Python] Waiting for messages...")
            message_count = 0
            while message_count < 10:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=10)
                    data = json.loads(msg)
                    msg_type = data.get("type")
                    print(f"[Python] Received message #{message_count + 1}: type={msg_type}")

                    if msg_type == "reply":
                        print(f"[Python] *** REPLY RECEIVED! ***")
                        print(f"[Python]   content: {data.get('content', '')[:100]}")
                        print(f"[Python]   sessionId: {data.get('sessionId')}")
                        break

                    message_count += 1
                except asyncio.TimeoutError:
                    print("[Python] Timeout waiting for message")
                    break

    except Exception as e:
        print(f"[Python] Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())