"""
使用和 Control Plane 完全相同配置的测试脚本
"""
import asyncio
import json
import websockets
import sys
import time

async def test_with_cp_config():
    url = "ws://127.0.0.1:18080"
    api_key = "openclaw-ao-v2-server-key-change-me-in-production"

    print(f"[CP-Test] Connecting with CP config...", flush=True)

    # 使用和 Control Plane 完全相同的配置
    async with websockets.connect(
        url,
        ping_interval=20,
        ping_timeout=10,
        close_timeout=5,
    ) as ws:
        print(f"[CP-Test] Connected!", flush=True)

        # 等待 welcome
        msg = await ws.recv()
        data = json.loads(msg)
        print(f"[CP-Test] Got: {data.get('type')}", flush=True)

        # 发送 auth
        auth_msg = {
            "id": "cp-test-auth",
            "type": "auth",
            "timestamp": int(time.time() * 1000),
            "payload": {
                "apiKey": api_key,
                "controlPlaneId": "cp-test-connection",
                "version": "2.0.0"
            }
        }
        await ws.send(json.dumps(auth_msg))
        print(f"[CP-Test] Sent auth", flush=True)

        # 等待 auth_response
        msg = await ws.recv()
        data = json.loads(msg)
        conn_id = data.get('payload', {}).get('connectionId')
        print(f"[CP-Test] Auth OK, connectionId={conn_id}", flush=True)

        # 启动心跳任务
        heartbeat_id = 0
        async def heartbeat_loop():
            nonlocal heartbeat_id
            while True:
                await asyncio.sleep(20)
                ping_msg = {
                    "type": "ping",
                    "id": f"heartbeat-{heartbeat_id}",
                }
                await ws.send(json.dumps(ping_msg))
                print(f"[CP-Test] Sent heartbeat-{heartbeat_id}", flush=True)
                heartbeat_id += 1

        heartbeat_task = asyncio.create_task(heartbeat_loop())

        # 发送 chat 消息
        chat_msg = {
            "id": "cp-test-chat",
            "type": "chat",
            "timestamp": int(time.time() * 1000),
            "sessionId": "cp-test-session",
            "content": "test with CP config",
            "from": {
                "id": "control_plane",
                "name": "Control Plane",
                "type": "user"
            },
            "metadata": {
                "channel": "ao"
            }
        }
        await ws.send(json.dumps(chat_msg))
        print(f"[CP-Test] Sent chat message", flush=True)

        # 消息循环
        print(f"[CP-Test] Starting message loop...", flush=True)
        message_count = 0
        while message_count < 20:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=30)
                data = json.loads(msg)
                msg_type = data.get("type")
                print(f"[CP-Test] Message #{message_count + 1}: type={msg_type}", flush=True)

                if msg_type == "reply":
                    print(f"[CP-Test] *** REPLY RECEIVED! ***", flush=True)
                    print(f"[CP-Test]   inReplyTo: {data.get('inReplyTo')}", flush=True)
                    print(f"[CP-Test]   sessionId: {data.get('sessionId')}", flush=True)
                    break

                if msg_type == "pong":
                    print(f"[CP-Test]   pong for: {data.get('inReplyTo')}", flush=True)

                message_count += 1
            except asyncio.TimeoutError:
                print(f"[CP-Test] Timeout!", flush=True)
                break
            except Exception as e:
                print(f"[CP-Test] Error: {e}", flush=True)
                break

        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass

if __name__ == "__main__":
    asyncio.run(test_with_cp_config())