"""
Meeting Flow Service

Controls the automatic flow of meetings:
- Starting meetings and inviting host to open
- Proceeding to next speaker after each response
- Requesting round summaries
- Advancing rounds or ending meetings
"""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Meeting, MeetingStatus, MeetingType, MeetingRound, MeetingRoundStatus,
    MeetingParticipant, ParticipantRole, MeetingMessage, Instance
)
from app.services.meeting_service import ParticipantService, MeetingRoundService, MeetingMessageService
from app.services.prompt_service import PromptService
from app.services.socketio_service import push_meeting_update, push_meeting_message
from app.connectors.ao_plugin import get_connector_pool
from app.utils.time_utils import beijing_now_naive


# 会议类型中文标签
MEETING_TYPE_LABELS = {
    MeetingType.BRAINSTORM: "头脑风暴",
    MeetingType.EXPERT_DISCUSSION: "专家讨论",
    MeetingType.DECISION_MAKING: "决策制定",
    MeetingType.PROBLEM_SOLVING: "问题解决",
    MeetingType.REVIEW: "评审",
}

# 参会者角色中文标签
PARTICIPANT_ROLE_LABELS = {
    ParticipantRole.HOST: "主持人",
    ParticipantRole.EXPERT: "专家",
    ParticipantRole.PARTICIPANT: "参会者",
    ParticipantRole.OBSERVER: "观察员",
}


