#!/bin/bash
# Control Plane Connection Test Script
# Tests the complete flow: register instance -> connect -> create session -> send message

set -e

CONTROL_PLANE_URL="http://localhost:8000"
API_KEY="openclaw-ao-v2-server-key-change-me-in-production"

echo "=========================================="
echo "Control Plane Connection Test"
echo "=========================================="
echo ""

# Test 1: Health Check
echo "[TEST 1] Checking Control Plane health..."
HEALTH=$(curl -s ${CONTROL_PLANE_URL}/health)
echo "Response: $HEALTH"
echo ""

# Test 2: Register Instance
echo "[TEST 2] Registering OpenClaw instance..."
INSTANCE_RESPONSE=$(curl -s -X POST ${CONTROL_PLANE_URL}/api/v1/instances \
  -H "Content-Type: application/json" \
  -d '{
    "name": "本地测试实例",
    "host": "127.0.0.1",
    "port": 18080,
    "channel_id": "ao",
    "credentials": {
      "auth_type": "token",
      "token": "'${API_KEY}'"
    }
  }')

INSTANCE_ID=$(echo $INSTANCE_RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")

if [ -z "$INSTANCE_ID" ]; then
    echo "ERROR: Failed to register instance"
    echo "Response: $INSTANCE_RESPONSE"
    exit 1
fi

echo "Instance registered successfully!"
echo "Instance ID: $INSTANCE_ID"
echo "Response: $INSTANCE_RESPONSE"
echo ""

# Test 3: Connect Instance
echo "[TEST 3] Connecting to instance..."
CONNECT_RESPONSE=$(curl -s -X POST ${CONTROL_PLANE_URL}/api/v1/instances/${INSTANCE_ID}/connect)
echo "Response: $CONNECT_RESPONSE"
echo ""

# Wait for connection
echo "Waiting for connection to establish..."
sleep 2

# Test 4: Check Instance Health
echo "[TEST 4] Checking instance health..."
HEALTH_RESPONSE=$(curl -s ${CONTROL_PLANE_URL}/api/v1/instances/${INSTANCE_ID}/health)
echo "Response: $HEALTH_RESPONSE"
echo ""

# Test 5: Create Session
echo "[TEST 5] Creating session..."
SESSION_RESPONSE=$(curl -s -X POST ${CONTROL_PLANE_URL}/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "instance_id": "'${INSTANCE_ID}'",
    "target": "test-session-001",
    "context": {
      "test": true,
      "timestamp": "'$(date -Iseconds)'"
    }
  }')

SESSION_ID=$(echo $SESSION_RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")

if [ -z "$SESSION_ID" ]; then
    echo "ERROR: Failed to create session"
    echo "Response: $SESSION_RESPONSE"
    exit 1
fi

echo "Session created successfully!"
echo "Session ID: $SESSION_ID"
echo "Response: $SESSION_RESPONSE"
echo ""

# Test 6: Send Message
echo "[TEST 6] Sending message..."
MESSAGE_RESPONSE=$(curl -s -X POST ${CONTROL_PLANE_URL}/api/v1/sessions/${SESSION_ID}/messages \
  -H "Content-Type: application/json" \
  -d '{
    "content": "你好，OpenClaw！这是一个测试消息。",
    "stream": false,
    "timeout": 60
  }')
echo "Response: $MESSAGE_RESPONSE"
echo ""

# Test 7: Get Message History
echo "[TEST 7] Getting message history..."
HISTORY_RESPONSE=$(curl -s ${CONTROL_PLANE_URL}/api/v1/sessions/${SESSION_ID}/messages)
echo "Response: $HISTORY_RESPONSE"
echo ""

# Test 8: List All Instances
echo "[TEST 8] Listing all instances..."
INSTANCES_LIST=$(curl -s ${CONTROL_PLANE_URL}/api/v1/instances)
echo "Response: $INSTANCES_LIST"
echo ""

# Test 9: System Status
echo "[TEST 9] Getting system status..."
SYSTEM_STATUS=$(curl -s ${CONTROL_PLANE_URL}/api/v1/system/status)
echo "Response: $SYSTEM_STATUS"
echo ""

echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo "Instance ID: $INSTANCE_ID"
echo "Session ID: $SESSION_ID"
echo ""
echo "All tests completed!"
echo ""
echo "Cleanup commands:"
echo "  # Close session:"
echo "  curl -X DELETE ${CONTROL_PLANE_URL}/api/v1/sessions/${SESSION_ID}"
echo ""
echo "  # Disconnect instance:"
echo "  curl -X POST ${CONTROL_PLANE_URL}/api/v1/instances/${INSTANCE_ID}/disconnect"
echo ""
echo "  # Delete instance:"
echo "  curl -X DELETE ${CONTROL_PLANE_URL}/api/v1/instances/${INSTANCE_ID}"
