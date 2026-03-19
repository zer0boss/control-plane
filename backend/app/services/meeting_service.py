"""
Meeting Management Service

Manages agent collective meetings for discussion.
"""

import uuid
from typing import Optional, List
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from app.models import (
    Meeting, MeetingStatus, MeetingType,
    MeetingParticipant, ParticipantRole,
    MeetingMessage, MeetingRound, MeetingRoundStatus,
    Instance, InstanceStatus,
)
from app.schemas import (
    MeetingCreate, MeetingUpdate,
    ParticipantCreate, ParticipantUpdate,
    MeetingMessageCreate, MeetingRoundCreate,
)
from app.utils.time_utils import beijing_now_naive
from app.connectors.ao_plugin import get_connector_pool


class MeetingService:
    """Service for managing meetings."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.connector_pool = get_connector_pool()

    async def create_meeting(self, data: MeetingCreate) -> Meeting:
        """Create a new meeting."""
        meeting = Meeting(
            id=str(uuid.uuid4()),
            title=data.title,
            description=data.description,
            meeting_type=data.meeting_type,
            host_instance_id=data.host_instance_id,
            max_rounds=data.max_rounds,
            context=data.context,
            status=MeetingStatus.DRAFT,
            current_round=0,
        )
        self.db.add(meeting)
        await self.db.commit()
        await self.db.refresh(meeting)

        # Add host as participant with HOST role
        host_participant = MeetingParticipant(
            id=str(uuid.uuid4()),
            meeting_id=meeting.id,
            instance_id=data.host_instance_id,
            role=ParticipantRole.HOST,
            speaking_order=0,
        )
        self.db.add(host_participant)
        await self.db.commit()

        return meeting

    async def get_meeting(self, meeting_id: str) -> Optional[Meeting]:
        """Get meeting by ID."""
        result = await self.db.execute(
            select(Meeting).where(Meeting.id == meeting_id)
        )
        return result.scalar_one_or_none()

    async def list_meetings(
        self,
        status: Optional[MeetingStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Meeting]:
        """List all meetings."""
        query = select(Meeting).order_by(Meeting.created_at.desc())
        if status:
            query = query.where(Meeting.status == status)
        query = query.limit(limit).offset(offset)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def count_meetings(self, status: Optional[MeetingStatus] = None) -> int:
        """Count meetings."""
        query = select(func.count()).select_from(Meeting)
        if status:
            query = query.where(Meeting.status == status)
        result = await self.db.execute(query)
        return result.scalar()

    async def update_meeting(self, meeting_id: str, data: MeetingUpdate) -> Optional[Meeting]:
        """Update a meeting."""
        meeting = await self.get_meeting(meeting_id)
        if not meeting:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                setattr(meeting, key, value)

        meeting.updated_at = beijing_now_naive()
        await self.db.commit()
        await self.db.refresh(meeting)
        return meeting

    async def delete_meeting(self, meeting_id: str) -> bool:
        """Delete a meeting and all related data."""
        meeting = await self.get_meeting(meeting_id)
        if not meeting:
            return False

        # Delete related records
        await self.db.execute(
            MeetingMessage.__table__.delete().where(MeetingMessage.meeting_id == meeting_id)
        )
        await self.db.execute(
            MeetingRound.__table__.delete().where(MeetingRound.meeting_id == meeting_id)
        )
        await self.db.execute(
            MeetingParticipant.__table__.delete().where(MeetingParticipant.meeting_id == meeting_id)
        )

        await self.db.delete(meeting)
        await self.db.commit()
        return True

    async def start_meeting(self, meeting_id: str) -> Optional[Meeting]:
        """Start a meeting."""
        meeting = await self.get_meeting(meeting_id)
        if not meeting:
            return None

        if meeting.status != MeetingStatus.READY:
            # Can only start from READY status
            if meeting.status == MeetingStatus.DRAFT:
                # Auto-transition from DRAFT to READY then IN_PROGRESS
                pass
            elif meeting.status == MeetingStatus.IN_PROGRESS:
                return meeting  # Already started
            else:
                return None

        meeting.status = MeetingStatus.IN_PROGRESS
        meeting.started_at = beijing_now_naive()
        meeting.current_round = 1
        meeting.updated_at = beijing_now_naive()
        await self.db.commit()
        await self.db.refresh(meeting)

        # Create first round
        await self._create_round(meeting_id, 1)

        return meeting

    async def pause_meeting(self, meeting_id: str) -> Optional[Meeting]:
        """Pause a meeting."""
        meeting = await self.get_meeting(meeting_id)
        if not meeting or meeting.status != MeetingStatus.IN_PROGRESS:
            return None

        meeting.status = MeetingStatus.PAUSED
        meeting.updated_at = beijing_now_naive()
        await self.db.commit()
        await self.db.refresh(meeting)
        return meeting

    async def resume_meeting(self, meeting_id: str) -> Optional[Meeting]:
        """Resume a paused meeting."""
        meeting = await self.get_meeting(meeting_id)
        if not meeting or meeting.status != MeetingStatus.PAUSED:
            return None

        meeting.status = MeetingStatus.IN_PROGRESS
        meeting.updated_at = beijing_now_naive()
        await self.db.commit()
        await self.db.refresh(meeting)
        return meeting

    async def end_meeting(self, meeting_id: str) -> Optional[Meeting]:
        """End a meeting."""
        meeting = await self.get_meeting(meeting_id)
        if not meeting or meeting.status not in [MeetingStatus.IN_PROGRESS, MeetingStatus.PAUSED]:
            return None

        meeting.status = MeetingStatus.COMPLETED
        meeting.completed_at = beijing_now_naive()
        meeting.updated_at = beijing_now_naive()
        await self.db.commit()
        await self.db.refresh(meeting)
        return meeting

    async def cancel_meeting(self, meeting_id: str) -> Optional[Meeting]:
        """Cancel a meeting."""
        meeting = await self.get_meeting(meeting_id)
        if not meeting or meeting.status == MeetingStatus.COMPLETED:
            return None

        meeting.status = MeetingStatus.CANCELLED
        meeting.updated_at = beijing_now_naive()
        await self.db.commit()
        await self.db.refresh(meeting)
        return meeting

    async def set_ready(self, meeting_id: str) -> Optional[Meeting]:
        """Set meeting status to READY."""
        meeting = await self.get_meeting(meeting_id)
        if not meeting or meeting.status != MeetingStatus.DRAFT:
            return None

        meeting.status = MeetingStatus.READY
        meeting.updated_at = beijing_now_naive()
        await self.db.commit()
        await self.db.refresh(meeting)
        return meeting

    async def _create_round(self, meeting_id: str, round_number: int, topic: str = None) -> MeetingRound:
        """Create a new meeting round."""
        meeting_round = MeetingRound(
            id=str(uuid.uuid4()),
            meeting_id=meeting_id,
            round_number=round_number,
            topic=topic,
            status=MeetingRoundStatus.IN_PROGRESS,
            started_at=beijing_now_naive(),
        )
        self.db.add(meeting_round)
        await self.db.commit()
        await self.db.refresh(meeting_round)
        return meeting_round


class ParticipantService:
    """Service for managing meeting participants."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_participant(self, meeting_id: str, data: ParticipantCreate) -> MeetingParticipant:
        """Add a participant to a meeting."""
        # Get current max speaking order
        result = await self.db.execute(
            select(func.max(MeetingParticipant.speaking_order))
            .where(MeetingParticipant.meeting_id == meeting_id)
        )
        max_order = result.scalar() or 0

        participant = MeetingParticipant(
            id=str(uuid.uuid4()),
            meeting_id=meeting_id,
            instance_id=data.instance_id,
            role=data.role,
            speaking_order=data.speaking_order if data.speaking_order > 0 else max_order + 1,
            expertise=data.expertise,
        )
        self.db.add(participant)
        await self.db.commit()
        await self.db.refresh(participant)
        return participant

    async def get_participant(self, participant_id: str) -> Optional[MeetingParticipant]:
        """Get participant by ID."""
        result = await self.db.execute(
            select(MeetingParticipant).where(MeetingParticipant.id == participant_id)
        )
        return result.scalar_one_or_none()

    async def list_participants(self, meeting_id: str) -> List[MeetingParticipant]:
        """List all participants for a meeting."""
        result = await self.db.execute(
            select(MeetingParticipant)
            .where(MeetingParticipant.meeting_id == meeting_id)
            .order_by(MeetingParticipant.speaking_order)
        )
        return result.scalars().all()

    async def update_participant(
        self, participant_id: str, data: ParticipantUpdate
    ) -> Optional[MeetingParticipant]:
        """Update a participant."""
        participant = await self.get_participant(participant_id)
        if not participant:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                setattr(participant, key, value)

        await self.db.commit()
        await self.db.refresh(participant)
        return participant

    async def remove_participant(self, participant_id: str) -> bool:
        """Remove a participant from a meeting."""
        participant = await self.get_participant(participant_id)
        if not participant:
            return False

        await self.db.delete(participant)
        await self.db.commit()
        return True

    async def reorder_participants(
        self, meeting_id: str, participant_orders: List[dict]
    ) -> List[MeetingParticipant]:
        """Reorder participants by speaking order."""
        for item in participant_orders:
            participant = await self.get_participant(item["id"])
            if participant and participant.meeting_id == meeting_id:
                participant.speaking_order = item["speaking_order"]

        await self.db.commit()
        return await self.list_participants(meeting_id)

    async def get_host_participant(self, meeting_id: str) -> Optional[MeetingParticipant]:
        """Get the host participant for a meeting."""
        result = await self.db.execute(
            select(MeetingParticipant)
            .where(
                and_(
                    MeetingParticipant.meeting_id == meeting_id,
                    MeetingParticipant.role == ParticipantRole.HOST
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_active_participants(self, meeting_id: str) -> List[MeetingParticipant]:
        """List all active participants for a meeting (excluding observers by default for speaking order)."""
        result = await self.db.execute(
            select(MeetingParticipant)
            .where(
                and_(
                    MeetingParticipant.meeting_id == meeting_id,
                    MeetingParticipant.is_active == True
                )
            )
            .order_by(MeetingParticipant.speaking_order)
        )
        return result.scalars().all()


class MeetingRoundService:
    """Service for managing meeting rounds."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_round(self, round_id: str) -> Optional[MeetingRound]:
        """Get round by ID."""
        result = await self.db.execute(
            select(MeetingRound).where(MeetingRound.id == round_id)
        )
        return result.scalar_one_or_none()

    async def list_rounds(self, meeting_id: str) -> List[MeetingRound]:
        """List all rounds for a meeting."""
        result = await self.db.execute(
            select(MeetingRound)
            .where(MeetingRound.meeting_id == meeting_id)
            .order_by(MeetingRound.round_number)
        )
        return result.scalars().all()

    async def get_current_round(self, meeting_id: str) -> Optional[MeetingRound]:
        """Get the current active round for a meeting."""
        result = await self.db.execute(
            select(Meeting)
            .where(Meeting.id == meeting_id)
        )
        meeting = result.scalar_one_or_none()
        if not meeting:
            return None

        result = await self.db.execute(
            select(MeetingRound)
            .where(
                and_(
                    MeetingRound.meeting_id == meeting_id,
                    MeetingRound.round_number == meeting.current_round
                )
            )
        )
        return result.scalar_one_or_none()

    async def complete_round(self, round_id: str) -> Optional[MeetingRound]:
        """Complete a round."""
        meeting_round = await self.get_round(round_id)
        if not meeting_round:
            return None

        meeting_round.status = MeetingRoundStatus.COMPLETED
        meeting_round.completed_at = beijing_now_naive()
        await self.db.commit()
        await self.db.refresh(meeting_round)
        return meeting_round

    async def start_next_round(
        self, meeting_id: str, topic: str = None
    ) -> Optional[MeetingRound]:
        """Start the next round in a meeting."""
        result = await self.db.execute(
            select(Meeting).where(Meeting.id == meeting_id)
        )
        meeting = result.scalar_one_or_none()
        if not meeting:
            return None

        # Complete current round if exists
        current_round = await self.get_current_round(meeting_id)
        if current_round and current_round.status == MeetingRoundStatus.IN_PROGRESS:
            await self.complete_round(current_round.id)

        # Check if max rounds reached
        if meeting.current_round >= meeting.max_rounds:
            return None

        # Increment round
        meeting.current_round += 1
        meeting.updated_at = beijing_now_naive()
        await self.db.commit()
        await self.db.refresh(meeting)

        # Create new round
        new_round = MeetingRound(
            id=str(uuid.uuid4()),
            meeting_id=meeting_id,
            round_number=meeting.current_round,
            topic=topic,
            status=MeetingRoundStatus.IN_PROGRESS,
            started_at=beijing_now_naive(),
        )
        self.db.add(new_round)
        await self.db.commit()
        await self.db.refresh(new_round)
        return new_round

    async def complete_round_with_summary(
        self,
        meeting_id: str,
        round_number: int,
        summary: str,
        summarized_by: str
    ) -> Optional[MeetingRound]:
        """Complete a round with a summary."""
        result = await self.db.execute(
            select(MeetingRound).where(
                and_(
                    MeetingRound.meeting_id == meeting_id,
                    MeetingRound.round_number == round_number
                )
            )
        )
        meeting_round = result.scalar_one_or_none()
        if not meeting_round:
            return None

        meeting_round.status = MeetingRoundStatus.COMPLETED
        meeting_round.summary = summary
        meeting_round.summarized_by_participant_id = summarized_by
        meeting_round.summarized_at = beijing_now_naive()
        meeting_round.completed_at = beijing_now_naive()
        await self.db.commit()
        await self.db.refresh(meeting_round)
        return meeting_round


class MeetingMessageService:
    """Service for managing meeting messages."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.connector_pool = get_connector_pool()

    async def create_message(
        self,
        meeting_id: str,
        participant_id: str,
        instance_id: str,
        content: str,
        round_number: int,
        speaking_order: int = 0,
        message_type: str = "statement",
        extra_data: dict = None
    ) -> MeetingMessage:
        """Create a new meeting message."""
        message = MeetingMessage(
            id=str(uuid.uuid4()),
            meeting_id=meeting_id,
            participant_id=participant_id,
            instance_id=instance_id,
            content=content,
            round_number=round_number,
            speaking_order=speaking_order,
            message_type=message_type,
            extra_data=extra_data or {},
        )
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        return message

    async def get_messages(
        self,
        meeting_id: str,
        round_number: Optional[int] = None,
        limit: int = 100
    ) -> List[MeetingMessage]:
        """Get messages for a meeting."""
        query = select(MeetingMessage).where(
            MeetingMessage.meeting_id == meeting_id
        )
        if round_number:
            query = query.where(MeetingMessage.round_number == round_number)
        query = query.order_by(
            MeetingMessage.round_number,
            MeetingMessage.speaking_order,
            MeetingMessage.created_at
        ).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_message_count(self, meeting_id: str) -> int:
        """Get total message count for a meeting."""
        result = await self.db.execute(
            select(func.count())
            .where(MeetingMessage.meeting_id == meeting_id)
        )
        return result.scalar()

    async def get_next_speaking_order(self, meeting_id: str, round_number: int) -> int:
        """Get the next speaking order for a round."""
        result = await self.db.execute(
            select(func.max(MeetingMessage.speaking_order))
            .where(
                and_(
                    MeetingMessage.meeting_id == meeting_id,
                    MeetingMessage.round_number == round_number
                )
            )
        )
        max_order = result.scalar()
        return (max_order or 0) + 1

    async def build_history_prompt(self, meeting_id: str, current_round: int) -> str:
        """Build a prompt with meeting history for an agent."""
        messages = await self.get_messages(meeting_id, limit=200)

        # Get meeting info
        result = await self.db.execute(
            select(Meeting).where(Meeting.id == meeting_id)
        )
        meeting = result.scalar_one_or_none()
        if not meeting:
            return ""

        # Get participants
        result = await self.db.execute(
            select(MeetingParticipant)
            .where(MeetingParticipant.meeting_id == meeting_id)
        )
        participants = result.scalars().all()
        participant_map = {p.instance_id: p for p in participants}

        # Build history text
        history_lines = [
            f"# 会议主题: {meeting.title}",
            f"# 会议类型: {meeting.meeting_type.value}",
            f"# 当前轮次: {current_round}/{meeting.max_rounds}",
            "",
            "## 参会者:",
        ]

        for p in participants:
            role_name = {
                ParticipantRole.HOST: "主持人",
                ParticipantRole.EXPERT: "专家",
                ParticipantRole.PARTICIPANT: "参会者",
                ParticipantRole.OBSERVER: "观察员",
            }.get(p.role, "参会者")
            history_lines.append(f"- {p.instance_id} ({role_name})" + (f": {p.expertise}" if p.expertise else ""))

        history_lines.append("")
        history_lines.append("## 会议记录:")

        for msg in messages:
            participant = participant_map.get(msg.instance_id)
            name = participant.instance_id if participant else msg.instance_id
            history_lines.append(f"[轮次{msg.round_number}] {name}: {msg.content}")

        return "\n".join(history_lines)

    async def invite_participant_to_speak(
        self,
        meeting_id: str,
        participant: MeetingParticipant,
        meeting: Meeting
    ) -> bool:
        """Invite a participant to speak by sending a message to their instance."""
        connector = self.connector_pool.get_connector(participant.instance_id)
        if not connector or not connector.is_connected:
            return False

        # Build history prompt
        history_prompt = await self.build_history_prompt(meeting_id, meeting.current_round)

        # Build invitation message
        invitation = f"""
你被邀请参加会议讨论。请根据你的角色和专业发言。

{history_prompt}

---
请你发言。请简明扼要地表达你的观点，你的发言将被记录在会议中并广播给所有参会者。
"""

        # Send message to the instance
        result = await connector.send_message(
            channel="meeting",
            session_id=f"meeting:{meeting_id}",
            content=invitation
        )

        return result is not None

    async def handle_meeting_reply(
        self,
        meeting_id: str,
        instance_id: str,
        content: str
    ) -> Optional[MeetingMessage]:
        """Handle a reply from an instance in a meeting."""
        # Get the meeting
        result = await self.db.execute(
            select(Meeting).where(Meeting.id == meeting_id)
        )
        meeting = result.scalar_one_or_none()
        if not meeting or meeting.status != MeetingStatus.IN_PROGRESS:
            return None

        # Get the participant
        result = await self.db.execute(
            select(MeetingParticipant).where(
                and_(
                    MeetingParticipant.meeting_id == meeting_id,
                    MeetingParticipant.instance_id == instance_id
                )
            )
        )
        participant = result.scalar_one_or_none()
        if not participant:
            return None

        # Get next speaking order
        speaking_order = await self.get_next_speaking_order(meeting_id, meeting.current_round)

        # Create message
        message = await self.create_message(
            meeting_id=meeting_id,
            participant_id=participant.id,
            instance_id=instance_id,
            content=content,
            round_number=meeting.current_round,
            speaking_order=speaking_order,
            message_type="statement",
        )

        # Update participant last spoken time
        participant.last_spoken_at = beijing_now_naive()
        await self.db.commit()

        return message