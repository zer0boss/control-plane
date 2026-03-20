"""
Meeting Type Role Configuration API Router
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import MeetingTypeRoleConfig, MeetingType

router = APIRouter(prefix="/meeting-type-roles", tags=["meeting-type-roles"])


async def get_db():
    async with AsyncSessionLocal() as db:
        yield db


# Default role configurations for each meeting type
DEFAULT_ROLE_CONFIGS = {
    "brainstorm": {
        "name": "头脑风暴",
        "roles": [
            {
                "name": "蓝色思考帽",
                "code": "blue_hat",
                "color": "#3B82F6",
                "description": "主持人 - 负责控制和调节思维过程，规划和管理整个思考过程，并负责做出结论",
                "order": 1,
                "is_host": True,
            },
            {
                "name": "白色思考帽",
                "code": "white_hat",
                "color": "#F3F4F6",
                "description": "中立客观 - 关注客观的事实和数据",
                "order": 2,
                "is_host": False,
            },
            {
                "name": "红色思考帽",
                "code": "red_hat",
                "color": "#EF4444",
                "description": "情感色彩 - 表现情绪、直觉、感受、预感等方面的看法",
                "order": 3,
                "is_host": False,
            },
            {
                "name": "黄色思考帽",
                "code": "yellow_hat",
                "color": "#F59E0B",
                "description": "价值与肯定 - 从正面考虑问题，表达乐观的、满怀希望的、建设性的观点",
                "order": 4,
                "is_host": False,
            },
            {
                "name": "黑色思考帽",
                "code": "black_hat",
                "color": "#1F2937",
                "description": "批判质疑 - 运用否定、怀疑、质疑的看法，合乎逻辑的进行批判",
                "order": 5,
                "is_host": False,
            },
            {
                "name": "绿色思考帽",
                "code": "green_hat",
                "color": "#10B981",
                "description": "创造生机 - 创造性思考、头脑风暴、求异思维",
                "order": 6,
                "is_host": False,
            },
        ],
    },
    "expert_discussion": {
        "name": "专家讨论",
        "roles": [
            {
                "name": "主持人",
                "code": "host",
                "color": "#3B82F6",
                "description": "负责引导讨论，控制节奏，总结发言",
                "order": 1,
                "is_host": True,
            },
            {
                "name": "专家A",
                "code": "expert_a",
                "color": "#8B5CF6",
                "description": "领域专家，提供专业见解",
                "order": 2,
                "is_host": False,
            },
            {
                "name": "专家B",
                "code": "expert_b",
                "color": "#8B5CF6",
                "description": "领域专家，提供专业见解",
                "order": 3,
                "is_host": False,
            },
            {
                "name": "专家C",
                "code": "expert_c",
                "color": "#8B5CF6",
                "description": "领域专家，提供专业见解",
                "order": 4,
                "is_host": False,
            },
        ],
    },
    "decision_making": {
        "name": "决策制定",
        "roles": [
            {
                "name": "决策主持人",
                "code": "decision_host",
                "color": "#3B82F6",
                "description": "负责引导决策过程，确保各方意见被听取",
                "order": 1,
                "is_host": True,
            },
            {
                "name": "支持方",
                "code": "proponent",
                "color": "#10B981",
                "description": "提出支持观点和论据",
                "order": 2,
                "is_host": False,
            },
            {
                "name": "反对方",
                "code": "opponent",
                "color": "#EF4444",
                "description": "提出反对观点和风险",
                "order": 3,
                "is_host": False,
            },
            {
                "name": "中立评估者",
                "code": "evaluator",
                "color": "#6B7280",
                "description": "客观评估双方论点",
                "order": 4,
                "is_host": False,
            },
        ],
    },
    "problem_solving": {
        "name": "问题解决",
        "roles": [
            {
                "name": "协调人",
                "code": "coordinator",
                "color": "#3B82F6",
                "description": "负责引导问题分析和解决方案制定",
                "order": 1,
                "is_host": True,
            },
            {
                "name": "问题分析者",
                "code": "analyst",
                "color": "#F59E0B",
                "description": "深入分析问题根因",
                "order": 2,
                "is_host": False,
            },
            {
                "name": "方案提出者",
                "code": "solution_provider",
                "color": "#10B981",
                "description": "提出可行解决方案",
                "order": 3,
                "is_host": False,
            },
            {
                "name": "实施顾问",
                "code": "implementer",
                "color": "#8B5CF6",
                "description": "评估方案可行性并提供实施建议",
                "order": 4,
                "is_host": False,
            },
        ],
    },
    "review": {
        "name": "评审",
        "roles": [
            {
                "name": "评审主持人",
                "code": "review_host",
                "color": "#3B82F6",
                "description": "负责引导评审流程，确保评审全面",
                "order": 1,
                "is_host": True,
            },
            {
                "name": "评审专家A",
                "code": "reviewer_a",
                "color": "#8B5CF6",
                "description": "从专业角度进行评审",
                "order": 2,
                "is_host": False,
            },
            {
                "name": "评审专家B",
                "code": "reviewer_b",
                "color": "#8B5CF6",
                "description": "从专业角度进行评审",
                "order": 3,
                "is_host": False,
            },
            {
                "name": "记录员",
                "code": "recorder",
                "color": "#6B7280",
                "description": "记录评审要点和决议",
                "order": 4,
                "is_host": False,
            },
        ],
    },
}


@router.get("")
async def list_role_configs(db: AsyncSession = Depends(get_db)):
    """List all meeting type role configurations."""
    result = await db.execute(select(MeetingTypeRoleConfig))
    configs = result.scalars().all()

    # Convert to dict for easy access
    config_dict = {config.meeting_type: config for config in configs}

    # Build response with all meeting types
    response = []
    for mt in MeetingType:
        if mt in config_dict:
            response.append({
                "meeting_type": mt.value,
                "roles": config_dict[mt].roles,
                "is_active": config_dict[mt].is_active,
            })
        else:
            # Return default config
            default = DEFAULT_ROLE_CONFIGS.get(mt.value, {"roles": []})
            response.append({
                "meeting_type": mt.value,
                "roles": default.get("roles", []),
                "is_active": True,
            })

    return {"items": response}


@router.get("/{meeting_type}")
async def get_role_config(meeting_type: str, db: AsyncSession = Depends(get_db)):
    """Get role configuration for a specific meeting type."""
    try:
        mt = MeetingType(meeting_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid meeting type")

    result = await db.execute(
        select(MeetingTypeRoleConfig).where(MeetingTypeRoleConfig.meeting_type == mt)
    )
    config = result.scalar_one_or_none()

    if config:
        return {
            "meeting_type": meeting_type,
            "roles": config.roles,
            "is_active": config.is_active,
        }
    else:
        # Return default config
        default = DEFAULT_ROLE_CONFIGS.get(meeting_type, {"roles": []})
        return {
            "meeting_type": meeting_type,
            "roles": default.get("roles", []),
            "is_active": True,
        }


@router.put("/{meeting_type}")
async def update_role_config(
    meeting_type: str,
    data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Update role configuration for a specific meeting type."""
    try:
        mt = MeetingType(meeting_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid meeting type")

    roles = data.get("roles", [])
    if not isinstance(roles, list):
        raise HTTPException(status_code=400, detail="Roles must be a list")

    # Validate roles
    for i, role in enumerate(roles):
        if not isinstance(role, dict):
            raise HTTPException(status_code=400, detail=f"Role at index {i} must be an object")
        if "name" not in role:
            raise HTTPException(status_code=400, detail=f"Role at index {i} must have a name")
        # Ensure order is set
        role["order"] = i + 1

    result = await db.execute(
        select(MeetingTypeRoleConfig).where(MeetingTypeRoleConfig.meeting_type == mt)
    )
    config = result.scalar_one_or_none()

    if config:
        config.roles = roles
        config.is_active = data.get("is_active", True)
    else:
        config = MeetingTypeRoleConfig(
            meeting_type=mt,
            roles=roles,
            is_active=data.get("is_active", True),
        )
        db.add(config)

    await db.commit()
    await db.refresh(config)

    return {
        "meeting_type": meeting_type,
        "roles": config.roles,
        "is_active": config.is_active,
    }


@router.post("/init-defaults")
async def init_default_configs(db: AsyncSession = Depends(get_db)):
    """Initialize default role configurations for all meeting types."""
    created = []
    for mt in MeetingType:
        result = await db.execute(
            select(MeetingTypeRoleConfig).where(MeetingTypeRoleConfig.meeting_type == mt)
        )
        config = result.scalar_one_or_none()

        if not config:
            default = DEFAULT_ROLE_CONFIGS.get(mt.value, {"roles": []})
            config = MeetingTypeRoleConfig(
                meeting_type=mt,
                roles=default.get("roles", []),
                is_active=True,
            )
            db.add(config)
            created.append(mt.value)

    await db.commit()
    return {"success": True, "created": created}


@router.post("/{meeting_type}/reset")
async def reset_role_config(meeting_type: str, db: AsyncSession = Depends(get_db)):
    """Reset role configuration to default for a specific meeting type."""
    try:
        mt = MeetingType(meeting_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid meeting type")

    default = DEFAULT_ROLE_CONFIGS.get(meeting_type, {"roles": []})

    result = await db.execute(
        select(MeetingTypeRoleConfig).where(MeetingTypeRoleConfig.meeting_type == mt)
    )
    config = result.scalar_one_or_none()

    if config:
        config.roles = default.get("roles", [])
    else:
        config = MeetingTypeRoleConfig(
            meeting_type=mt,
            roles=default.get("roles", []),
            is_active=True,
        )
        db.add(config)

    await db.commit()
    await db.refresh(config)

    return {
        "meeting_type": meeting_type,
        "roles": config.roles,
        "is_active": config.is_active,
    }