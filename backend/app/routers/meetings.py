"""
Meeting Management API Router
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import (
    MeetingStatus, MeetingType, ParticipantRole,
    MeetingRoundStatus,
)
from app.schemas import (
    MeetingCreate,
    MeetingUpdate,
    MeetingResponse,
    MeetingList,
    ParticipantCreate,
    ParticipantUpdate,
    ParticipantResponse,
    ParticipantList,
    ParticipantsReorder,
    MeetingMessageResponse,
    MeetingMessageList,
    MeetingMessageCreate,
    MeetingRoundResponse,
    MeetingRoundList,
    MeetingRoundCreate,
    MeetingTranscript,
    SpeakInvitation,
    NextSpeakerRequest,
    DirectMessageRequest,
    MeetingStatus as MeetingStatusSchema,
    MeetingType as MeetingTypeSchema,
    ParticipantRole as ParticipantRoleSchema,
    MeetingRoundStatus as MeetingRoundStatusSchema,
)
from app.services.meeting_service import (
    MeetingService,
    ParticipantService,
    MeetingRoundService,
    MeetingMessageService,
)
from app.services.meeting_flow_service import MeetingFlowService
from app.services.socketio_service import push_meeting_update, push_meeting_message

router = APIRouter(prefix="/meetings", tags=["meetings"])


async def get_db():
    async with AsyncSessionLocal() as db:
        yield db


# ============================================================================
# Meeting CRUD
# ============================================================================

@router.post("", response_model=MeetingResponse)
async def create_meeting(
    data: MeetingCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new meeting."""
    service = MeetingService(db)
    meeting = await service.create_meeting(data)
    return meeting


