"""
端到端测试 - 通过 Control Plane API 发送消息并检查回复
"""
import asyncio
import json
import websockets
import httpx
import time

CONTROL_PLANE_URL = "http://127.0.0.1:8100"
AO_PLUGIN_URL = "ws://127.0.0.1:18080"
API_KEY = "openclaw-ao-v2-server-key-change-me-in-production"

async def test_e2e():
    print("=" * 60)
    print("端到端测试 - Control Plane <-> AO Plugin")
    print("=" * 60)

    # 1. 获取实例列表
    print("\n[1] 获取实例列表...")
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{CONTROL_PLANE_URL}/api/v1/instances")
        instances = resp.json()
        print(f"    找到 {instances['total']} 个实例")

        if instances['total'] == 0:
            print("    ERROR: 没有实例!")
            return False

        instance = instances['items'][0]
        instance_id = instance['id']
        print(f"    实例: {instance['name']}, 状态: {instance['status']}, ID: {instance_id}")

    # 2. 确保 Control Plane 已连接
    if instance['status'] != 'connected':
        print("\n[2] 连接实例...")
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{CONTROL_PLANE_URL}/api/v1/instances/{instance_id}/connect")
            result = resp.json()
            print(f"    连接结果: {result}")
            await asyncio.sleep(2)
    else:
        print("\n[2] 实例已连接，跳过连接步骤")

    # 3. 通过 WebSocket 直接发送消息 (模拟前端)
    print("\n[3] 通过 WebSocket 发送测试消息...")

    async with websockets.connect(
        AO_PLUGIN_URL,
        ping_interval=20,
        ping_timeout=10,
    ) as ws:
        # 等待 welcome
        msg = await ws.recv()
        data = json.loads(msg)
        print(f"    收到 welcome: {data.get('type')}")

        # 发送 auth
        await ws.send(json.dumps({
            "id": "e2e-test-auth",
            "type": "auth",
            "timestamp": int(time.time() * 1000),
            "payload": {
                "apiKey": API_KEY,
                "controlPlaneId": "e2e-test"
            }
        }))

        # 等待 auth_response
        msg = await ws.recv()
        data = json.loads(msg)
        connection_id = data.get('payload', {}).get('connectionId')
        print(f"    认证成功, connectionId: {connection_id}")

        # 发送 chat 消息
        session_id = f"e2e-session-{int(time.time())}"
        await ws.send(json.dumps({
            "id": "e2e-test-chat",
            "type": "chat",
            "timestamp": int(time.time() * 1000),
            "sessionId": session_id,
            "content": "e2e test message - please reply",
            "from": {"id": "e2e-tester", "name": "E2E Test"}
        }))
        print(f"    发送 chat 消息, sessionId: {session_id}")

        # 等待回复
        print("\n[4] 等待 OpenClaw 回复...")
        received_reply = False
        timeout = 30
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=5)
                data = json.loads(msg)
                msg_type = data.get("type")
                elapsed = time.time() - start_time
                print(f"    [{elapsed:.1f}s] 收到消息类型: {msg_type}")

                if msg_type == "reply":
                    print(f"\n    *** 成功收到回复! ***")
                    print(f"    inReplyTo: {data.get('inReplyTo')}")
                    print(f"    sessionId: {data.get('sessionId')}")
                    print(f"    content: {data.get('content', '')[:100]}...")
                    received_reply = True
                    break
            except asyncio.TimeoutError:
                print(f"    等待中...")
                continue

    print("\n" + "=" * 60)
    if received_reply:
        print("✅ 测试通过! Control Plane 能正常收到 AO Plugin 的回复")
    else:
        print("❌ 测试失败! Control Plane 没有收到回复")
    print("=" * 60)

    return received_reply

if __name__ == "__main__":
    result = asyncio.run(test_e2e())
    exit(0 if result else 1)