class MeetingFlowService:
    """会议流程自动控制服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.participant_service = ParticipantService(db)
        self.round_service = MeetingRoundService(db)
        self.message_service = MeetingMessageService(db)
        self.prompt_service = PromptService(db)

    async def get_meeting(self, meeting_id: str) -> Optional[Meeting]:
        """获取会议"""
        result = await self.db.execute(
            select(Meeting).where(Meeting.id == meeting_id)
        )
        return result.scalar_one_or_none()

    async def start_meeting_flow(self, meeting_id: str) -> bool:
        """
        开始会议流程

        1. 获取或创建第一轮
        2. 邀请主持人开场
        """
        meeting = await self.get_meeting(meeting_id)
        if not meeting or meeting.status != MeetingStatus.IN_PROGRESS:
            return False

        # 获取主持人
        host = await self.participant_service.get_host_participant(meeting_id)
        if not host:
            return False

        # 获取或创建第一轮
        current_round = await self.round_service.get_current_round(meeting_id)
        if not current_round:
            # 如果没有轮次，创建第一轮
            current_round = await self.round_service.start_next_round(meeting_id)
            if not current_round:
                return False
            meeting.current_round = 1
        elif current_round.status != MeetingRoundStatus.IN_PROGRESS:
            # 如果轮次不是进行中，更新状态
            current_round.status = MeetingRoundStatus.IN_PROGRESS
            current_round.started_at = beijing_now_naive()
            await self.db.commit()

        # 更新会议状态
        meeting.current_speaker_id = host.id
        meeting.waiting_for_summary = False
        await self.db.commit()

        # 构建开场提示词并邀请主持人
        success = await self._invite_host_opening(meeting, host, current_round)

        if success:
            # 通知前端
            await push_meeting_update(meeting_id, "meeting_started", {
                "round_number": meeting.current_round,
                "current_speaker_id": host.id,
            })

        return success

    async def proceed_to_next_speaker(self, meeting_id: str, from_participant_id: str) -> bool:
        """
        推进到下一位发言人

        Args:
            meeting_id: 会议ID
            from_participant_id: 刚刚发言完的参会者ID

        Returns:
            是否成功推进
        """
        meeting = await self.get_meeting(meeting_id)
        if not meeting or meeting.status != MeetingStatus.IN_PROGRESS:
            return False

        # 获取所有活跃参会者（按发言顺序排序）
        participants = await self.participant_service.list_active_participants(meeting_id)
        if not participants:
            return False

        # 获取主持人
        host = await self.participant_service.get_host_participant(meeting_id)

        # 获取当前轮次已经发言过的参会者
        messages = await self.message_service.get_messages(meeting_id, round_number=meeting.current_round)
        spoken_participant_ids = set()
        for msg in messages:
            if msg.message_type != "round_summary":
                spoken_participant_ids.add(msg.participant_id)

        # 找到刚刚发言者的角色
        current_is_host = False
        for p in participants:
            if p.id == from_participant_id:
                current_is_host = (p.role == ParticipantRole.HOST)
                break

        # 找到下一位发言人
        # 如果刚发言的是主持人，找下一个还没发言的参会者
        # 如果刚发言的是参会者，主持人引导后找下一个还没发言的参会者
        next_participant = None
        for p in participants:
            if p.role == ParticipantRole.OBSERVER:
                continue  # 跳过观察员
            if p.id in spoken_participant_ids:
                continue  # 跳过已经发言过的
            if p.role == ParticipantRole.HOST:
                continue  # 主持人不参与普通发言顺序
            if next_participant is None or p.speaking_order < next_participant.speaking_order:
                next_participant = p

        if next_participant:
            # 有下一位发言人
            if current_is_host:
                # 主持人刚说完（引导），直接邀请下一位发言
                meeting.current_speaker_id = next_participant.id
                await self.db.commit()

                success = await self._invite_participant_speak(meeting, next_participant)

                if success:
                    await push_meeting_update(meeting_id, "speaker_changed", {
                        "current_speaker_id": next_participant.id,
                        "participant_id": next_participant.id,
                    })

                return success
            else:
                # 参会者刚说完，主持人引导后邀请下一位
                if host and meeting.auto_proceed:
                    # 先让主持人引导下一位发言
                    meeting.current_speaker_id = host.id
                    await self.db.commit()

                    # 获取当前轮次
                    current_round_result = await self.db.execute(
                        select(MeetingRound).where(
                            MeetingRound.meeting_id == meeting_id,
                            MeetingRound.round_number == meeting.current_round
                        )
                    )
                    current_round = current_round_result.scalar_one_or_none()

                    if current_round:
                        success = await self._invite_host_guide_speaker(meeting, host, next_participant, current_round)
                    else:
                        # 没有轮次信息，直接邀请下一位
                        meeting.current_speaker_id = next_participant.id
                        await self.db.commit()
                        success = await self._invite_participant_speak(meeting, next_participant)

                    if success:
                        await push_meeting_update(meeting_id, "host_guiding", {
                            "host_participant_id": host.id,
                            "next_speaker_id": next_participant.id,
                        })

                    return success
                else:
                    # 没有主持人或不自动推进，直接邀请
                    meeting.current_speaker_id = next_participant.id
                    await self.db.commit()

                    success = await self._invite_participant_speak(meeting, next_participant)

                    if success:
                        await push_meeting_update(meeting_id, "speaker_changed", {
                            "current_speaker_id": next_participant.id,
                            "participant_id": next_participant.id,
                        })

                    return success
        else:
            # 本轮所有参会者都已发言完毕，邀请主持人摘要
            return await self._request_round_summary(meeting)

    async def _request_round_summary(self, meeting: Meeting) -> bool:
        """
        邀请主持人生成轮次摘要

        Returns:
            是否成功邀请
        """
        meeting_id = meeting.id

        # 获取主持人
        host = await self.participant_service.get_host_participant(meeting_id)
        if not host:
            return False

        # 更新状态
        meeting.waiting_for_summary = True
        meeting.current_speaker_id = host.id
        await self.db.commit()

        # 构建轮次摘要提示词
        template = await self.prompt_service.get_template(meeting.prompt_template_id)
        if not template:
            template = await self.prompt_service.ensure_default_template_exists()

        # 获取本轮消息
        messages = await self.message_service.get_messages(meeting_id, round_number=meeting.current_round)
        instance_map = await self._get_instance_map()
        round_messages = self._format_messages_for_prompt(messages, instance_map)

        prompt = self.prompt_service.render_round_summary(
            template=template,
            meeting_title=meeting.title,
            round_number=meeting.current_round,
            round_messages=round_messages,
        )

        # 发送给主持人
        success = await self._send_to_instance(
            instance_id=host.instance_id,
            meeting_id=meeting_id,
            content=prompt,
            metadata={"message_type": "summary_request", "round_number": meeting.current_round}
        )

        if success:
            await push_meeting_update(meeting_id, "summary_requested", {
                "round_number": meeting.current_round,
                "host_participant_id": host.id,
            })

        return success

    async def complete_round_and_proceed(self, meeting_id: str, round_number: int, summary: str) -> bool:
        """
        完成轮次摘要，进入下一轮或结束会议

        Args:
            meeting_id: 会议ID
            round_number: 轮次号
            summary: 摘要内容

        Returns:
            是否成功
        """
        meeting = await self.get_meeting(meeting_id)
        if not meeting:
            return False

        # 获取主持人
        host = await self.participant_service.get_host_participant(meeting_id)
        if not host:
            return False

        # 存储摘要消息
        await self.message_service.create_message(
            meeting_id=meeting_id,
            participant_id=host.id,
            instance_id=host.instance_id,
            content=summary,
            round_number=round_number,
            speaking_order=999,  # 摘要放最后
            message_type="round_summary",
        )

        # 更新轮次记录
        await self.round_service.complete_round_with_summary(
            meeting_id=meeting_id,
            round_number=round_number,
            summary=summary,
            summarized_by=host.id,
        )

        # 广播摘要
        await push_meeting_message(meeting_id, {
            "participant_id": host.id,
            "instance_id": host.instance_id,
            "content": summary,
            "round_number": round_number,
            "message_type": "round_summary",
        })

        # 判断是否还有下一轮
        if meeting.current_round >= meeting.max_rounds:
            # 会议结束
            return await self._end_meeting(meeting)
        else:
            # 开始下一轮
            return await self._start_next_round(meeting)

    async def _start_next_round(self, meeting: Meeting) -> bool:
        """开始下一轮"""
        meeting_id = meeting.id

        # 创建新一轮
        new_round = await self.round_service.start_next_round(meeting_id)
        if not new_round:
            return False

        # 更新会议状态
        meeting.current_round = new_round.round_number
        meeting.waiting_for_summary = False
        await self.db.commit()

        # 获取第一位发言人（通常是主持人开场，或者是发言顺序第一的参会者）
        participants = await self.participant_service.list_active_participants(meeting_id)
        host = await self.participant_service.get_host_participant(meeting_id)

        # 找第一个非观察员、非主持人
        first_speaker = None
        for p in participants:
            if p.role not in [ParticipantRole.OBSERVER, ParticipantRole.HOST]:
                if first_speaker is None or p.speaking_order < first_speaker.speaking_order:
                    first_speaker = p

        if not first_speaker:
            first_speaker = host

        if not first_speaker:
            return False

        # 邀请主持人引导发言
        if first_speaker != host and meeting.auto_proceed:
            # 先让主持人引导，current_speaker_id 设为主持人
            meeting.current_speaker_id = host.id
            await self.db.commit()

            success = await self._invite_host_guide_speaker(meeting, host, first_speaker, new_round)
            if not success:
                # 如果主持人引导失败，直接邀请参会者
                meeting.current_speaker_id = first_speaker.id
                await self.db.commit()
                success = await self._invite_participant_speak(meeting, first_speaker)
        else:
            # 直接邀请发言
            meeting.current_speaker_id = first_speaker.id
            await self.db.commit()

            success = await self._invite_participant_speak(meeting, first_speaker)

        if success:
            await push_meeting_update(meeting_id, "new_round_started", {
                "round_number": new_round.round_number,
                "current_speaker_id": meeting.current_speaker_id,
            })

        return success

    async def _end_meeting(self, meeting: Meeting) -> bool:
        """结束会议"""
        meeting_id = meeting.id

        # 获取主持人
        host = await self.participant_service.get_host_participant(meeting_id)
        if not host:
            # 没有主持人，直接结束
            meeting.status = MeetingStatus.COMPLETED
            from app.utils.time_utils import beijing_now_naive
            meeting.completed_at = beijing_now_naive()
            await self.db.commit()
            return True

        # 邀请主持人生成会议总结
        template = await self.prompt_service.get_template(meeting.prompt_template_id)
        if not template:
            template = await self.prompt_service.ensure_default_template_exists()

        # 获取所有轮次摘要
        rounds = await self.round_service.list_rounds(meeting_id)
        summaries = []
        for r in rounds:
            if r.summary:
                summaries.append(f"### 第 {r.round_number} 轮\n{r.summary}")

        all_summaries = "\n\n".join(summaries) if summaries else "暂无摘要"

        prompt = self.prompt_service.render_closing_summary(
            template=template,
            meeting_title=meeting.title,
            meeting_type_label=MEETING_TYPE_LABELS.get(meeting.meeting_type, "会议"),
            max_rounds=meeting.max_rounds,
            all_round_summaries=all_summaries,
        )

        meeting.waiting_for_summary = True
        await self.db.commit()

        success = await self._send_to_instance(
            instance_id=host.instance_id,
            meeting_id=meeting_id,
            content=prompt,
            metadata={"message_type": "closing_request"}
        )

        if success:
            await push_meeting_update(meeting_id, "closing_requested", {
                "host_participant_id": host.id,
            })

        return success

    async def _invite_host_opening(self, meeting: Meeting, host: MeetingParticipant, current_round: MeetingRound) -> bool:
        """邀请主持人开场"""
        template = await self.prompt_service.get_template(meeting.prompt_template_id)
        if not template:
            template = await self.prompt_service.ensure_default_template_exists()

        # 获取参会者信息
        participants = await self.participant_service.list_participants(meeting.id)
        participants_info = self._format_participants_info(participants)

        prompt = self.prompt_service.render_opening(
            template=template,
            meeting_title=meeting.title,
            meeting_type_label=MEETING_TYPE_LABELS.get(meeting.meeting_type, "会议"),
            meeting_description=meeting.description or "",
            max_rounds=meeting.max_rounds,
            participants_info=participants_info,
        )

        return await self._send_to_instance(
            instance_id=host.instance_id,
            meeting_id=meeting.id,
            content=prompt,
            metadata={"message_type": "opening_request", "round_number": 1}
        )

    async def _invite_host_guide_speaker(self, meeting: Meeting, host: MeetingParticipant, speaker: MeetingParticipant, current_round: MeetingRound) -> bool:
        """邀请主持人引导下一位发言人"""
        template = await self.prompt_service.get_template(meeting.prompt_template_id)
        if not template:
            template = await self.prompt_service.ensure_default_template_exists()

        # 获取发言人实例信息
        instance_map = await self._get_instance_map()
        speaker_instance = instance_map.get(speaker.instance_id)

        # 获取当前轮次消息
        messages = await self.message_service.get_messages(meeting.id, round_number=current_round.round_number)
        current_messages = self._format_messages_for_prompt(messages, instance_map)

        # 获取之前轮次摘要
        previous_summaries = await self._get_previous_summaries(meeting.id, current_round.round_number)

        # 获取刚发言的人的名称（用于感谢）
        previous_speaker_name = None
        if messages:
            last_msg = messages[-1]
            prev_instance = instance_map.get(last_msg.instance_id)
            previous_speaker_name = prev_instance.name if prev_instance else None

        prompt = self.prompt_service.render_free_speak(
            template=template,
            meeting_title=meeting.title,
            round_number=current_round.round_number,
            max_rounds=meeting.max_rounds,
            previous_summaries=previous_summaries,
            current_round_messages=current_messages,
            speaker_name=speaker_instance.name if speaker_instance else speaker.instance_id,
            speaker_role=PARTICIPANT_ROLE_LABELS.get(speaker.role, "参会者"),
            speaker_expertise=speaker.expertise or "",
            previous_speaker_name=previous_speaker_name,
        )

        return await self._send_to_instance(
            instance_id=host.instance_id,
            meeting_id=meeting.id,
            content=prompt,
            metadata={"message_type": "guide_request", "next_speaker_id": speaker.id}
        )

    async def _invite_participant_speak(self, meeting: Meeting, participant: MeetingParticipant) -> bool:
        """邀请参会者发言"""
        template = await self.prompt_service.get_template(meeting.prompt_template_id)
        if not template:
            template = await self.prompt_service.ensure_default_template_exists()

        # 获取实例信息
        instance_map = await self._get_instance_map()
        participant_instance = instance_map.get(participant.instance_id)

        # 获取当前轮次消息
        messages = await self.message_service.get_messages(meeting.id, round_number=meeting.current_round)
        current_messages = self._format_messages_for_prompt(messages, instance_map)

        # 获取之前轮次摘要
        previous_summaries = await self._get_previous_summaries(meeting.id, meeting.current_round)

        prompt = self.prompt_service.render_participant_speak(
            template=template,
            meeting_title=meeting.title,
            meeting_type_label=MEETING_TYPE_LABELS.get(meeting.meeting_type, "会议"),
            round_number=meeting.current_round,
            max_rounds=meeting.max_rounds,
            your_role=PARTICIPANT_ROLE_LABELS.get(participant.role, "参会者"),
            your_expertise=participant.expertise or "",
            previous_summaries=previous_summaries,
            current_round_messages=current_messages,
            host_invitation="请分享你的观点。",
        )

        return await self._send_to_instance(
            instance_id=participant.instance_id,
            meeting_id=meeting.id,
            content=prompt,
            metadata={"message_type": "speak_request", "round_number": meeting.current_round}
        )

    async def _send_to_instance(
        self,
        instance_id: str,
        meeting_id: str,
        content: str,
        metadata: dict = None
    ) -> bool:
        """发送消息到智能体实例"""
        connector_pool = get_connector_pool()
        connector = connector_pool.get_connector(instance_id)

        if not connector or not connector.is_connected:
            return False

        # 构建消息
        full_message = content
        if metadata:
            import json
            full_message = f"{content}\n\n[METADATA:{json.dumps(metadata)}]"

        result = await connector.send_message(
            channel="meeting",
            session_id=f"meeting:{meeting_id}",
            content=full_message
        )

        return result is not None

    async def _get_previous_summaries(self, meeting_id: str, current_round: int) -> str:
        """获取之前轮次的摘要"""
        rounds = await self.round_service.list_rounds(meeting_id)
        summaries = []
        for r in rounds:
            if r.round_number < current_round and r.summary:
                summaries.append(f"### 第 {r.round_number} 轮\n{r.summary}")
        return "\n\n".join(summaries) if summaries else "暂无"

    async def _get_instance_map(self) -> dict:
        """获取实例ID到实例的映射"""
        result = await self.db.execute(select(Instance))
        instances = result.scalars().all()
        return {i.id: i for i in instances}

    def _format_participants_info(self, participants: list[MeetingParticipant]) -> str:
        """格式化参会者信息"""
        lines = []
        for p in sorted(participants, key=lambda x: x.speaking_order):
            role_label = PARTICIPANT_ROLE_LABELS.get(p.role, "参会者")
            expertise = f" - {p.expertise}" if p.expertise else ""
            lines.append(f"{p.speaking_order}. {role_label}{expertise}")
        return "\n".join(lines)

    def _format_messages_for_prompt(self, messages: list[MeetingMessage], instance_map: dict = None) -> str:
        """格式化消息用于提示词"""
        if not messages:
            return "暂无发言"

        lines = []
        for msg in messages:
            if msg.message_type == "round_summary":
                lines.append(f"\n**本轮摘要**: {msg.content}")
            else:
                # 获取发言人名称
                if instance_map:
                    instance = instance_map.get(msg.instance_id)
                    speaker_name = instance.name if instance else msg.instance_id[:8]
                else:
                    speaker_name = msg.instance_id[:8]
                lines.append(f"[{speaker_name}]: {msg.content}")
        return "\n".join(lines)

    # ==================== 手动控制方法 ====================

    async def skip_current_speaker(self, meeting_id: str) -> bool:
        """跳过当前发言人"""
        meeting = await self.get_meeting(meeting_id)
        if not meeting or not meeting.current_speaker_id:
            return False

        return await self.proceed_to_next_speaker(meeting_id, meeting.current_speaker_id)

    async def override_next_speaker(self, meeting_id: str, participant_id: str) -> bool:
        """指定下一位发言人"""
        meeting = await self.get_meeting(meeting_id)
        if not meeting:
            return False

        participant = await self.participant_service.get_participant(participant_id)
        if not participant or participant.meeting_id != meeting_id:
            return False

        meeting.current_speaker_id = participant_id
        await self.db.commit()

        return await self._invite_participant_speak(meeting, participant)

    async def force_next_round(self, meeting_id: str) -> bool:
        """强制进入下一轮"""
        meeting = await self.get_meeting(meeting_id)
        if not meeting:
            return False

        return await self._start_next_round(meeting)