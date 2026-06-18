"""Celery application wiring with a no-op fallback for local imports."""

from __future__ import annotations

import os
from functools import wraps
from typing import Any, Callable, TypeVar
from dotenv import load_dotenv

load_dotenv()


TaskFunc = TypeVar("TaskFunc", bound=Callable[..., Any])


class LocalCeleryFallback:
    """Expose a Celery-like task decorator when Celery is not installed."""

    def task(self, *decorator_args: Any, **decorator_kwargs: Any) -> Callable[[TaskFunc], TaskFunc]:
        def decorate(func: TaskFunc) -> TaskFunc:
            @wraps(func)
            def delay(*args: Any, **kwargs: Any) -> Any:
                return func(*args, **kwargs)

            setattr(func, "delay", delay)
            return func

        if decorator_args and callable(decorator_args[0]) and not decorator_kwargs:
            return decorate(decorator_args[0])
        return decorate


def create_celery_app() -> Any:
    broker_url = os.getenv("CELERY_BROKER_URL") or os.getenv("REDIS_URL")
    result_backend = os.getenv("CELERY_RESULT_BACKEND") or broker_url

    try:
        from celery import Celery  # type: ignore
    except Exception:
        return LocalCeleryFallback()

    celery = Celery(
        "ai_chat_api",
        broker=broker_url,
        backend=result_backend,
        include=[
            "app.jobs.document_tasks",
            "app.jobs.memory_tasks",
            "app.jobs.retrieval_jobs",
        ],
    )
    celery.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        task_track_started=True,
        worker_prefetch_multiplier=1,
    )
    return celery


celery_app = create_celery_app()
