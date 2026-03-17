"""
Instance Management API Routes
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.instance_manager import InstanceService
from app.schemas import (
    InstanceCreate,
    InstanceUpdate,
    InstanceResponse,
    InstanceList,
    InstanceHealth,
)

router = APIRouter(prefix="/instances", tags=["instances"])


async def get_instance_service(db: AsyncSession = Depends(get_db)) -> InstanceService:
    """Dependency to get instance service."""
    return InstanceService(db)


@router.get("", response_model=InstanceList)
async def list_instances(
    service: InstanceService = Depends(get_instance_service)
) -> InstanceList:
    """List all OpenClaw instances."""
    instances = await service.list_instances()
    return InstanceList(
        items=[service.to_response(i) for i in instances],
        total=len(instances)
    )


@router.post("", response_model=InstanceResponse, status_code=status.HTTP_201_CREATED)
async def create_instance(
    data: InstanceCreate,
    service: InstanceService = Depends(get_instance_service)
) -> InstanceResponse:
    """Create a new OpenClaw instance."""
    instance = await service.create_instance(data)
    return service.to_response(instance)


@router.get("/{instance_id}", response_model=InstanceResponse)
async def get_instance(
    instance_id: str,
    service: InstanceService = Depends(get_instance_service)
) -> InstanceResponse:
    """Get instance details."""
    instance = await service.get_instance(instance_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instance not found"
        )
    return service.to_response(instance)


@router.patch("/{instance_id}", response_model=InstanceResponse)
async def update_instance(
    instance_id: str,
    data: InstanceUpdate,
    service: InstanceService = Depends(get_instance_service)
) -> InstanceResponse:
    """Update an instance."""
    instance = await service.update_instance(instance_id, data)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instance not found"
        )
    return service.to_response(instance)


@router.delete("/{instance_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_instance(
    instance_id: str,
    service: InstanceService = Depends(get_instance_service)
) -> None:
    """Delete an instance."""
    success = await service.delete_instance(instance_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instance not found"
        )


@router.post("/{instance_id}/connect")
async def connect_instance(
    instance_id: str,
    service: InstanceService = Depends(get_instance_service)
) -> dict:
    """Connect to an instance."""
    instance = await service.get_instance(instance_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instance not found"
        )

    connected = await service.connect_instance(instance_id)
    return {
        "success": connected,
        "status": instance.status.value,
        "message": instance.status_message
    }


@router.post("/{instance_id}/disconnect")
async def disconnect_instance(
    instance_id: str,
    service: InstanceService = Depends(get_instance_service)
) -> dict:
    """Disconnect from an instance."""
    instance = await service.get_instance(instance_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instance not found"
        )

    await service.disconnect_instance(instance_id)
    return {
        "success": True,
        "status": "disconnected"
    }


@router.get("/{instance_id}/health")
async def get_instance_health(
    instance_id: str,
    service: InstanceService = Depends(get_instance_service)
) -> InstanceHealth:
    """Get instance health status."""
    instance = await service.get_instance(instance_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instance not found"
        )

    return await service.get_instance_health(instance_id)
