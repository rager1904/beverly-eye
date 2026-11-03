"""Colab scheduler: only enqueue tasks actually implemented in this checkout."""
from src.backend.core.queue.celery_app import celery_app

celery_app.conf.beat_schedule = {
    key: value for key, value in celery_app.conf.beat_schedule.items()
    if value['task'] in celery_app.tasks
}
