"""Celery application configuration for distributed document processing.

This module configures the Celery application with:
- Redis as message broker and result backend
- Task routing for different processing types
- Concurrency and prefetch settings for GPU optimization
- Health monitoring and task lifecycle hooks

Usage:
    # Start worker
    celery -A image_preprocessing_detector.workers worker -l info

    # Start worker with GPU concurrency
    celery -A image_preprocessing_detector.workers worker -l info -c 2 --pool=solo

    # Monitor with flower
    celery -A image_preprocessing_detector.workers flower

Phase 4 Integration - Week 17 Sprint 4.3.5
"""

import os
from dataclasses import dataclass, field
from typing import Any

from celery import Celery
from celery.signals import (
    task_failure,
    task_postrun,
    task_prerun,
    worker_ready,
    worker_shutdown,
)
from kombu import Exchange, Queue

from image_preprocessing_detector.utils.log_config import get_logger

logger = get_logger(__name__)


@dataclass
class CeleryConfig:
    """Celery configuration settings.

    Attributes:
        broker_url: Redis connection URL for message broker
        result_backend: Redis connection URL for results
        task_serializer: Serialization format for tasks
        result_serializer: Serialization format for results
        accept_content: Accepted content types
        task_acks_late: Acknowledge after task completion
        worker_prefetch_multiplier: Tasks to prefetch per worker
        task_default_queue: Default queue name
        task_queues: Queue configurations
        task_routes: Task routing rules
    """

    broker_url: str = field(
        default_factory=lambda: os.getenv(
            "CELERY_BROKER_URL", "redis://localhost:6379/0"
        )
    )
    result_backend: str = field(
        default_factory=lambda: os.getenv(
            "CELERY_RESULT_BACKEND", "redis://localhost:6379/1"
        )
    )
    task_serializer: str = "json"
    result_serializer: str = "json"
    accept_content: list[str] = field(default_factory=lambda: ["json"])
    task_acks_late: bool = True
    worker_prefetch_multiplier: int = 1  # Minimize prefetch for GPU tasks
    task_default_queue: str = "default"
    task_time_limit: int = 300  # 5 minute hard limit
    task_soft_time_limit: int = 240  # 4 minute soft limit
    result_expires: int = 3600  # Results expire after 1 hour

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary for Celery."""
        return {
            "broker_url": self.broker_url,
            "result_backend": self.result_backend,
            "task_serializer": self.task_serializer,
            "result_serializer": self.result_serializer,
            "accept_content": self.accept_content,
            "task_acks_late": self.task_acks_late,
            "worker_prefetch_multiplier": self.worker_prefetch_multiplier,
            "task_default_queue": self.task_default_queue,
            "task_time_limit": self.task_time_limit,
            "task_soft_time_limit": self.task_soft_time_limit,
            "result_expires": self.result_expires,
            "task_queues": self._get_queues(),
            "task_routes": self._get_routes(),
        }

    def _get_queues(self) -> tuple[Queue, ...]:
        """Define Celery queues."""
        default_exchange = Exchange("default", type="direct")
        gpu_exchange = Exchange("gpu", type="direct")
        batch_exchange = Exchange("batch", type="direct")

        return (
            Queue("default", default_exchange, routing_key="default"),
            Queue(
                "gpu",
                gpu_exchange,
                routing_key="gpu",
                queue_arguments={"x-max-priority": 10},
            ),
            Queue("batch", batch_exchange, routing_key="batch"),
        )

    def _get_routes(self) -> dict[str, dict[str, str]]:
        """Define task routing rules."""
        return {
            "image_preprocessing_detector.workers.tasks.run_iqa_analysis": {
                "queue": "gpu",
                "routing_key": "gpu",
            },
            "image_preprocessing_detector.workers.tasks.process_single_document": {
                "queue": "default",
                "routing_key": "default",
            },
            "image_preprocessing_detector.workers.tasks.process_batch_documents": {
                "queue": "batch",
                "routing_key": "batch",
            },
        }


# Create Celery application
celery_app = Celery("image_preprocessing_detector")

# Load configuration
config = CeleryConfig()
celery_app.config_from_object(config.to_dict())


# Task lifecycle hooks
@celery_app.task(bind=True, name="celery.ping")
def ping(_self: Any) -> str:
    """Health check task."""
    return "pong"


@worker_ready.connect
def on_worker_ready(**kwargs: Any) -> None:
    """Handle worker startup."""
    logger.info("Celery worker ready", **kwargs)


@worker_shutdown.connect
def on_worker_shutdown(**kwargs: Any) -> None:
    """Handle worker shutdown."""
    logger.info("Celery worker shutting down", **kwargs)


@task_prerun.connect
def on_task_prerun(task_id: str, task: Any, **_kwargs: Any) -> None:
    """Handle task start."""
    logger.debug("Task starting", task_id=task_id, task_name=task.name)


@task_postrun.connect
def on_task_postrun(
    task_id: str, task: Any, _retval: Any, state: str, **_kwargs: Any
) -> None:
    """Handle task completion."""
    logger.debug("Task completed", task_id=task_id, task_name=task.name, state=state)


@task_failure.connect
def on_task_failure(task_id: str, exception: Exception, **_kwargs: Any) -> None:
    """Handle task failure."""
    logger.exception(
        "Task failed",
        task_id=task_id,
        error=str(exception),
    )


def get_celery_app() -> Celery:
    """Get the configured Celery application."""
    return celery_app


def check_broker_connection() -> bool:
    """Check if broker connection is available."""
    try:
        with celery_app.connection() as conn:
            conn.ensure_connection(max_retries=1)
    except Exception as e:
        logger.warning("Broker connection failed", error=str(e))
        return False
    else:
        return True


def get_worker_stats() -> dict[str, Any]:
    """Get statistics from active workers.

    Returns:
        Dictionary with worker statistics
    """
    try:
        inspect = celery_app.control.inspect()
        stats = inspect.stats() or {}
        active = inspect.active() or {}
        reserved = inspect.reserved() or {}

        return {
            "workers": list(stats.keys()),
            "worker_count": len(stats),
            "active_tasks": sum(len(tasks) for tasks in active.values()),
            "reserved_tasks": sum(len(tasks) for tasks in reserved.values()),
            "stats": stats,
        }
    except Exception as e:
        logger.warning("Failed to get worker stats", error=str(e))
        return {
            "workers": [],
            "worker_count": 0,
            "active_tasks": 0,
            "reserved_tasks": 0,
            "error": str(e),
        }


def get_queue_lengths() -> dict[str, int | str]:
    """Get message counts for each queue.

    Returns:
        Dictionary mapping queue names to message counts or error message
    """
    try:
        with celery_app.connection() as conn:
            lengths: dict[str, int | str] = {}
            for queue in ["default", "gpu", "batch"]:
                try:
                    queue_obj = conn.channel().queue_declare(queue=queue, passive=True)
                    lengths[queue] = queue_obj.message_count
                except Exception:
                    lengths[queue] = -1  # Queue doesn't exist
            return lengths
    except Exception as e:
        logger.warning("Failed to get queue lengths", error=str(e))
        return {"error": str(e)}
