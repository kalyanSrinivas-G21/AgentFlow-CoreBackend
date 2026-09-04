# backend/app/monitoring/router.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.monitoring.models import ResourceMetric
from app.security.auth import get_current_actor

# Both endpoints require the Stage 12 authentication dependency
router = APIRouter(tags=["monitoring"], dependencies=[Depends(get_current_actor)])

@router.get("/api/v1/metrics/latest")
async def get_latest_metrics(db: AsyncSession = Depends(get_db)):
    """Returns the most recent resource sampling as JSON for the UI."""
    result = await db.execute(
        select(ResourceMetric).order_by(desc(ResourceMetric.recorded_at)).limit(1)
    )
    metric = result.scalar_one_or_none()
    
    if not metric:
        raise HTTPException(status_code=404, detail="No metrics available yet.")
        
    return {
        "id": str(metric.id),
        "cpu_percent": metric.cpu_percent,
        "memory_percent": metric.memory_percent,
        "gpu_percent": metric.gpu_percent,
        "active_tasks": metric.active_tasks,
        "recorded_at": metric.recorded_at.isoformat() if metric.recorded_at else None
    }

@router.get("/metrics", response_class=PlainTextResponse)
async def get_prometheus_metrics(db: AsyncSession = Depends(get_db)):
    """Exposes the latest metrics in standard Prometheus text-exposition format."""
    result = await db.execute(
        select(ResourceMetric).order_by(desc(ResourceMetric.recorded_at)).limit(1)
    )
    metric = result.scalar_one_or_none()
    
    if not metric:
        return "# No data\n"
        
    lines = [
        "# HELP ai_workbench_cpu_percent CPU usage percentage",
        "# TYPE ai_workbench_cpu_percent gauge",
        f"ai_workbench_cpu_percent {metric.cpu_percent}",
        "# HELP ai_workbench_memory_percent Memory usage percentage",
        "# TYPE ai_workbench_memory_percent gauge",
        f"ai_workbench_memory_percent {metric.memory_percent}",
        "# HELP ai_workbench_active_tasks Number of currently running tasks",
        "# TYPE ai_workbench_active_tasks gauge",
        f"ai_workbench_active_tasks {metric.active_tasks}",
    ]
    
    if metric.gpu_percent is not None:
        lines.extend([
            "# HELP ai_workbench_gpu_percent GPU usage percentage",
            "# TYPE ai_workbench_gpu_percent gauge",
            f"ai_workbench_gpu_percent {metric.gpu_percent}",
        ])
        
    return "\n".join(lines) + "\n"