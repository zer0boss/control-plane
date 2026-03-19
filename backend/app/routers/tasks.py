"""
Task Management API Router
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import TaskStatus, TaskPriority, SubTaskStatus
from app.schemas import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskList,
    TaskAssignManager,
    TaskAnalyze,
    TaskConfirm,
    SubTaskCreate,
    SubTaskUpdate,
    SubTaskResponse,
    SubTaskList,
    TaskProgressResponse,
    TaskProgressList,
    TaskStatus as TaskStatusSchema,
    TaskPriority as TaskPrioritySchema,
    SubTaskStatus as SubTaskStatusSchema,
)
from app.services.task_manager import TaskService, SubTaskService, TaskProgressService

router = APIRouter(prefix="/tasks", tags=["tasks"])


async def get_db():
    async with AsyncSessionLocal() as db:
        yield db


# ============================================================================
# Task CRUD
# ============================================================================

@router.post("", response_model=TaskResponse)
async def create_task(
    data: TaskCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new task."""
    service = TaskService(db)
    task = await service.create_task(
        title=data.title,
        description=data.description,
        priority=TaskPriority(data.priority.value),
        tags=data.tags,
        extra_data=data.extra_data,
        deadline=data.deadline,
    )
    return task


@router.get("", response_model=TaskList)
async def list_tasks(
    status: Optional[TaskStatusSchema] = Query(default=None),
    priority: Optional[TaskPrioritySchema] = Query(default=None),
    manager_instance_id: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List all tasks with optional filtering."""
    service = TaskService(db)
    status_filter = TaskStatus(status.value) if status else None
    priority_filter = TaskPriority(priority.value) if priority else None
    tasks, total = await service.list_tasks(
        status=status_filter,
        priority=priority_filter,
        manager_instance_id=manager_instance_id,
        limit=limit,
        offset=offset,
    )
    return TaskList(items=tasks, total=total)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a task by ID."""
    service = TaskService(db)
    task = await service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    data: TaskUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a task."""
    service = TaskService(db)
    status = TaskStatus(data.status.value) if data.status else None
    priority = TaskPriority(data.priority.value) if data.priority else None
    task = await service.update_task(
        task_id=task_id,
        title=data.title,
        description=data.description,
        priority=priority,
        tags=data.tags,
        extra_data=data.extra_data,
        deadline=data.deadline,
        status=status,
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a task."""
    service = TaskService(db)
    success = await service.delete_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"success": True}


# ============================================================================
# Task Lifecycle
# ============================================================================

@router.post("/{task_id}/publish", response_model=TaskResponse)
async def publish_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Publish a draft task."""
    service = TaskService(db)
    task = await service.publish_task(task_id)
    if not task:
        raise HTTPException(
            status_code=400,
            detail="Task not found or not in draft status"
        )
    return task


@router.post("/{task_id}/assign-manager", response_model=TaskResponse)
async def assign_manager(
    task_id: str,
    data: TaskAssignManager,
    db: AsyncSession = Depends(get_db),
):
    """Assign a manager instance to a task."""
    service = TaskService(db)
    task = await service.assign_manager(task_id, data.manager_instance_id)
    if not task:
        raise HTTPException(
            status_code=400,
            detail="Task not found or not in published/assigned status"
        )
    return task


@router.post("/{task_id}/analyze", response_model=TaskResponse)
async def analyze_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Start analyzing a task."""
    service = TaskService(db)
    task = await service.start_analyzing(task_id)
    if not task:
        raise HTTPException(
            status_code=400,
            detail="Task not found or not in assigned status"
        )
    return task


@router.post("/{task_id}/confirm", response_model=TaskResponse)
async def confirm_decomposition(
    task_id: str,
    data: TaskConfirm,
    db: AsyncSession = Depends(get_db),
):
    """Confirm task decomposition."""
    service = TaskService(db)
    task = await service.confirm_decomposition(task_id)
    if not task:
        raise HTTPException(
            status_code=400,
            detail="Task not found or not in analyzing status"
        )
    return task


@router.post("/{task_id}/start", response_model=TaskResponse)
async def start_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Start task execution."""
    service = TaskService(db)
    task = await service.start_task(task_id)
    if not task:
        raise HTTPException(
            status_code=400,
            detail="Task not found or not in decomposed status"
        )
    return task


@router.post("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(
    task_id: str,
    result: Optional[str] = Query(default=None),
    summary: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Mark task as completed."""
    service = TaskService(db)
    task = await service.complete_task(task_id, result=result, summary=summary)
    if not task:
        raise HTTPException(
            status_code=400,
            detail="Task not found or not in progress"
        )
    return task