@router.get("", response_model=MeetingList)
async def list_meetings(
    status: Optional[MeetingStatusSchema] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List all meetings with optional filtering."""
    service = MeetingService(db)
    status_filter = MeetingStatus(status.value) if status else None
    meetings = await service.list_meetings(
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    total = await service.count_meetings(status=status_filter)
    return MeetingList(items=meetings, total=total)


@router.get("/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(
    meeting_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a meeting by ID."""
    service = MeetingService(db)
    meeting = await service.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting


@router.patch("/{meeting_id}", response_model=MeetingResponse)
async def update_meeting(
    meeting_id: str,
    data: MeetingUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a meeting."""
    service = MeetingService(db)
    meeting = await service.update_meeting(meeting_id, data)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting


@router.delete("/{meeting_id}")
async def delete_meeting(
    meeting_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a meeting."""
    service = MeetingService(db)
    success = await service.delete_meeting(meeting_id)
    if not success:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return {"success": True}


# ============================================================================
# Meeting Lifecycle
# ============================================================================

@router.post("/{meeting_id}/ready", response_model=MeetingResponse)
async def set_meeting_ready(
    meeting_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Set meeting status to READY."""
    service = MeetingService(db)
    meeting = await service.set_ready(meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=400,
            detail="Meeting not found or not in draft status"
        )
    return meeting


@router.post("/{meeting_id}/start", response_model=MeetingResponse)
async def start_meeting(
    meeting_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Start a meeting."""
    service = MeetingService(db)
    meeting = await service.start_meeting(meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=400,
            detail="Meeting not found or cannot be started"
        )

    # Notify via Socket.IO
    await push_meeting_update(
        meeting_id,
        "started",
        {"status": meeting.status.value, "current_round": meeting.current_round}
    )

    # Start the meeting flow (invite host to open)
    flow_service = MeetingFlowService(db)
    await flow_service.start_meeting_flow(meeting_id)

    return meeting


@router.post("/{meeting_id}/pause", response_model=MeetingResponse)
async def pause_meeting(
    meeting_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Pause a meeting."""
    service = MeetingService(db)
    meeting = await service.pause_meeting(meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=400,
            detail="Meeting not found or not in progress"
        )

    # Notify via Socket.IO
    await push_meeting_update(
        meeting_id,
        "paused",
        {"status": meeting.status.value}
    )

    return meeting


@router.post("/{meeting_id}/resume", response_model=MeetingResponse)
async def resume_meeting(
    meeting_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Resume a paused meeting."""
    service = MeetingService(db)
    meeting = await service.resume_meeting(meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=400,
            detail="Meeting not found or not paused"
        )

    # Notify via Socket.IO
    await push_meeting_update(
        meeting_id,
        "resumed",
        {"status": meeting.status.value}
    )

    return meeting


@router.post("/{meeting_id}/end", response_model=MeetingResponse)
async def end_meeting(
    meeting_id: str,
    db: AsyncSession = Depends(get_db),
):
    """End a meeting."""
    service = MeetingService(db)
    meeting = await service.end_meeting(meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=400,
            detail="Meeting not found or not in progress/paused"
        )

    # Notify via Socket.IO
    await push_meeting_update(
        meeting_id,
        "ended",
        {"status": meeting.status.value}
    )

    return meeting


@router.post("/{meeting_id}/cancel", response_model=MeetingResponse)
async def cancel_meeting(
    meeting_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Cancel a meeting."""
    service = MeetingService(db)
    meeting = await service.cancel_meeting(meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=400,
            detail="Meeting not found or already completed"
        )

    # Notify via Socket.IO
    await push_meeting_update(
        meeting_id,
        "cancelled",
        {"status": meeting.status.value}
    )

    return meeting


# ============================================================================
# Participants
# ============================================================================

@router.get("/{meeting_id}/participants", response_model=ParticipantList)
async def list_participants(
    meeting_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List all participants for a meeting."""
    meeting_service = MeetingService(db)
    meeting = await meeting_service.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    participant_service = ParticipantService(db)
    participants = await participant_service.list_participants(meeting_id)
    return ParticipantList(items=participants, total=len(participants))


@router.post("/{meeting_id}/participants", response_model=ParticipantResponse)
async def add_participant(
    meeting_id: str,
    data: ParticipantCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add a participant to a meeting."""
    meeting_service = MeetingService(db)
    meeting = await meeting_service.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    participant_service = ParticipantService(db)
    participant = await participant_service.add_participant(meeting_id, data)
    return participant


@router.get("/participants/{participant_id}", response_model=ParticipantResponse)
async def get_participant(
    participant_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a participant by ID."""
    service = ParticipantService(db)
    participant = await service.get_participant(participant_id)
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    return participant


@router.patch("/participants/{participant_id}", response_model=ParticipantResponse)
async def update_participant(
    participant_id: str,
    data: ParticipantUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a participant."""
    service = ParticipantService(db)
    participant = await service.update_participant(participant_id, data)
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    return participant


@router.delete("/participants/{participant_id}")
async def remove_participant(
    participant_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Remove a participant from a meeting."""
    service = ParticipantService(db)
    success = await service.remove_participant(participant_id)
    if not success:
        raise HTTPException(status_code=404, detail="Participant not found")
    return {"success": True}


@router.post("/{meeting_id}/participants/reorder", response_model=ParticipantList)
async def reorder_participants(
    meeting_id: str,
    data: ParticipantsReorder,
    db: AsyncSession = Depends(get_db),
):
    """Reorder participants by speaking order."""
    meeting_service = MeetingService(db)
    meeting = await meeting_service.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    participant_service = ParticipantService(db)
    participants = await participant_service.reorder_participants(
        meeting_id, data.participant_orders
    )
    return ParticipantList(items=participants, total=len(participants))


# ============================================================================
# Rounds
# ============================================================================

@router.get("/{meeting_id}/rounds", response_model=MeetingRoundList)
async def list_rounds(
    meeting_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List all rounds for a meeting."""
    meeting_service = MeetingService(db)
    meeting = await meeting_service.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    round_service = MeetingRoundService(db)
    rounds = await round_service.list_rounds(meeting_id)
    return MeetingRoundList(items=rounds, total=len(rounds))


@router.post("/{meeting_id}/rounds", response_model=MeetingRoundResponse)
async def start_next_round(
    meeting_id: str,
    data: MeetingRoundCreate = None,
    db: AsyncSession = Depends(get_db),
):
    """Start the next round in a meeting."""
    meeting_service = MeetingService(db)
    meeting = await meeting_service.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if meeting.status != MeetingStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=400,
            detail="Meeting is not in progress"
        )

    round_service = MeetingRoundService(db)
    topic = data.topic if data else None
    new_round = await round_service.start_next_round(meeting_id, topic)
    if not new_round:
        raise HTTPException(
            status_code=400,
            detail="Maximum rounds reached or meeting not in progress"
        )

    # Notify via Socket.IO
    await push_meeting_update(
        meeting_id,
        "new_round",
        {"round_number": new_round.round_number, "topic": new_round.topic}
    )

    return new_round


@router.post("/rounds/{round_id}/complete", response_model=MeetingRoundResponse)
async def complete_round(
    round_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Complete a round."""
    round_service = MeetingRoundService(db)
    meeting_round = await round_service.complete_round(round_id)
    if not meeting_round:
        raise HTTPException(status_code=404, detail="Round not found")
    return meeting_round


# ============================================================================
# Messages
# ============================================================================

@router.get("/{meeting_id}/messages", response_model=MeetingMessageList)
async def list_messages(
    meeting_id: str,
    round_number: Optional[int] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Get messages for a meeting."""
    meeting_service = MeetingService(db)
    meeting = await meeting_service.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    message_service = MeetingMessageService(db)
    messages = await message_service.get_messages(
        meeting_id, round_number=round_number, limit=limit
    )
    total = await message_service.get_message_count(meeting_id)
    return MeetingMessageList(items=messages, total=total)


@router.post("/{meeting_id}/messages", response_model=MeetingMessageResponse)
async def send_message(
    meeting_id: str,
    data: MeetingMessageCreate,
    participant_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Send a message to a meeting (typically used by host)."""
    meeting_service = MeetingService(db)
    meeting = await meeting_service.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if meeting.status != MeetingStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=400,
            detail="Meeting is not in progress"
        )

    participant_service = ParticipantService(db)
    participant = await participant_service.get_participant(participant_id)
    if not participant or participant.meeting_id != meeting_id:
        raise HTTPException(status_code=404, detail="Participant not found in this meeting")

    message_service = MeetingMessageService(db)
    speaking_order = await message_service.get_next_speaking_order(
        meeting_id, meeting.current_round
    )

    message = await message_service.create_message(
        meeting_id=meeting_id,
        participant_id=participant_id,
        instance_id=participant.instance_id,
        content=data.content,
        round_number=meeting.current_round,
        speaking_order=speaking_order,
        message_type=data.message_type,
    )

    # Broadcast via Socket.IO
    await push_meeting_message(meeting_id, {
        "id": message.id,
        "participant_id": participant_id,
        "instance_id": participant.instance_id,
        "content": message.content,
        "round_number": message.round_number,
        "speaking_order": message.speaking_order,
        "message_type": message.message_type,
    })

    return message


@router.post("/{meeting_id}/invite-speak")
async def invite_speak(
    meeting_id: str,
    data: SpeakInvitation,
    db: AsyncSession = Depends(get_db),
):
    """Invite a participant to speak."""
    meeting_service = MeetingService(db)
    meeting = await meeting_service.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if meeting.status != MeetingStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=400,
            detail="Meeting is not in progress"
        )

    participant_service = ParticipantService(db)
    participant = await participant_service.get_participant(data.participant_id)
    if not participant or participant.meeting_id != meeting_id:
        raise HTTPException(status_code=404, detail="Participant not found in this meeting")

    message_service = MeetingMessageService(db)
    success = await message_service.invite_participant_to_speak(
        meeting_id, participant, meeting
    )

    if not success:
        raise HTTPException(
            status_code=400,
            detail="Failed to invite participant - instance may not be connected"
        )

    # Notify via Socket.IO
    await push_meeting_update(
        meeting_id,
        "speaker_invited",
        {
            "participant_id": data.participant_id,
            "instance_id": participant.instance_id,
        }
    )

    return {"success": True, "participant_id": data.participant_id}


@router.post("/{meeting_id}/direct-message")
async def send_direct_message(
    meeting_id: str,
    data: DirectMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    """Send a direct message from host to a specific participant."""
    from app.connectors.ao_plugin import get_connector_pool

    meeting_service = MeetingService(db)
    meeting = await meeting_service.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if meeting.status != MeetingStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=400,
            detail="Meeting is not in progress"
        )

    participant_service = ParticipantService(db)
    participant = await participant_service.get_participant(data.participant_id)
    if not participant or participant.meeting_id != meeting_id:
        raise HTTPException(status_code=404, detail="Participant not found in this meeting")

    # Get connector and send message to the participant's instance
    connector_pool = get_connector_pool()
    connector = connector_pool.get_connector(participant.instance_id)
    if not connector or not connector.is_connected:
        raise HTTPException(
            status_code=400,
            detail="Participant's instance is not connected"
        )

    # Build context with meeting info
    message_service = MeetingMessageService(db)
    history_prompt = await message_service.build_history_prompt(meeting_id, meeting.current_round)

    # Build the direct message
    full_message = f"""
主持人发来消息：

{data.content}

---

会议上下文：
{history_prompt}
"""

    # Send to the participant's instance
    result = await connector.send_message(
        channel="meeting",
        session_id=f"meeting:{meeting_id}",
        content=full_message
    )

    if not result:
        raise HTTPException(
            status_code=500,
            detail="Failed to send message to participant"
        )

    # Notify via Socket.IO
    await push_meeting_update(
        meeting_id,
        "direct_message_sent",
        {
            "participant_id": data.participant_id,
            "instance_id": participant.instance_id,
            "content": data.content,
        }
    )

    return {"success": True, "message": "Message sent to participant"}


@router.post("/{meeting_id}/next-speaker")
async def set_next_speaker(
    meeting_id: str,
    data: NextSpeakerRequest,
    db: AsyncSession = Depends(get_db),
):
    """Set the next speaker in the meeting."""
    meeting_service = MeetingService(db)
    meeting = await meeting_service.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if meeting.status != MeetingStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=400,
            detail="Meeting is not in progress"
        )

    participant_service = ParticipantService(db)
    participant = await participant_service.get_participant(data.participant_id)
    if not participant or participant.meeting_id != meeting_id:
        raise HTTPException(status_code=404, detail="Participant not found in this meeting")

    # Notify via Socket.IO
    await push_meeting_update(
        meeting_id,
        "next_speaker",
        {
            "participant_id": data.participant_id,
            "instance_id": participant.instance_id,
            "role": participant.role.value,
        }
    )

    return {"success": True, "next_speaker": data.participant_id}


# ============================================================================
# Summary & Transcript
# ============================================================================

@router.post("/{meeting_id}/summarize")
async def summarize_meeting(
    meeting_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Generate a meeting summary (calls host agent to summarize)."""
    meeting_service = MeetingService(db)
    meeting = await meeting_service.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if meeting.status != MeetingStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail="Meeting must be completed before summarizing"
        )

    # Build transcript and invite host to summarize
    participant_service = ParticipantService(db)
    host = await participant_service.get_host_participant(meeting_id)

    if not host:
        raise HTTPException(status_code=404, detail="Host participant not found")

    message_service = MeetingMessageService(db)
    history = await message_service.build_history_prompt(meeting_id, meeting.current_round)

    summary_prompt = f"""
{history}

---
会议已结束。请作为主持人，为本次会议生成一份简洁的总结，包括：
1. 主要讨论观点
2. 达成的共识或结论
3. 后续行动建议（如有）

请用简洁的中文撰写总结。
"""

    # Send to host for summarization
    success = await message_service.invite_participant_to_speak(
        meeting_id, host, meeting
    )

    if not success:
        raise HTTPException(
            status_code=400,
            detail="Failed to request summary from host - instance may not be connected"
        )

    return {"success": True, "message": "Summary request sent to host"}


@router.get("/{meeting_id}/transcript", response_model=MeetingTranscript)
async def get_transcript(
    meeting_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get the full meeting transcript."""
    meeting_service = MeetingService(db)
    meeting = await meeting_service.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    participant_service = ParticipantService(db)
    participants = await participant_service.list_participants(meeting_id)

    message_service = MeetingMessageService(db)
    messages = await message_service.get_messages(meeting_id, limit=500)

    round_service = MeetingRoundService(db)
    rounds = await round_service.list_rounds(meeting_id)

    return MeetingTranscript(
        meeting=meeting,
        participants=participants,
        messages=messages,
        rounds=rounds,
    )


# ============================================================================
# Flow Control API
# ============================================================================

@router.post("/{meeting_id}/skip-speaker")
async def skip_current_speaker(
    meeting_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Skip the current speaker and proceed to the next."""
    flow_service = MeetingFlowService(db)
    success = await flow_service.skip_current_speaker(meeting_id)
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Failed to skip speaker - meeting may not be in progress"
        )
    return {"success": True}


@router.post("/{meeting_id}/override-speaker")
async def override_next_speaker(
    meeting_id: str,
    participant_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Override and specify the next speaker."""
    flow_service = MeetingFlowService(db)
    success = await flow_service.override_next_speaker(meeting_id, participant_id)
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Failed to override speaker - meeting or participant not found"
        )
    return {"success": True, "participant_id": participant_id}


@router.post("/{meeting_id}/force-next-round")
async def force_next_round(
    meeting_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Force the meeting to proceed to the next round."""
    flow_service = MeetingFlowService(db)
    success = await flow_service.force_next_round(meeting_id)
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Failed to force next round - meeting may have ended"
        )
    return {"success": True}


@router.post("/{meeting_id}/submit-summary")
async def submit_round_summary(
    meeting_id: str,
    round_number: int = Query(...),
    content: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Submit a round summary (called by host after generating summary)."""
    flow_service = MeetingFlowService(db)
    success = await flow_service.complete_round_and_proceed(meeting_id, round_number, content)
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Failed to submit summary"
        )
    return {"success": True}


@router.post("/{meeting_id}/toggle-auto-proceed")
async def toggle_auto_proceed(
    meeting_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Toggle auto-proceed mode for the meeting."""
    service = MeetingService(db)
    meeting = await service.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    meeting.auto_proceed = not meeting.auto_proceed
    await db.commit()

    # Notify via Socket.IO
    await push_meeting_update(
        meeting_id,
        "auto_proceed_toggled",
        {"auto_proceed": meeting.auto_proceed}
    )

    return {"success": True, "auto_proceed": meeting.auto_proceed}


@router.get("/{meeting_id}/context")
async def get_speaker_context(
    meeting_id: str,
    participant_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Get the speaking context for a participant (for advanced agents to query)."""
    service = MeetingService(db)
    meeting = await service.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    participant_service = ParticipantService(db)
    participant = await participant_service.get_participant(participant_id)
    if not participant or participant.meeting_id != meeting_id:
        raise HTTPException(status_code=404, detail="Participant not found")

    # Build context
    message_service = MeetingMessageService(db)
    messages = await message_service.get_messages(meeting_id, limit=100)

    # Get previous round summaries
    round_service = MeetingRoundService(db)
    rounds = await round_service.list_rounds(meeting_id)
    summaries = []
    for r in rounds:
        if r.round_number < meeting.current_round and r.summary:
            summaries.append({
                "round_number": r.round_number,
                "summary": r.summary
            })

    return {
        "meeting": {
            "id": meeting.id,
            "title": meeting.title,
            "current_round": meeting.current_round,
            "max_rounds": meeting.max_rounds,
        },
        "participant": {
            "id": participant.id,
            "role": participant.role.value,
            "expertise": participant.expertise,
        },
        "previous_summaries": summaries,
        "recent_messages": [
            {
                "instance_id": m.instance_id,
                "content": m.content,
                "round_number": m.round_number,
                "message_type": m.message_type,
            }
            for m in messages[-20:]  # Last 20 messages
        ],
    }