"""
AO Plugin Connector

WebSocket client for connecting to AO Plugin instances.
"""

import asyncio
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Callable, Optional, Dict, Set
from urllib.parse import urlparse
import os

import websockets
from websockets.client import WebSocketClientProtocol
from websockets.exceptions import ConnectionClosed, InvalidStatusCode

# 文件日志
LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "control-plane-ws.log")

def _log_to_file(message: str):
    """写入日志到文件"""
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            ts = format_beijing(beijing_now())
            f.write(f"[{ts}] {message}\n")
    except Exception:
        pass


def beijing_now() -> datetime:
    """Get current time in Beijing timezone (UTC+8)."""
    beijing_tz = timezone(timedelta(hours=8))
    return datetime.now(beijing_tz)


def format_beijing(dt: datetime) -> str:
    """Format datetime as Beijing time string."""
    beijing_tz = timezone(timedelta(hours=8))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(beijing_tz).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+08:00"


@dataclass
class AoConnectionConfig:
    """AO Plugin connection configuration."""
    host: str
    port: int
    auth_type: str = "token"
    token: Optional[str] = None
    password: Optional[str] = None
    channel_id: str = "ao"
    timeout: int = 30
    retry_attempts: int = 3


@dataclass
class AoMessage:
    """AO Plugin message."""
    type: str
    event: Optional[str]
    payload: dict
    timestamp: datetime


