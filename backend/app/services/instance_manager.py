"""
Instance Management Service

Manages OpenClaw instances and their connections.
"""

import uuid
from typing import Optional
import os

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Instance, InstanceStatus
from app.schemas import InstanceCreate, InstanceUpdate, InstanceResponse, InstanceHealth
from app.connectors.ao_plugin import AoPluginConnector, AoConnectionConfig, get_connector_pool
from app.services.session_manager import MessageService, SessionService
from app.utils.time_utils import beijing_now_naive, beijing_now, format_beijing_time
from app.database import AsyncSessionLocal
import asyncio

# 文件日志
LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "control-plane-ws.log")

def _log_to_file(message: str):
    """写入日志到文件"""
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            ts = format_beijing_time(beijing_now())
            f.write(f"[{ts}] {message}\n")
    except Exception:
        pass


class InstanceService:
    """Service for managing OpenClaw instances."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.connector_pool = get_connector_pool()

    async def list_instances(self) -> list[Instance]:
        """List all instances."""
        result = await self.db.execute(select(Instance).order_by(Instance.created_at.desc()))
        return result.scalars().all()

    async def create_instance(self, data: InstanceCreate) -> Instance:
        """Create a new instance."""
        instance = Instance(
            id=str(uuid.uuid4()),
            name=data.name,
            host=data.host,
            port=data.port,
            auth_type=data.credentials.auth_type,
            credentials=self._filter_credentials(data.credentials),
            channel_id=data.channel_id,
            status=InstanceStatus.DISCONNECTED,
        )
        self.db.add(instance)
        await self.db.commit()
        await self.db.refresh(instance)
        return instance

    def _filter_credentials(self, creds) -> dict:
        """Filter credentials to only store necessary fields."""
        result = {"auth_type": creds.auth_type}
        if creds.auth_type == "token" and creds.token:
            result["token"] = creds.token
        elif creds.auth_type == "password" and creds.password:
            result["password"] = creds.password
        elif creds.auth_type == "mtls":
            result["cert_path"] = creds.cert_path
            result["key_path"] = creds.key_path
            result["ca_path"] = creds.ca_path
        return result

    async def get_instance(self, instance_id: str) -> Optional[Instance]:
        """Get instance by ID."""
        result = await self.db.execute(select(Instance).where(Instance.id == instance_id))
        return result.scalar_one_or_none()

    async def update_instance(self, instance_id: str, data: InstanceUpdate) -> Optional[Instance]:
        """Update an instance."""
        instance = await self.get_instance(instance_id)
        if not instance:
            return None

        update_data = data.model_dump(exclude_unset=True)

        if "credentials" in update_data and update_data["credentials"]:
            instance.credentials = self._filter_credentials(update_data["credentials"])
            del update_data["credentials"]

        for key, value in update_data.items():
            if value is not None:
                setattr(instance, key, value)

        instance.updated_at = beijing_now_naive()
        await self.db.commit()
        await self.db.refresh(instance)
        return instance

    async def delete_instance(self, instance_id: str) -> bool:
        """Delete an instance."""
        instance = await self.get_instance(instance_id)
        if not instance:
            return False

        # Disconnect first
        await self.disconnect_instance(instance_id)

        await self.db.delete(instance)
        await self.db.commit()
        return True

    async def connect_instance(self, instance_id: str) -> bool:
        """Connect to an instance."""
        instance = await self.get_instance(instance_id)
        if not instance:
            return False

        # Check if already connected
        existing_connector = self.connector_pool.get_connector(instance_id)
        if existing_connector and existing_connector.is_connected:
            _log_to_file(f"[InstanceManager] connect_instance: already connected, skipping")
            return True

        # Update status to connecting
        instance.status = InstanceStatus.CONNECTING
        await self.db.commit()

        try:
            connector = await self.connector_pool.add_connector(
                instance.id,
                AoConnectionConfig(
                    host=instance.host,
                    port=instance.port,
                    auth_type=instance.auth_type,
                    token=instance.credentials.get("token"),
                    password=instance.credentials.get("password"),
                    channel_id=instance.channel_id,
                )
            )

            _log_to_file(f"[InstanceManager] connect_instance: calling connector.connect()")
            connected = await connector.connect()
            _log_to_file(f"[InstanceManager] connect_instance: connected={connected}")

            if connected:
                instance.status = InstanceStatus.CONNECTED
                instance.last_connected_at = beijing_now_naive()
                instance.status_message = None

                # Set up handlers - create a new db session for each message
                async def handle_message_async(msg_data: dict):
                    _log_to_file(f"[InstanceManager] handle_message_async called: type={msg_data.get('type')}")
                    # Create a new database session for this message to avoid stale session issues
                    async with AsyncSessionLocal() as db:
                        await self._handle_message_with_session(instance_id, msg_data, db)

                _log_to_file(f"[InstanceManager] Registering message handler on connector")
                connector.on_message(handle_message_async)
                connector.on_status_change(
                    lambda status: self._handle_status_change(instance_id, status)
                )
                _log_to_file(f"[InstanceManager] Handler registered, handlers count will be checked in message_loop")
            else:
                instance.status = InstanceStatus.ERROR
                instance.status_message = "Connection failed"
                instance.last_error_at = beijing_now_naive()

            await self.db.commit()
            return connected

        except Exception as e:
            instance.status = InstanceStatus.ERROR
            instance.status_message = str(e)
            instance.last_error_at = beijing_now_naive()
            await self.db.commit()
            return False

    async def disconnect_instance(self, instance_id: str) -> bool:
        """Disconnect from an instance."""
        await self.connector_pool.remove_connector(instance_id)

        instance = await self.get_instance(instance_id)
        if instance:
            instance.status = InstanceStatus.DISCONNECTED
            await self.db.commit()
            return True
        return False

    async def get_instance_health(self, instance_id: str) -> InstanceHealth:
        """Get instance health status."""
        connector = self.connector_pool.get_connector(instance_id)
        if connector:
            health = connector.get_health()
            return InstanceHealth(
                latency_ms=None,  # TODO: Measure actual latency
                last_ping_at=health.get("last_ping_at"),
                reconnect_count=health.get("reconnect_count", 0),
                error_count=1 if health.get("last_error") else 0,
            )
        return InstanceHealth()

    async def _handle_message(self, instance_id: str, message: dict):
        """Handle incoming message from AO Plugin - uses self.db session (legacy method)."""
        await self._handle_message_with_session(instance_id, message, self.db)

    async def _handle_message_with_session(self, instance_id: str, message: dict, db: AsyncSession):
        """Handle incoming message from AO Plugin with a specific database session.

        This is called when AO Plugin sends a reply back (e.g., from OpenClaw).
        The message format follows ReplyMessage from AO Plugin types:
        {
            "type": "reply",
            "inReplyTo": "original-message-id",
            "sessionId": "session-id",
            "content": "reply content",
            "from": {"id": "...", "name": "...", "type": "agent"},
            "metadata": {...}
        }
        """
        import logging
        logger = logging.getLogger(__name__)

        _log_to_file(f"[InstanceManager] _handle_message called: instance={instance_id}, type={message.get('type')}")

        try:
            ts = format_beijing_time(beijing_now())
            logger.info(f"[{ts}] [InstanceManager] Received message from {instance_id}: {message.get('type')}")
            logger.info(f"[{ts}] [InstanceManager] Full message: type={message.get('type')}, sessionId={message.get('sessionId')}, content={str(message.get('content', ''))[:50]}")
            _log_to_file(f"[InstanceManager] Full message: type={message.get('type')}, sessionId={message.get('sessionId')}")
            logger.debug(f"[{ts}] [InstanceManager] Full message: {message}")

            # Only handle reply messages
            if message.get("type") != "reply":
                logger.debug(f"[{ts}] [InstanceManager] Ignoring non-reply message type: {message.get('type')}")
                return

            session_id = message.get("sessionId")
            content = message.get("content")

            logger.info(f"[{ts}] [InstanceManager] Processing reply for session {session_id}, content length: {len(content) if content else 0}")

            if not session_id:
                logger.warning(f"[{ts}] [InstanceManager] Reply message missing sessionId: {message}")
                return

            if not content:
                logger.warning(f"[{ts}] [InstanceManager] Reply message missing content: {message}")
                return

            # Check if this is a meeting message (format: meeting:{id})
            if session_id.startswith("meeting:"):
                await self._handle_meeting_message(instance_id, session_id, content, message, db)
                return

            # Create message service to store the reply
            message_service = MessageService(db)

            # Store as assistant message
            new_message = await message_service.create_message(
                session_id=session_id,
                role="assistant",
                content=content,
                metadata={
                    "in_reply_to": message.get("inReplyTo"),
                    "from": message.get("from"),
                    "instance_id": instance_id,
                }
            )

            # Update session last message timestamp
            session_service = SessionService(db)
            await session_service.update_last_message(session_id)

            logger.info(f"[{ts}] [InstanceManager] Stored assistant reply for session {session_id}")

            # Push message to frontend via Socket.IO
            try:
                from app.services.socketio_service import push_message_to_session
                message_data = {
                    "id": new_message.id,
                    "session_id": session_id,
                    "role": "assistant",
                    "content": content,
                    "created_at": new_message.created_at.isoformat() if new_message.created_at else None,
                    "metadata": new_message.extra_data or {},
                }
                pushed = await push_message_to_session(session_id, message_data)
                if pushed:
                    logger.info(f"[{ts}] [InstanceManager] Pushed message to frontend via Socket.IO")
                else:
                    logger.debug(f"[{ts}] [InstanceManager] No frontend clients connected for Socket.IO push")
            except Exception as push_error:
                logger.warning(f"[{ts}] [InstanceManager] Failed to push to frontend: {push_error}")
                import traceback
                logger.warning(f"[{ts}] [InstanceManager] Push traceback: {traceback.format_exc()}")

        except Exception as e:
            ts = format_beijing_time(beijing_now())
            logger.error(f"[{ts}] [InstanceManager] Failed to handle incoming message: {e}")
            import traceback
            logger.error(f"[{ts}] [InstanceManager] Traceback: {traceback.format_exc()}")

    async def _handle_meeting_message(
        self,
        instance_id: str,
        session_id: str,
        content: str,
        message: dict,
        db: AsyncSession
    ):
        """Handle incoming meeting message from an instance."""
        import logging
        logger = logging.getLogger(__name__)

        ts = format_beijing_time(beijing_now())
        _log_to_file(f"[InstanceManager] Handling meeting message: session_id={session_id}, from_instance={instance_id}")

        try:
            # Extract meeting_id from session_id (format: meeting:{meeting_id})
            meeting_id = session_id.replace("meeting:", "")

            # Get meeting to check current speaker
            from app.models import Meeting, MeetingParticipant
            result = await db.execute(
                select(Meeting).where(Meeting.id == meeting_id)
            )
            meeting = result.scalar_one_or_none()

            if not meeting or meeting.status.value != "in_progress":
                logger.warning(f"[{ts}] [InstanceManager] Meeting {meeting_id} not found or not in progress")
                return

            # Get the expected current speaker's instance_id
            if meeting.current_speaker_id:
                result = await db.execute(
                    select(MeetingParticipant).where(MeetingParticipant.id == meeting.current_speaker_id)
                )
                expected_speaker = result.scalar_one_or_none()

                if expected_speaker and expected_speaker.instance_id != instance_id:
                    # This response is from a different instance than expected - ignore it
                    expected_name = expected_speaker.instance_id[:8]
                    logger.warning(
                        f"[{ts}] [InstanceManager] Ignoring message from {instance_id[:8]}: "
                        f"expected speaker is {expected_name}"
                    )
                    return
            else:
                logger.warning(f"[{ts}] [InstanceManager] No current speaker set for meeting {meeting_id}")
                return

            # Check if this is a summary response (waiting_for_summary=True)
            # Don't store as regular message, let the flow service handle it
            if meeting.waiting_for_summary:
                from app.services.meeting_flow_service import MeetingFlowService
                from app.models import MeetingRound

                flow_service = MeetingFlowService(db)

                # Need to determine if this is a round summary or closing summary
                # Case 1: If current round already has a summary stored, this must be the closing summary
                # Case 2: If this is the last round (current_round >= max_rounds), this is the closing summary
                round_result = await db.execute(
                    select(MeetingRound).where(
                        MeetingRound.meeting_id == meeting_id,
                        MeetingRound.round_number == meeting.current_round
                    )
                )
                current_round_record = round_result.scalar_one_or_none()

                # Check if this should be treated as closing summary
                is_last_round = meeting.current_round >= meeting.max_rounds
                has_round_summary = current_round_record and current_round_record.summary

                if has_round_summary or is_last_round:
                    logger.info(f"[{ts}] [InstanceManager] Processing meeting closing summary (last_round={is_last_round}, has_summary={has_round_summary})")
                    # Save the closing summary and complete the meeting
                    meeting.summary = content
                    meeting.status = "completed"
                    meeting.waiting_for_summary = False
                    from app.utils.time_utils import beijing_now_naive
                    meeting.completed_at = beijing_now_naive()
                    await db.commit()

                    # Notify frontend
                    await push_meeting_update(meeting_id, "meeting_completed", {
                        "summary": content,
                    })
                else:
                    # This is a round summary response, complete the round
                    logger.info(f"[{ts}] [InstanceManager] Processing round summary, completing round {meeting.current_round}")
                    await flow_service.complete_round_and_proceed(
                        meeting_id,
                        meeting.current_round,
                        content
                    )
                return

            # Normal message - store it
            from app.services.meeting_service import MeetingMessageService
            message_service = MeetingMessageService(db)

            meeting_message = await message_service.handle_meeting_reply(
                meeting_id=meeting_id,
                instance_id=instance_id,
                content=content
            )

            if meeting_message:
                logger.info(f"[{ts}] [InstanceManager] Stored meeting message for meeting {meeting_id}")

                # Push message to frontend via Socket.IO
                try:
                    from app.services.socketio_service import push_meeting_message
                    await push_meeting_message(meeting_id, {
                        "id": meeting_message.id,
                        "participant_id": meeting_message.participant_id,
                        "instance_id": instance_id,
                        "content": content,
                        "round_number": meeting_message.round_number,
                        "speaking_order": meeting_message.speaking_order,
                        "message_type": meeting_message.message_type,
                    })
                except Exception as push_error:
                    logger.warning(f"[{ts}] [InstanceManager] Failed to push meeting message: {push_error}")

                # Auto-proceed to next speaker if auto_proceed is enabled
                from app.services.meeting_flow_service import MeetingFlowService

                if meeting.auto_proceed:
                    flow_service = MeetingFlowService(db)

                    # Normal speech, proceed to next speaker
                    logger.info(f"[{ts}] [InstanceManager] Auto-proceeding to next speaker")
                    await flow_service.proceed_to_next_speaker(
                        meeting_id,
                        meeting_message.participant_id
                    )
            else:
                logger.warning(f"[{ts}] [InstanceManager] Failed to store meeting message - meeting may not be in progress")

        except Exception as e:
            logger.error(f"[{ts}] [InstanceManager] Error handling meeting message: {e}")
            import traceback
            logger.error(f"[{ts}] [InstanceManager] Traceback: {traceback.format_exc()}")

    def _handle_status_change(self, instance_id: str, status: str):
        """Handle connection status change."""
        import logging
        import asyncio
        from app.services.socketio_service import push_status_update
        logger = logging.getLogger(__name__)
        ts = format_beijing_time(beijing_now())
        logger.info(f"[{ts}] Instance {instance_id} status changed to: {status}")

        # 推送状态更新到前端
        try:
            # 获取或创建事件循环
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果已经在异步上下文中，创建任务
                asyncio.create_task(push_status_update(instance_id, status))
            else:
                # 否则运行协程
                loop.run_until_complete(push_status_update(instance_id, status))
        except Exception as e:
            logger.error(f"[{ts}] Failed to push status update: {e}")

    def to_response(self, instance: Instance) -> InstanceResponse:
        """Convert instance model to response schema."""
        # 获取 AO 端连接数信息
        ao_connections = None
        ao_max_connections = None
        connector = self.connector_pool.get_connector(instance.id)
        if connector:
            ao_connections = connector.ao_connections
            ao_max_connections = connector.ao_max_connections

        return InstanceResponse(
            id=instance.id,
            name=instance.name,
            host=instance.host,
            port=instance.port,
            channel_id=instance.channel_id,
            status=instance.status,
            status_message=instance.status_message,
            health=InstanceHealth(
                ao_connections=ao_connections,
                ao_max_connections=ao_max_connections,
            ),
            last_connected_at=instance.last_connected_at,
            last_error_at=instance.last_error_at,
            created_at=instance.created_at,
            updated_at=instance.updated_at,
        )
