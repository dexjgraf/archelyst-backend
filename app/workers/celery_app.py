"""
Celery application for background tasks.

Configures Celery for handling asynchronous tasks like data processing,
AI analysis, and other background operations.
"""

import logging
from celery import Celery
from ..core.config import settings

# Setup logging
logger = logging.getLogger(__name__)

# Create Celery app
celery_app = Celery(
    "archelyst_workers",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"]
)

# Configure Celery
celery_app.conf.update(
    # Task routing
    task_routes={
        "app.workers.tasks.data_processing.*": {"queue": "data_processing"},
        "app.workers.tasks.ai_analysis.*": {"queue": "ai_analysis"},
        "app.workers.tasks.notifications.*": {"queue": "notifications"},
    },
    
    # Task serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # Timezone
    timezone="UTC",
    enable_utc=True,
    
    # Task configuration
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
    task_soft_time_limit=240,  # 4 minutes
    worker_prefetch_multiplier=1,
    
    # Result backend settings
    result_expires=3600,  # 1 hour
    
    # Beat schedule for periodic tasks
    beat_schedule={
        "health-check": {
            "task": "app.workers.tasks.system.health_check",
            "schedule": 60.0,  # Every minute
        },
        "data-provider-status-check": {
            "task": "app.workers.tasks.data_processing.check_provider_status",
            "schedule": 300.0,  # Every 5 minutes
        },
        "cleanup-logs": {
            "task": "app.workers.tasks.system.cleanup_old_logs",
            "schedule": 3600.0,  # Every hour
        },
    },
)

# Auto-discover tasks
celery_app.autodiscover_tasks()

@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery functionality."""
    logger.info(f"Request: {self.request!r}")
    return f"Debug task executed successfully"

# Health check task
@celery_app.task
def health_check():
    """Simple health check task."""
    logger.info("Celery health check executed")
    return {"status": "healthy", "timestamp": "now"}

if __name__ == "__main__":
    celery_app.start()