@router.post("/{task_id}/fail", response_model=TaskResponse)
async def fail_task(
    task_id: str,
    error_message: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Mark task as failed."""
    service = TaskService(db)
    task = await service.fail_task(task_id, error_message=error_message)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


# ============================================================================
# SubTasks
# ============================================================================

@router.get("/{task_id}/subtasks", response_model=SubTaskList)
async def list_subtasks(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List all subtasks for a task."""
    task_service = TaskService(db)
    task = await task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    subtask_service = SubTaskService(db)
    subtasks = await subtask_service.list_subtasks(task_id)
    return SubTaskList(items=subtasks, total=len(subtasks))


@router.post("/{task_id}/subtasks", response_model=SubTaskResponse)
async def create_subtask(
    task_id: str,
    data: SubTaskCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new subtask for a task."""
    task_service = TaskService(db)
    task = await task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    subtask_service = SubTaskService(db)
    subtask = await subtask_service.create_subtask(
        task_id=task_id,
        title=data.title,
        description=data.description,
        order=data.order,
        dependencies=data.dependencies,
    )
    return subtask


@router.get("/subtasks/{subtask_id}", response_model=SubTaskResponse)
async def get_subtask(
    subtask_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a subtask by ID."""
    service = SubTaskService(db)
    subtask = await service.get_subtask(subtask_id)
    if not subtask:
        raise HTTPException(status_code=404, detail="SubTask not found")
    return subtask


@router.patch("/subtasks/{subtask_id}", response_model=SubTaskResponse)
async def update_subtask(
    subtask_id: str,
    data: SubTaskUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a subtask."""
    service = SubTaskService(db)
    status = SubTaskStatus(data.status.value) if data.status else None
    subtask = await service.update_subtask(
        subtask_id=subtask_id,
        title=data.title,
        description=data.description,
        status=status,
        executor_instance_id=data.executor_instance_id,
        order=data.order,
        dependencies=data.dependencies,
        result=data.result,
        error_message=data.error_message,
    )
    if not subtask:
        raise HTTPException(status_code=404, detail="SubTask not found")
    return subtask


@router.delete("/subtasks/{subtask_id}")
async def delete_subtask(
    subtask_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a subtask."""
    service = SubTaskService(db)
    success = await service.delete_subtask(subtask_id)
    if not success:
        raise HTTPException(status_code=404, detail="SubTask not found")
    return {"success": True}


@router.post("/subtasks/{subtask_id}/assign", response_model=SubTaskResponse)
async def assign_subtask(
    subtask_id: str,
    executor_instance_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Assign an executor to a subtask."""
    service = SubTaskService(db)
    subtask = await service.assign_subtask(subtask_id, executor_instance_id)
    if not subtask:
        raise HTTPException(status_code=404, detail="SubTask not found")
    return subtask


@router.post("/subtasks/{subtask_id}/start", response_model=SubTaskResponse)
async def start_subtask(
    subtask_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Start a subtask."""
    service = SubTaskService(db)
    subtask = await service.start_subtask(subtask_id)
    if not subtask:
        raise HTTPException(status_code=404, detail="SubTask not found")
    return subtask


@router.post("/subtasks/{subtask_id}/complete", response_model=SubTaskResponse)
async def complete_subtask(
    subtask_id: str,
    result: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Mark subtask as completed."""
    service = SubTaskService(db)
    subtask = await service.complete_subtask(subtask_id, result=result)
    if not subtask:
        raise HTTPException(status_code=404, detail="SubTask not found")
    return subtask


@router.post("/subtasks/{subtask_id}/fail", response_model=SubTaskResponse)
async def fail_subtask(
    subtask_id: str,
    error_message: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Mark subtask as failed."""
    service = SubTaskService(db)
    subtask = await service.fail_subtask(subtask_id, error_message=error_message)
    if not subtask:
        raise HTTPException(status_code=404, detail="SubTask not found")
    return subtask


# ============================================================================
# Task Progress
# ============================================================================

@router.get("/{task_id}/progress", response_model=TaskProgressList)
async def list_progress(
    task_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List progress events for a task."""
    task_service = TaskService(db)
    task = await task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    progress_service = TaskProgressService(db)
    events, total = await progress_service.list_progress(
        task_id=task_id,
        limit=limit,
        offset=offset,
    )
    return TaskProgressList(items=events, total=total)


@router.get("/{task_id}/progress/percent")
async def get_progress_percent(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get task progress percentage."""
    service = TaskService(db)
    task = await service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    percent = await service.calculate_progress(task_id)
    return {"task_id": task_id, "progress_percent": percent}