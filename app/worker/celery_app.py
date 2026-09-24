"""
Celery Application Factory
===========================
Initialises the Celery instance used by both the API (to dispatch tasks)
and the worker process (to execute them).
"""

from celery import Celery
from app.core.config import REDIS_URL

celery_app = Celery(
    "ksiti_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

import os
is_eager = not bool(REDIS_URL)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,  # Prevent memory leaks from CV/ML models
    task_always_eager=is_eager,     # RUN SYNCHRONOUSLY LOCALLY IF NO REDIS
    task_eager_propagates=is_eager, # Propagate exceptions in eager mode
)

# Auto-discover tasks module
celery_app.autodiscover_tasks(["app.worker"])
