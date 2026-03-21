"""
Prompt Template Service
"""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PromptTemplate
from app.schemas import PromptTemplateCreate, PromptTemplateUpdate
from app.services.default_templates import DEFAULT_TEMPLATE


class PromptService:
    """提示词模板服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_template(self, template_id: Optional[str] = None) -> Optional[PromptTemplate]:
        """获取模板，未指定则返回默认模板"""
        if template_id:
            template = await self.db.get(PromptTemplate, template_id)
            if template:
                return template

        # 返回默认模板
        result = await self.db.execute(
            select(PromptTemplate).where(PromptTemplate.is_default == True)
        )
        return result.scalar_one_or_none()

    async def get_template_by_code(self, code: str) -> Optional[PromptTemplate]:
        """根据代码获取模板"""
        result = await self.db.execute(
            select(PromptTemplate).where(PromptTemplate.code == code)
        )
        return result.scalar_one_or_none()

    async def list_templates(self) -> list[PromptTemplate]:
        """列出所有模板"""
        result = await self.db.execute(
            select(PromptTemplate).order_by(PromptTemplate.is_default.desc(), PromptTemplate.created_at)
        )
        return list(result.scalars().all())

    async def create_template(self, data: PromptTemplateCreate) -> PromptTemplate:
        """创建自定义模板"""
        template = PromptTemplate(**data.model_dump())
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def update_template(self, template_id: str, data: PromptTemplateUpdate) -> Optional[PromptTemplate]:
        """更新模板"""
        template = await self.db.get(PromptTemplate, template_id)
        if not template:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(template, key, value)

        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def delete_template(self, template_id: str) -> bool:
        """删除模板（系统模板不可删除）"""
        template = await self.db.get(PromptTemplate, template_id)
        if not template:
            return False
        if template.is_system:
            return False

        await self.db.delete(template)
        await self.db.commit()
        return True

    async def set_default_template(self, template_id: str) -> Optional[PromptTemplate]:
        """设置默认模板"""
        template = await self.db.get(PromptTemplate, template_id)
        if not template:
            return None

        # 先清除其他默认
        result = await self.db.execute(
            select(PromptTemplate).where(PromptTemplate.is_default == True)
        )
        for old_default in result.scalars().all():
            old_default.is_default = False

        template.is_default = True
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def ensure_default_template_exists(self) -> PromptTemplate:
        """确保默认模板存在，不存在则创建"""
        existing = await self.get_template()
        if existing:
            return existing

        # 创建默认模板
        template = PromptTemplate(**DEFAULT_TEMPLATE)
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        return template

    def render_template(
        self,
        template: PromptTemplate,
        template_type: str,
        variables: dict
    ) -> str:
        """
        渲染模板，替换变量

        Args:
            template: 模板对象
            template_type: 模板类型 (opening, round_summary, guided_speak, free_speak, closing_summary, participant_speak)
            variables: 变量字典

        Returns:
            渲染后的提示词
        """
        template_attr = f"{template_type}_template"
        template_text = getattr(template, template_attr, "")

        # 添加 max_words 变量
        if "max_opening_words" not in variables:
            variables["max_opening_words"] = template.max_opening_words
        if "max_summary_words" not in variables:
            variables["max_summary_words"] = template.max_summary_words
        if "max_speak_words" not in variables:
            variables["max_speak_words"] = template.max_speak_words

        try:
            return template_text.format(**variables)
        except KeyError as e:
            # 缺少变量时，保留占位符
            return template_text

    def render_opening(
        self,
        template: PromptTemplate,
        meeting_title: str,
        meeting_type_label: str,
        meeting_description: str,
        max_rounds: int,
        participants_info: str
    ) -> str:
        """渲染开场提示词"""
        return self.render_template(template, "opening", {
            "meeting_title": meeting_title,
            "meeting_type_label": meeting_type_label,
            "meeting_description": meeting_description or "无",
            "max_rounds": max_rounds,
            "participants_info": participants_info,
        })

    def render_round_summary(
        self,
        template: PromptTemplate,
        meeting_title: str,
        round_number: int,
        round_messages: str
    ) -> str:
        """渲染轮次摘要提示词"""
        return self.render_template(template, "round_summary", {
            "meeting_title": meeting_title,
            "round_number": round_number,
            "round_messages": round_messages,
        })

    def render_guided_speak(
        self,
        template: PromptTemplate,
        meeting_title: str,
        round_number: int,
        max_rounds: int,
        current_topic: str,
        current_round_messages: str,
        speaker_name: str,
        speaker_role: str,
        speaker_expertise: str
    ) -> str:
        """渲染引导发言提示词"""
        return self.render_template(template, "guided_speak", {
            "meeting_title": meeting_title,
            "round_number": round_number,
            "max_rounds": max_rounds,
            "current_topic": current_topic or "自由讨论",
            "current_round_messages": current_round_messages,
            "speaker_name": speaker_name,
            "speaker_role": speaker_role,
            "speaker_expertise": speaker_expertise or "未指定",
        })

    def render_free_speak(
        self,
        template: PromptTemplate,
        meeting_title: str,
        round_number: int,
        max_rounds: int,
        previous_summaries: str,
        current_round_messages: str,
        speaker_name: str,
        speaker_role: str,
        speaker_expertise: str,
        previous_speaker_name: str = None
    ) -> str:
        """渲染自由发言邀请提示词"""
        return self.render_template(template, "free_speak", {
            "meeting_title": meeting_title,
            "round_number": round_number,
            "max_rounds": max_rounds,
            "previous_summaries": previous_summaries or "暂无",
            "current_round_messages": current_round_messages or "暂无",
            "speaker_name": speaker_name,
            "speaker_role": speaker_role,
            "speaker_expertise": speaker_expertise or "未指定",
            "previous_speaker_name": previous_speaker_name or "",
        })

    def render_closing_summary(
        self,
        template: PromptTemplate,
        meeting_title: str,
        meeting_type_label: str,
        max_rounds: int,
        all_round_summaries: str
    ) -> str:
        """渲染会议总结提示词"""
        return self.render_template(template, "closing_summary", {
            "meeting_title": meeting_title,
            "meeting_type_label": meeting_type_label,
            "max_rounds": max_rounds,
            "all_round_summaries": all_round_summaries,
        })

    def render_participant_speak(
        self,
        template: PromptTemplate,
        meeting_title: str,
        meeting_type_label: str,
        round_number: int,
        max_rounds: int,
        your_role: str,
        your_expertise: str,
        previous_summaries: str,
        current_round_messages: str,
        host_invitation: str,
        role_description: str = "",
        role_task: str = "从你的专业领域出发，针对会议主题发表观点。",
    ) -> str:
        """渲染参会者发言提示词"""
        # 构建角色描述部分
        role_description_section = ""
        if role_description:
            role_description_section = f"- 角色说明：{role_description}"

        return self.render_template(template, "participant_speak", {
            "meeting_title": meeting_title,
            "meeting_type_label": meeting_type_label,
            "round_number": round_number,
            "max_rounds": max_rounds,
            "your_role": your_role,
            "your_expertise": your_expertise or "未指定",
            "previous_summaries": previous_summaries or "暂无",
            "current_round_messages": current_round_messages or "暂无",
            "host_invitation": host_invitation,
            "role_description_section": role_description_section,
            "role_task": role_task,
        })