class AoPluginConnector:
    """
    WebSocket connector for AO Plugin.

    Manages connection lifecycle, message handling, and automatic reconnection.
    """

    def __init__(self, config: AoConnectionConfig):
        self.config = config
        self.ws: Optional[WebSocketClientProtocol] = None
        self._is_connected = False
        self._is_authenticated = False
        self._message_handlers: Set[Callable] = set()
        self._status_handlers: Set[Callable] = set()
        self._reconnect_count = 0
        self._last_ping_at: Optional[datetime] = None
        self._last_error: Optional[str] = None
        self._connection_task: Optional[asyncio.Task] = None
        self._running = False

    @property
    def is_connected(self) -> bool:
        """Check if connected and authenticated."""
        return self._is_connected and self._is_authenticated and self.ws is not None

    @property
    def ws_url(self) -> str:
        """Generate WebSocket URL."""
        scheme = "wss" if self.config.port == 443 else "ws"
        return f"{scheme}://{self.config.host}:{self.config.port}/ws/openclaw"

    async def connect(self) -> bool:
        """
        Establish WebSocket connection.

        Returns:
            True if connected and authenticated successfully, False otherwise.
        """
        if self.is_connected:
            return True

        try:
            self.ws = await websockets.connect(
                self.ws_url,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=5,
            )
            self._is_connected = True
            self._is_authenticated = False
            self._reconnect_count = 0
            self._last_error = None
            self._last_ping_at = beijing_now()

            # Start message handler
            self._running = True
            self._connection_task = asyncio.create_task(self._message_loop())

            # Wait for welcome message and send auth
            # AO Plugin V2 protocol: receive welcome -> send auth
            await asyncio.sleep(0.5)  # Brief wait for welcome

            # Send auth message
            auth_sent = await self._send_auth()
            if not auth_sent:
                self._last_error = "Failed to send auth"
                await self.disconnect()
                return False

            # Wait for auth_response with timeout and check result
            auth_timeout = 5.0  # 5 seconds timeout
            auth_check_interval = 0.1
            elapsed = 0.0

            while elapsed < auth_timeout:
                if self._is_authenticated:
                    # Auth successful
                    # Start heartbeat task after authentication
                    self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                    await self._notify_status("connected")
                    return True
                if self._last_error and "Auth failed" in self._last_error:
                    # Auth explicitly failed
                    await self.disconnect()
                    return False
                await asyncio.sleep(auth_check_interval)
                elapsed += auth_check_interval

            # Timeout - auth_response not received
            self._last_error = "Auth response timeout"
            await self.disconnect()
            return False

        except InvalidStatusCode as e:
            self._last_error = f"HTTP {e.status_code}: {e.reason}"
            print(f"DEBUG InvalidStatusCode: {self._last_error}")
            return False
        except Exception as e:
            self._last_error = str(e)
            import traceback
            print(f"DEBUG Exception: {self._last_error}")
            traceback.print_exc()
            return False

    async def _send_auth(self) -> bool:
        """Send authentication message to AO Plugin V2."""
        if not self.ws:
            return False

        auth_message = {
            "type": "auth",
            "id": f"cp-{uuid.uuid4().hex[:8]}",
            "timestamp": int(beijing_now().timestamp() * 1000),
            "payload": {
                "apiKey": self.config.token or "",
                "controlPlaneId": f"control-plane-{self.config.host}",
                "version": "2.0.0",
            },
        }

        try:
            await self.ws.send(json.dumps(auth_message))
            print(f"DEBUG: Auth message sent: {auth_message}")
            return True
        except Exception as e:
            print(f"DEBUG: Failed to send auth: {e}")
            return False

    async def disconnect(self) -> None:
        """Close WebSocket connection gracefully."""
        _log_to_file(f"[WS] disconnect() called, running={self._running}, ws={self.ws is not None}")
        self._running = False

        if self._connection_task:
            _log_to_file(f"[WS] Cancelling connection task")
            self._connection_task.cancel()
            try:
                await self._connection_task
            except asyncio.CancelledError:
                pass
            self._connection_task = None

        if self.ws:
            # 发送断开通知消息，让 AO 端立即释放连接
            if self._is_authenticated:
                try:
                    disconnect_msg = {
                        "type": "disconnect",
                        "id": f"cp-{uuid.uuid4().hex[:8]}",
                        "timestamp": int(beijing_now().timestamp() * 1000),
                        "payload": {
                            "reason": "client_shutdown",
                            "controlPlaneId": f"control-plane-{self.config.host}",
                        },
                    }
                    await self.ws.send(json.dumps(disconnect_msg))
                    _log_to_file(f"[WS] Disconnect notification sent")
                    # 等待消息发送完成
                    await asyncio.sleep(0.1)
                except Exception as e:
                    _log_to_file(f"[WS] Failed to send disconnect notification: {e}")

            _log_to_file(f"[WS] Closing WebSocket connection")
            try:
                # 使用 Close frame with normal closure code
                await self.ws.close(code=1000, reason="Client shutdown")
                _log_to_file(f"[WS] WebSocket closed successfully")
            except Exception as e:
                _log_to_file(f"[WS] Error closing WebSocket: {e}")
            self.ws = None

        self._is_connected = False
        self._is_authenticated = False
        _log_to_file(f"[WS] disconnect() completed, notifying status handlers")
        await self._notify_status("disconnected")

    async def reconnect(self) -> bool:
        """Reconnect to the server."""
        await self.disconnect()
        await asyncio.sleep(1)  # Brief delay before reconnect
        self._reconnect_count += 1
        return await self.connect()

    async def send(self, method: str, params: dict) -> Optional[str]:
        """
        Send a request to the AO Plugin.

        Args:
            method: Method name
            params: Method parameters

        Returns:
            Request ID if sent successfully, None otherwise.
        """
        if not self.is_connected or not self.ws:
            return None

        request_id = f"cp-{uuid.uuid4().hex[:8]}"
        frame = {
            "type": "req",
            "id": request_id,
            "method": method,
            "params": params,
        }

        try:
            await self.ws.send(json.dumps(frame))
            return request_id
        except Exception:
            return None

    async def send_message(self, channel: str, session_id: str, content: str) -> Optional[str]:
        """
        Send a chat message using AO Plugin V2 protocol format.

        Args:
            channel: Channel ID
            session_id: Session ID
            content: Message content

        Returns:
            Request ID if sent successfully, None otherwise.
        """
        _log_to_file(f"[Connector] send_message called: channel={channel}, session_id={session_id}, ws_url={self.ws_url}")
        if not self.is_connected or not self.ws:
            _log_to_file(f"[Connector] send_message FAILED: not connected, is_connected={self.is_connected}, ws={self.ws is not None}")
            print(f"DEBUG send_message: not connected")
            return None

        request_id = f"cp-{uuid.uuid4().hex[:8]}"

        # Use AO Plugin V2 protocol format (ChatMessage)
        message = {
            "type": "chat",
            "id": request_id,
            "timestamp": int(beijing_now().timestamp() * 1000),
            "sessionId": session_id,
            "content": content,
            "from": {
                "id": "control_plane",
                "name": "Control Plane",
                "type": "user",
            },
            "metadata": {
                "channel": channel,
            },
        }

        try:
            await self.ws.send(json.dumps(message))
            _log_to_file(f"[Connector] send_message SUCCESS: request_id={request_id}, session_id={session_id}")
            print(f"DEBUG send_message: sent successfully, request_id={request_id}")
            return request_id
        except Exception as e:
            _log_to_file(f"[Connector] send_message ERROR: {e}")
            print(f"DEBUG send_message error: {e}")
            return None

    def on_message(self, handler: Callable[[AoMessage], None]) -> Callable:
        """
        Register a message handler.

        Returns:
            Unregister function.
        """
        self._message_handlers.add(handler)
        return lambda: self._message_handlers.discard(handler)

    def on_status_change(self, handler: Callable[[str], None]) -> Callable:
        """
        Register a status change handler.

        Returns:
            Unregister function.
        """
        self._status_handlers.add(handler)
        return lambda: self._status_handlers.discard(handler)

    async def _message_loop(self) -> None:
        """Main message receiving loop."""
        _log_to_file(f"[WS] _message_loop started, running={self._running}")
        while self._running and self.ws:
            try:
                raw_data = await self.ws.recv()

                # Log EVERY raw message received - no filtering
                ts = format_beijing(beijing_now())
                raw_str = raw_data if isinstance(raw_data, str) else raw_data.decode('utf-8', errors='replace')
                _log_to_file(f"[WS] RAW RECV: {len(raw_str)} bytes, first 500 chars: {raw_str[:500]}")
                print(f"[{ts}] RAW RECV: type check = '{raw_str[:50]}'")

                # Debug: Check raw_data type before JSON parsing
                _log_to_file(f"[WS] About to parse JSON, raw_data type={type(raw_data).__name__}")
                try:
                    data = json.loads(raw_data)
                except Exception as parse_err:
                    _log_to_file(f"[WS] JSON parse error: {parse_err}, trying raw_str")
                    print(f"[{ts}] DEBUG: JSON parse error with raw_data, trying raw_str: {parse_err}")
                    data = json.loads(raw_str)

                # Parse message for internal use
                msg_type = data.get("type", "unknown")

                # Safe print to handle Unicode errors on Windows (GBK encoding)
                try:
                    print(f"DEBUG: Received message type={msg_type}, data={data}")
                except UnicodeEncodeError:
                    # Fallback: encode with replacement for non-encodable characters
                    safe_data = json.dumps(data, ensure_ascii=False)[:500]
                    print(f"DEBUG: Received message type={msg_type}, data={safe_data.encode('gbk', errors='replace').decode('gbk')}")

                try:
                    _log_to_file(f"[WS] Received message type={msg_type}, data={json.dumps(data)[:500]}")
                except Exception as log_err:
                    _log_to_file(f"[WS] Received message type={msg_type}, data=<failed to serialize: {log_err}>")

                # Handle welcome message (AO Plugin V2)
                if msg_type == "welcome":
                    print(f"DEBUG: Received welcome from AO Plugin")
                    continue

                # Handle auth_response (AO Plugin V2)
                if msg_type == "auth_response":
                    payload = data.get("payload", {})
                    if payload.get("success"):
                        self._is_authenticated = True
                        print(f"DEBUG: Auth successful, connectionId={payload.get('connectionId')}")
                        await self._notify_status("authenticated")
                    else:
                        self._last_error = payload.get("error", "Auth failed")
                        print(f"DEBUG: Auth failed: {self._last_error}")
                    continue

                # Handle ping/pong (AO Plugin V2 uses ping messages)
                if msg_type == "ping":
                    # Send pong response
                    pong = {
                        "type": "pong",
                        "inReplyTo": data.get("id"),
                        "timestamp": int(beijing_now().timestamp() * 1000),
                    }
                    await self.ws.send(json.dumps(pong))
                    self._last_ping_at = beijing_now()
                    continue

                if msg_type == "pong":
                    self._last_ping_at = beijing_now()
                    continue

                # Handle reply messages from AO Plugin
                if msg_type == "reply":
                    ts = format_beijing(beijing_now())
                    # Safe print to handle Unicode on Windows
                    try:
                        print(f"[{ts}] DEBUG: Received reply: {data.get('content', '')[:100]}...")
                    except UnicodeEncodeError:
                        pass  # Skip print if encoding fails
                    print(f"[{ts}] DEBUG: Reply sessionId={data.get('sessionId')}, inReplyTo={data.get('inReplyTo')}")
                    _log_to_file(f"[WS] REPLY received: sessionId={data.get('sessionId')}, content={data.get('content', '')[:100]}")

                # Notify handlers with raw data
                ts = format_beijing(beijing_now())
                print(f"[{ts}] DEBUG: Calling {len(self._message_handlers)} message handler(s) for type={msg_type}")
                _log_to_file(f"[WS] Calling {len(self._message_handlers)} handlers for type={msg_type}")
                for handler in self._message_handlers:
                    try:
                        print(f"[{ts}] DEBUG: Calling handler {handler.__name__ if hasattr(handler, '__name__') else handler} for type={msg_type}")
                        _log_to_file(f"[WS] Calling handler: {handler.__name__ if hasattr(handler, '__name__') else str(handler)}")
                        result = handler(data)
                        print(f"[{ts}] DEBUG: Handler returned {type(result)}, iscoroutine={asyncio.iscoroutine(result)}")
                        _log_to_file(f"[WS] Handler returned, iscoroutine={asyncio.iscoroutine(result)}")
                        if asyncio.iscoroutine(result):
                            print(f"[{ts}] DEBUG: Creating task for handler result")
                            _log_to_file(f"[WS] Creating async task for handler")
                            asyncio.create_task(result)
                    except Exception as e:
                        print(f"[{ts}] DEBUG Handler error: {e}")
                        _log_to_file(f"[WS] Handler error: {e}")
                        import traceback
                        traceback.print_exc()

            except ConnectionClosed:
                self._is_connected = False
                await self._notify_status("disconnected")
                break
            except json.JSONDecodeError as e:
                _log_to_file(f"[WS] JSONDecodeError: {e}, raw_data preview: {raw_str[:200] if 'raw_str' in dir() else 'N/A'}")
                print(f"[{format_beijing(beijing_now())}] DEBUG JSONDecodeError: {e}")
                continue
            except Exception as e:
                _log_to_file(f"[WS] UNHANDLED EXCEPTION in message loop: {type(e).__name__}: {e}")
                print(f"[{format_beijing(beijing_now())}] DEBUG UNHANDLED EXCEPTION: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
                self._last_error = str(e)
                await self._notify_status("error")

    async def _notify_status(self, status: str) -> None:
        """Notify status handlers."""
        for handler in self._status_handlers:
            try:
                handler(status)
            except Exception:
                pass

    async def _heartbeat_loop(self) -> None:
        """
        Send application-layer ping messages to AO Plugin.

        AO Plugin V2 expects application-layer ping messages (not WebSocket protocol ping).
        Sends ping every 20 seconds to keep connection alive.
        """
        ping_id = 0
        while self._running and self.ws and self._is_authenticated:
            try:
                await asyncio.sleep(20)  # Send ping every 20 seconds

                if not self._is_authenticated or not self.ws:
                    break

                # Send application-layer ping
                ping_msg = {
                    "type": "ping",
                    "id": f"heartbeat-{ping_id}",
                }
                await self.ws.send(json.dumps(ping_msg))
                ping_id += 1

            except asyncio.CancelledError:
                break
            except Exception:
                break

    def get_health(self) -> dict:
        """Get connection health status."""
        return {
            "is_connected": self.is_connected,
            "reconnect_count": self._reconnect_count,
            "last_ping_at": self._last_ping_at.isoformat() if self._last_ping_at else None,
            "last_error": self._last_error,
            "ws_url": self.ws_url,
        }


class AoConnectorPool:
    """
    Pool of AO Plugin connectors for managing multiple instances.
    """

    def __init__(self):
        self._connectors: Dict[str, AoPluginConnector] = {}
        self._health_checks: Dict[str, asyncio.Task] = {}

    async def add_connector(self, instance_id: str, config: AoConnectionConfig) -> AoPluginConnector:
        """Add and connect a new connector."""
        _log_to_file(f"[Pool] add_connector called for instance_id={instance_id}")
        # Remove existing if any
        if instance_id in self._connectors:
            _log_to_file(f"[Pool] Existing connector found, calling remove_connector")
        await self.remove_connector(instance_id)

        connector = AoPluginConnector(config)
        self._connectors[instance_id] = connector
        _log_to_file(f"[Pool] Connector added for instance_id={instance_id}")

        # Start health check
        self._health_checks[instance_id] = asyncio.create_task(
            self._health_check_loop(instance_id)
        )

        return connector

    async def remove_connector(self, instance_id: str) -> None:
        """Remove a connector."""
        _log_to_file(f"[Pool] remove_connector called for instance_id={instance_id}")
        if instance_id in self._connectors:
            connector = self._connectors[instance_id]
            _log_to_file(f"[Pool] Calling connector.disconnect() for instance_id={instance_id}")
            await connector.disconnect()
            del self._connectors[instance_id]
            _log_to_file(f"[Pool] Connector removed for instance_id={instance_id}")

        if instance_id in self._health_checks:
            self._health_checks[instance_id].cancel()
            try:
                await self._health_checks[instance_id]
            except asyncio.CancelledError:
                pass
            del self._health_checks[instance_id]

    def get_connector(self, instance_id: str) -> Optional[AoPluginConnector]:
        """Get a connector by instance ID."""
        return self._connectors.get(instance_id)

    def get_all_connectors(self) -> Dict[str, AoPluginConnector]:
        """Get all connectors."""
        return self._connectors.copy()

    async def close_all(self) -> None:
        """Close all connections."""
        for instance_id in list(self._connectors.keys()):
            await self.remove_connector(instance_id)

    async def _health_check_loop(self, instance_id: str) -> None:
        """Health check loop for a connector."""
        while instance_id in self._connectors:
            await asyncio.sleep(30)  # Check every 30 seconds

            connector = self._connectors.get(instance_id)
            if not connector:
                break

            # Check if still connected
            if not connector.is_connected:
                # Try to reconnect
                await connector.reconnect()


# Global connector pool
_connector_pool: Optional[AoConnectorPool] = None


def get_connector_pool() -> AoConnectorPool:
    """Get global connector pool."""
    global _connector_pool
    if _connector_pool is None:
        _connector_pool = AoConnectorPool()
    return _connector_pool
