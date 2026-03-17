# Control Plane Connection Test Script (PowerShell)
# Tests the complete flow: register instance -> connect -> create session -> send message

$ErrorActionPreference = "Stop"

$CONTROL_PLANE_URL = "http://localhost:8000"
$API_KEY = "openclaw-ao-v2-server-key-change-me-in-production"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Control Plane Connection Test" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Test 1: Health Check
Write-Host "[TEST 1] Checking Control Plane health..." -ForegroundColor Yellow
try {
    $HEALTH = Invoke-RestMethod -Uri "$CONTROL_PLANE_URL/health" -Method GET
    Write-Host "Response: $($HEALTH | ConvertTo-Json -Compress)" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Control Plane is not running. Please start it first." -ForegroundColor Red
    exit 1
}
Write-Host ""

# Test 2: Register Instance
Write-Host "[TEST 2] Registering OpenClaw instance..." -ForegroundColor Yellow
$INSTANCE_BODY = @{
    name = "本地测试实例"
    host = "127.0.0.1"
    port = 18080
    channel_id = "ao"
    credentials = @{
        auth_type = "token"
        token = $API_KEY
    }
} | ConvertTo-Json -Depth 10

try {
    $INSTANCE_RESPONSE = Invoke-RestMethod -Uri "$CONTROL_PLANE_URL/api/v1/instances" -Method POST -Body $INSTANCE_BODY -ContentType "application/json"
    $INSTANCE_ID = $INSTANCE_RESPONSE.id
    Write-Host "Instance registered successfully!" -ForegroundColor Green
    Write-Host "Instance ID: $INSTANCE_ID" -ForegroundColor Cyan
    Write-Host "Response: $($INSTANCE_RESPONSE | ConvertTo-Json -Compress)" -ForegroundColor Gray
} catch {
    Write-Host "ERROR: Failed to register instance" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
Write-Host ""

# Test 3: Connect Instance
Write-Host "[TEST 3] Connecting to instance..." -ForegroundColor Yellow
try {
    $CONNECT_RESPONSE = Invoke-RestMethod -Uri "$CONTROL_PLANE_URL/api/v1/instances/$INSTANCE_ID/connect" -Method POST
    Write-Host "Response: $($CONNECT_RESPONSE | ConvertTo-Json -Compress)" -ForegroundColor Green
} catch {
    Write-Host "WARNING: Connection may have issues" -ForegroundColor Yellow
    Write-Host $_.Exception.Message -ForegroundColor Yellow
}
Write-Host ""

# Wait for connection
Write-Host "Waiting for connection to establish..." -ForegroundColor Gray
Start-Sleep -Seconds 3

# Test 4: Check Instance Health
Write-Host "[TEST 4] Checking instance health..." -ForegroundColor Yellow
try {
    $HEALTH_RESPONSE = Invoke-RestMethod -Uri "$CONTROL_PLANE_URL/api/v1/instances/$INSTANCE_ID/health" -Method GET
    Write-Host "Response: $($HEALTH_RESPONSE | ConvertTo-Json -Compress)" -ForegroundColor Green
} catch {
    Write-Host "WARNING: Could not get health status" -ForegroundColor Yellow
}
Write-Host ""

# Test 5: Create Session
Write-Host "[TEST 5] Creating session..." -ForegroundColor Yellow
$SESSION_BODY = @{
    instance_id = $INSTANCE_ID
    target = "test-session-001"
    context = @{
        test = $true
        timestamp = (Get-Date -Format "o")
    }
} | ConvertTo-Json -Depth 10

try {
    $SESSION_RESPONSE = Invoke-RestMethod -Uri "$CONTROL_PLANE_URL/api/v1/sessions" -Method POST -Body $SESSION_BODY -ContentType "application/json"
    $SESSION_ID = $SESSION_RESPONSE.id
    Write-Host "Session created successfully!" -ForegroundColor Green
    Write-Host "Session ID: $SESSION_ID" -ForegroundColor Cyan
    Write-Host "Response: $($SESSION_RESPONSE | ConvertTo-Json -Compress)" -ForegroundColor Gray
} catch {
    Write-Host "ERROR: Failed to create session" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
Write-Host ""

# Test 6: Send Message
Write-Host "[TEST 6] Sending message..." -ForegroundColor Yellow
$MESSAGE_BODY = @{
    content = "你好，OpenClaw！这是一个测试消息。"
    stream = $false
    timeout = 60
} | ConvertTo-Json -Depth 10

try {
    $MESSAGE_RESPONSE = Invoke-RestMethod -Uri "$CONTROL_PLANE_URL/api/v1/sessions/$SESSION_ID/messages" -Method POST -Body $MESSAGE_BODY -ContentType "application/json"
    Write-Host "Message sent successfully!" -ForegroundColor Green
    Write-Host "Response: $($MESSAGE_RESPONSE | ConvertTo-Json -Compress)" -ForegroundColor Gray
} catch {
    Write-Host "WARNING: Message sending may have failed" -ForegroundColor Yellow
    Write-Host $_.Exception.Message -ForegroundColor Yellow
}
Write-Host ""

# Test 7: Get Message History
Write-Host "[TEST 7] Getting message history..." -ForegroundColor Yellow
try {
    $HISTORY_RESPONSE = Invoke-RestMethod -Uri "$CONTROL_PLANE_URL/api/v1/sessions/$SESSION_ID/messages" -Method GET
    Write-Host "Response: $($HISTORY_RESPONSE | ConvertTo-Json -Compress)" -ForegroundColor Green
} catch {
    Write-Host "WARNING: Could not get message history" -ForegroundColor Yellow
}
Write-Host ""

# Test 8: List All Instances
Write-Host "[TEST 8] Listing all instances..." -ForegroundColor Yellow
try {
    $INSTANCES_LIST = Invoke-RestMethod -Uri "$CONTROL_PLANE_URL/api/v1/instances" -Method GET
    Write-Host "Response: $($INSTANCES_LIST | ConvertTo-Json -Compress)" -ForegroundColor Green
} catch {
    Write-Host "WARNING: Could not list instances" -ForegroundColor Yellow
}
Write-Host ""

# Test 9: System Status
Write-Host "[TEST 9] Getting system status..." -ForegroundColor Yellow
try {
    $SYSTEM_STATUS = Invoke-RestMethod -Uri "$CONTROL_PLANE_URL/api/v1/system/status" -Method GET
    Write-Host "Response: $($SYSTEM_STATUS | ConvertTo-Json -Compress)" -ForegroundColor Green
} catch {
    Write-Host "WARNING: Could not get system status" -ForegroundColor Yellow
}
Write-Host ""

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Test Summary" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Instance ID: $INSTANCE_ID" -ForegroundColor White
Write-Host "Session ID: $SESSION_ID" -ForegroundColor White
Write-Host ""
Write-Host "All tests completed!" -ForegroundColor Green
Write-Host ""
Write-Host "Cleanup commands:" -ForegroundColor Yellow
Write-Host "  # Close session:" -ForegroundColor Gray
Write-Host "  Invoke-RestMethod -Uri '$CONTROL_PLANE_URL/api/v1/sessions/$SESSION_ID' -Method DELETE" -ForegroundColor Cyan
Write-Host ""
Write-Host "  # Disconnect instance:" -ForegroundColor Gray
Write-Host "  Invoke-RestMethod -Uri '$CONTROL_PLANE_URL/api/v1/instances/$INSTANCE_ID/disconnect' -Method POST" -ForegroundColor Cyan
Write-Host ""
Write-Host "  # Delete instance:" -ForegroundColor Gray
Write-Host "  Invoke-RestMethod -Uri '$CONTROL_PLANE_URL/api/v1/instances/$INSTANCE_ID' -Method DELETE" -ForegroundColor Cyan
