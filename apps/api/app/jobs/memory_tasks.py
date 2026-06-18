from app.jobs.celery_app import celery_app


@celery_app.task(name="memory.summarize_chat")
def summarize_chat_task(chat_id: str) -> dict:
    return {"chat_id": chat_id, "status": "queued_for_summary"}

