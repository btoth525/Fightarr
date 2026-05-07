"""Health and system status endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException

from app import __version__

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": __version__}


@router.get("/system/status")
async def system_status() -> dict:
    return {
        "appName": "Fightarr",
        "version": __version__,
        "isDebug": False,
        "branch": "main",
    }


@router.get("/system/tasks")
async def system_tasks() -> list[dict]:
    """Return scheduled job info (name, next run time)."""
    from app.core.scheduler import get_scheduler

    scheduler = get_scheduler()
    if scheduler is None:
        return []

    jobs = []
    for job in scheduler.get_jobs():
        next_run = job.next_run_time
        jobs.append(
            {
                "id": job.id,
                "name": job.name,
                "next_run_time": next_run.isoformat() if next_run else None,
            }
        )
    return jobs


@router.post("/system/tasks/{job_id}/run-now")
async def run_task_now(job_id: str) -> dict:
    """Trigger a scheduled job to run immediately."""
    from app.core.scheduler import get_scheduler

    scheduler = get_scheduler()
    if scheduler is None:
        raise HTTPException(status_code=500, detail="Scheduler not running")

    job = scheduler.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    scheduler.modify_job(job_id, next_run_time=datetime.now(tz=UTC))
    return {"status": "triggered", "job_id": job_id}


@router.get("/system/health")
async def system_health() -> dict:
    """Return the latest indexer + download client health status.

    Cached from the most recent health_check task run. Use POST .../run-now on
    the 'health_check' task to refresh immediately.
    """
    from app.services.maintenance import get_last_health

    return get_last_health()


@router.get("/system/logs")
async def system_logs(limit: int = 500, level: str | None = None) -> list[dict]:
    """Return the most recent in-memory log lines.

    Buffer holds up to 2000 entries (INFO and above). Pass level=WARNING/ERROR
    to filter. Designed for the System → Logs UI panel.
    """
    from app.core.log_buffer import get_logs

    return get_logs(limit=limit, level=level)
