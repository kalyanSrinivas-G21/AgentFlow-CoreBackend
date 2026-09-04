# backend/app/monitoring/sampler.py
import asyncio
import logging
import psutil
from sqlalchemy import select, func
from app.db import async_session_maker
from app.monitoring.models import ResourceMetric
from app.tasks.models import Task
from app.events.publisher import publish
from app.events.envelope import EventEnvelope
from redis.asyncio import Redis

logger = logging.getLogger(__name__)

HAS_GPU = False
try:
    import pynvml
    pynvml.nvmlInit()
    HAS_GPU = True
except Exception as e:
    logger.info(f"NVIDIA GPU not detected or NVML failed to initialize: {e}")

async def sample_resources(redis_url: str):
    """Background task to sample hardware metrics every 5 seconds."""
    logger.info("Starting hardware resource sampler...")
    redis = Redis.from_url(redis_url, decode_responses=True)
    
    # Initialize CPU metric to avoid 0.0 on first read
    psutil.cpu_percent(interval=None)
    
    while True:
        try:
            # 1. Gather hardware metrics
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            
            gpu_percent = None
            if HAS_GPU:
                try:
                    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                    util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    gpu_percent = float(util.gpu)
                except Exception as e:
                    logger.warning(f"Failed to read GPU metrics: {e}")

            # 2. Open standalone session for DB interaction
            async with async_session_maker() as session:
                # Get active task count
                result = await session.execute(select(func.count()).where(Task.status == 'RUNNING'))
                active_tasks = result.scalar() or 0
                
                # Save to database
                metric = ResourceMetric(
                    cpu_percent=cpu,
                    memory_percent=ram,
                    gpu_percent=gpu_percent,
                    active_tasks=active_tasks
                )
                session.add(metric)
                await session.commit()
                await session.refresh(metric)
                
                # 3. Broadcast to Event Bus
                evt = EventEnvelope(
                    event_type="resource.metric.sampled",
                    source="resource_sampler",
                    correlation_id=metric.id,  # <-- CRITICAL FIX: Added required correlation_id
                    payload={
                        "cpu_percent": cpu,
                        "memory_percent": ram,
                        "gpu_percent": gpu_percent,
                        "active_tasks": active_tasks,
                        "recorded_at": metric.recorded_at.isoformat() if metric.recorded_at else None
                    }
                )
                await publish(session, redis, evt)
                
        except asyncio.CancelledError:
            logger.info("Resource sampler task cancelled cleanly.")
            break
        except Exception as e:
            # Fault tolerance: log and continue to next tick
            logger.error(f"Unexpected error in resource sampling loop: {e}")
            
        await asyncio.sleep(5)