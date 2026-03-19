"""
Prompt Template API Router
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import PromptTemplate
from app.schemas import (
    PromptTemplateCreate,
    PromptTemplateUpdate,
    PromptTemplateResponse,
    PromptTemplateList,
)
from app.services.prompt_service import PromptService

router = APIRouter(prefix="/prompt-templates", tags=["prompt-templates"])


async def get_db():
    async with AsyncSessionLocal() as db:
        yield db


@router.get("", response_model=PromptTemplateList)
async def list_templates(db: AsyncSession = Depends(get_db)):
    """List all prompt templates."""
    service = PromptService(db)
    templates = await service.list_templates()
    return PromptTemplateList(items=templates, total=len(templates))


@router.get("/{template_id}", response_model=PromptTemplateResponse)
async def get_template(template_id: str, db: AsyncSession = Depends(get_db)):
    """Get a prompt template by ID."""
    service = PromptService(db)
    template = await service.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.post("", response_model=PromptTemplateResponse)
async def create_template(data: PromptTemplateCreate, db: AsyncSession = Depends(get_db)):
    """Create a custom prompt template."""
    service = PromptService(db)

    # Check if code already exists
    existing = await service.get_template_by_code(data.code)
    if existing:
        raise HTTPException(status_code=400, detail="Template with this code already exists")

    template = await service.create_template(data)
    return template


@router.patch("/{template_id}", response_model=PromptTemplateResponse)
async def update_template(
    template_id: str,
    data: PromptTemplateUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a prompt template."""
    service = PromptService(db)
    template = await service.update_template(template_id, data)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.delete("/{template_id}")
async def delete_template(template_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a prompt template (system templates cannot be deleted)."""
    service = PromptService(db)
    success = await service.delete_template(template_id)
    if not success:
        # Could be not found or system template
        template = await service.get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        if template.is_system:
            raise HTTPException(status_code=400, detail="System templates cannot be deleted")
    return {"success": True}


@router.post("/{template_id}/set-default", response_model=PromptTemplateResponse)
async def set_default_template(template_id: str, db: AsyncSession = Depends(get_db)):
    """Set a template as the default."""
    service = PromptService(db)
    template = await service.set_default_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.post("/init-default")
async def init_default_template(db: AsyncSession = Depends(get_db)):
    """Initialize default template if not exists."""
    service = PromptService(db)
    template = await service.ensure_default_template_exists()
    return {"success": True, "template_id": template.id}