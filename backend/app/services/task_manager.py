"""
Task Manager Service

Provides CRUD operations and lifecycle management for tasks.
"""

import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Task, TaskStatus, TaskPriority,
    SubTask, SubTaskStatus,
    TaskProgress, TaskProgressEventType,
)
from app.utils.time_utils import beijing_now_naive


class TaskService:
    """Service for managing tasks."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_task(
        self,
        title: str,
        description: Optional[str] = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        tags: Optional[List[str]] = None,
        extra_data: Optional[dict] = None,
        deadline: Optional[datetime] = None,
    ) -> Task:
        """Create a new task."""
        task = Task(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            status=TaskStatus.DRAFT,
            priority=priority,
            tags=tags or [],
            extra_data=extra_data or {},
            deadline=deadline,
        )
        self.db.add(task)

        # Create progress event
        await self._create_progress_event(
            task_id=task.id,
            event_type=TaskProgressEventType.CREATED,
            message=f"Task '{title}' created",
            progress_percent=0,
        )

        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        result = await self.db.execute(
            select(Task).where(Task.id == task_id)
        )
        return result.scalar_one_or_none()

    async def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None,
        manager_instance_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[List[Task], int]:
        """List tasks with optional filtering."""
        filters = []
        if status:
            filters.append(Task.status == status)
        if priority:
            filters.append(Task.priority == priority)
        if manager_instance_id:
            filters.append(Task.manager_instance_id == manager_instance_id)

        query = select(Task)
        if filters:
            query = query.where(and_(*filters))

        # Count total
        count_query = select(Task)
        if filters:
            count_query = count_query.where(and_(*filters))
        count_result = await self.db.execute(count_query)
        total = len(count_result.scalars().all())

        # Get paginated results
        query = query.order_by(Task.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        tasks = list(result.scalars().all())

        return tasks, total

    async def update_task(
        self,
        task_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[TaskPriority] = None,
        tags: Optional[List[str]] = None,
        extra_data: Optional[dict] = None,
        deadline: Optional[datetime] = None,
        status: Optional[TaskStatus] = None,
    ) -> Optional[Task]:
        """Update a task."""
        task = await self.get_task(task_id)
        if not task:
            return None

        if title is not None:
            task.title = title
        if description is not None:
            task.description = description
        if priority is not None:
            task.priority = priority
        if tags is not None:
            task.tags = tags
        if extra_data is not None:
            task.extra_data = extra_data
        if deadline is not None:
            task.deadline = deadline
        if status is not None:
            task.status = status

        task.updated_at = beijing_now_naive()
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def delete_task(self, task_id: str) -> bool:
        """Delete a task and its subtasks."""
        task = await self.get_task(task_id)
        if not task:
            return False

        # Delete subtasks first
        await self.db.execute(
            select(SubTask).where(SubTask.task_id == task_id)
        )
        subtasks_result = await self.db.execute(
            select(SubTask).where(SubTask.task_id == task_id)
        )
        for subtask in subtasks_result.scalars().all():
            await self.db.delete(subtask)

        # Delete progress events
        progress_result = await self.db.execute(
            select(TaskProgress).where(TaskProgress.task_id == task_id)
        )
        for progress in progress_result.scalars().all():
            await self.db.delete(progress)

        await self.db.delete(task)
        await self.db.commit()
        return True

    async def publish_task(self, task_id: str) -> Optional[Task]:
        """Publish a draft task."""
        task = await self.get_task(task_id)
        if not task or task.status != TaskStatus.DRAFT:
            return None

        task.status = TaskStatus.PUBLISHED
        task.updated_at = beijing_now_naive()

        await self._create_progress_event(
            task_id=task_id,
            event_type=TaskProgressEventType.PUBLISHED,
            message=f"Task '{task.title}' published",
            progress_percent=5,
        )

        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def assign_manager(
        self, task_id: str, manager_instance_id: str
    ) -> Optional[Task]:
        """Assign a manager instance to a task."""
        task = await self.get_task(task_id)
        if not task or task.status not in [TaskStatus.PUBLISHED, TaskStatus.ASSIGNED]:
            return None

        task.manager_instance_id = manager_instance_id
        task.status = TaskStatus.ASSIGNED
        task.updated_at = beijing_now_naive()

        await self._create_progress_event(
            task_id=task_id,
            event_type=TaskProgressEventType.ASSIGNED,
            message=f"Manager assigned to task",
            progress_percent=10,
        )

        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def start_analyzing(self, task_id: str) -> Optional[Task]:
        """Start analyzing a task."""
        task = await self.get_task(task_id)
        if not task or task.status != TaskStatus.ASSIGNED:
            return None

        task.status = TaskStatus.ANALYZING
        task.updated_at = beijing_now_naive()

        await self._create_progress_event(
            task_id=task_id,
            event_type=TaskProgressEventType.ANALYZING,
            message="Task analysis started",
            progress_percent=15,
        )

        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def confirm_decomposition(self, task_id: str) -> Optional[Task]:
        """Confirm task decomposition and start execution."""
        task = await self.get_task(task_id)
        if not task or task.status != TaskStatus.ANALYZING:
            return None

        task.status = TaskStatus.DECOMPOSED
        task.updated_at = beijing_now_naive()

        await self._create_progress_event(
            task_id=task_id,
            event_type=TaskProgressEventType.DECOMPOSED,
            message="Task decomposition confirmed",
            progress_percent=20,
        )

        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def start_task(self, task_id: str) -> Optional[Task]:
        """Start task execution."""
        task = await self.get_task(task_id)
        if not task or task.status != TaskStatus.DECOMPOSED:
            return None

        task.status = TaskStatus.IN_PROGRESS
        task.started_at = beijing_now_naive()
        task.updated_at = beijing_now_naive()

        await self._create_progress_event(
            task_id=task_id,
            event_type=TaskProgressEventType.STARTED,
            message="Task execution started",
            progress_percent=25,
        )

        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def complete_task(
        self, task_id: str, result: Optional[str] = None, summary: Optional[str] = None
    ) -> Optional[Task]:
        """Mark task as completed."""
        task = await self.get_task(task_id)
        if not task or task.status != TaskStatus.IN_PROGRESS:
            return None

        task.status = TaskStatus.COMPLETED
        task.completed_at = beijing_now_naive()
        task.updated_at = beijing_now_naive()
        if result:
            task.result = result
        if summary:
            task.summary = summary

        await self._create_progress_event(
            task_id=task_id,
            event_type=TaskProgressEventType.COMPLETED,
            message="Task completed successfully",
            progress_percent=100,
        )

        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def fail_task(
        self, task_id: str, error_message: Optional[str] = None
    ) -> Optional[Task]:
        """Mark task as failed."""
        task = await self.get_task(task_id)
        if not task:
            return None

        task.status = TaskStatus.FAILED
        task.completed_at = beijing_now_naive()
        task.updated_at = beijing_now_naive()

        await self._create_progress_event(
            task_id=task_id,
            event_type=TaskProgressEventType.FAILED,
            message=error_message or "Task failed",
            progress_percent=0,
        )

        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def calculate_progress(self, task_id: str) -> int:
        """Calculate task progress based on subtask completion."""
        result = await self.db.execute(
            select(SubTask).where(SubTask.task_id == task_id)
        )
        subtasks = list(result.scalars().all())

        if not subtasks:
            return 0

        completed = sum(1 for s in subtasks if s.status == SubTaskStatus.COMPLETED)
        return int((completed / len(subtasks)) * 100)

    async def _create_progress_event(
        self,
        task_id: str,
        event_type: TaskProgressEventType,
        message: Optional[str] = None,
        progress_percent: int = 0,
        subtask_id: Optional[str] = None,
    ) -> TaskProgress:
        """Create a progress event for a task."""
        progress = TaskProgress(
            id=str(uuid.uuid4()),
            task_id=task_id,
            subtask_id=subtask_id,
            event_type=event_type,
            message=message,
            progress_percent=progress_percent,
        )
        self.db.add(progress)
        return progress


class SubTaskService:
    """Service for managing subtasks."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_subtask(
        self,
        task_id: str,
        title: str,
        description: Optional[str] = None,
        order: int = 0,
        dependencies: Optional[List[str]] = None,
    ) -> SubTask:
        """Create a new subtask."""
        subtask = SubTask(
            id=str(uuid.uuid4()),
            task_id=task_id,
            title=title,
            description=description,
            status=SubTaskStatus.PENDING,
            order=order,
            dependencies=dependencies or [],
        )
        self.db.add(subtask)

        # Create progress event
        progress = TaskProgress(
            id=str(uuid.uuid4()),
            task_id=task_id,
            subtask_id=subtask.id,
            event_type=TaskProgressEventType.SUBTASK_CREATED,
            message=f"SubTask '{title}' created",
            progress_percent=0,
        )
        self.db.add(progress)

        await self.db.commit()
        await self.db.refresh(subtask)
        return subtask

    async def get_subtask(self, subtask_id: str) -> Optional[SubTask]:
        """Get a subtask by ID."""
        result = await self.db.execute(
            select(SubTask).where(SubTask.id == subtask_id)
        )
        return result.scalar_one_or_none()

    async def list_subtasks(self, task_id: str) -> List[SubTask]:
        """List all subtasks for a task."""
        result = await self.db.execute(
            select(SubTask)
            .where(SubTask.task_id == task_id)
            .order_by(SubTask.order)
        )
        return list(result.scalars().all())

    async def update_subtask(
        self,
        subtask_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[SubTaskStatus] = None,
        executor_instance_id: Optional[str] = None,
        order: Optional[int] = None,
        dependencies: Optional[List[str]] = None,
        result: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Optional[SubTask]:
        """Update a subtask."""
        subtask = await self.get_subtask(subtask_id)
        if not subtask:
            return None

        if title is not None:
            subtask.title = title
        if description is not None:
            subtask.description = description
        if status is not None:
            subtask.status = status
        if executor_instance_id is not None:
            subtask.executor_instance_id = executor_instance_id
        if order is not None:
            subtask.order = order
        if dependencies is not None:
            subtask.dependencies = dependencies
        if result is not None:
            subtask.result = result
        if error_message is not None:
            subtask.error_message = error_message

        subtask.updated_at = beijing_now_naive()
        await self.db.commit()
        await self.db.refresh(subtask)
        return subtask

    async def assign_subtask(
        self, subtask_id: str, executor_instance_id: str
    ) -> Optional[SubTask]:
        """Assign an executor to a subtask."""
        subtask = await self.get_subtask(subtask_id)
        if not subtask:
            return None

        subtask.executor_instance_id = executor_instance_id
        subtask.status = SubTaskStatus.ASSIGNED
        subtask.updated_at = beijing_now_naive()

        # Create progress event
        progress = TaskProgress(
            id=str(uuid.uuid4()),
            task_id=subtask.task_id,
            subtask_id=subtask.id,
            event_type=TaskProgressEventType.SUBTASK_ASSIGNED,
            message=f"SubTask '{subtask.title}' assigned",
            progress_percent=0,
        )
        self.db.add(progress)

        await self.db.commit()
        await self.db.refresh(subtask)
        return subtask

    async def start_subtask(self, subtask_id: str) -> Optional[SubTask]:
        """Start a subtask."""
        subtask = await self.get_subtask(subtask_id)
        if not subtask:
            return None

        subtask.status = SubTaskStatus.IN_PROGRESS
        subtask.updated_at = beijing_now_naive()

        # Create progress event
        progress = TaskProgress(
            id=str(uuid.uuid4()),
            task_id=subtask.task_id,
            subtask_id=subtask.id,
            event_type=TaskProgressEventType.SUBTASK_STARTED,
            message=f"SubTask '{subtask.title}' started",
            progress_percent=0,
        )
        self.db.add(progress)

        await self.db.commit()
        await self.db.refresh(subtask)
        return subtask

    async def complete_subtask(
        self, subtask_id: str, result: Optional[str] = None
    ) -> Optional[SubTask]:
        """Mark subtask as completed."""
        subtask = await self.get_subtask(subtask_id)
        if not subtask:
            return None

        subtask.status = SubTaskStatus.COMPLETED
        subtask.result = result
        subtask.updated_at = beijing_now_naive()

        # Create progress event
        progress = TaskProgress(
            id=str(uuid.uuid4()),
            task_id=subtask.task_id,
            subtask_id=subtask.id,
            event_type=TaskProgressEventType.SUBTASK_COMPLETED,
            message=f"SubTask '{subtask.title}' completed",
            progress_percent=0,
        )
        self.db.add(progress)

        await self.db.commit()
        await self.db.refresh(subtask)
        return subtask

    async def fail_subtask(
        self, subtask_id: str, error_message: str
    ) -> Optional[SubTask]:
        """Mark subtask as failed."""
        subtask = await self.get_subtask(subtask_id)
        if not subtask:
            return None

        subtask.status = SubTaskStatus.FAILED
        subtask.error_message = error_message
        subtask.updated_at = beijing_now_naive()

        # Create progress event
        progress = TaskProgress(
            id=str(uuid.uuid4()),
            task_id=subtask.task_id,
            subtask_id=subtask.id,
            event_type=TaskProgressEventType.SUBTASK_FAILED,
            message=f"SubTask '{subtask.title}' failed: {error_message}",
            progress_percent=0,
        )
        self.db.add(progress)

        await self.db.commit()
        await self.db.refresh(subtask)
        return subtask

    async def delete_subtask(self, subtask_id: str) -> bool:
        """Delete a subtask."""
        subtask = await self.get_subtask(subtask_id)
        if not subtask:
            return False

        await self.db.delete(subtask)
        await self.db.commit()
        return True


class TaskProgressService:
    """Service for task progress."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_progress(
        self, task_id: str, limit: int = 100, offset: int = 0
    ) -> tuple[List[TaskProgress], int]:
        """List progress events for a task."""
        # Count total
        count_result = await self.db.execute(
            select(TaskProgress).where(TaskProgress.task_id == task_id)
        )
        total = len(count_result.scalars().all())

        # Get paginated results
        result = await self.db.execute(
            select(TaskProgress)
            .where(TaskProgress.task_id == task_id)
            .order_by(TaskProgress.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        events = list(result.scalars().all())

        return events, total