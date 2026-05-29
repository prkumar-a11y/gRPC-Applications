"""In-memory state store for jobs and logs"""
import asyncio
from typing import Dict, List, Set, Callable, Awaitable, Optional
from collections import defaultdict
import logging

from .models import Job, JobState, LogEntry

logger = logging.getLogger(__name__)


class StateStore:
    """Thread-safe in-memory store for jobs, logs, and subscriptions"""
    
    def __init__(self):
        self.jobs: Dict[str, Job] = {}
        self.logs: Dict[str, List[LogEntry]] = defaultdict(list)
        
        # Subscribers for job updates (job_id -> set of callback functions)
        self.job_subscribers: Dict[str, Set[Callable[[Job], Awaitable[None]]]] = defaultdict(set)
        
        # Session subscribers for interactive sessions (job_id -> set of queues)
        self.session_subscribers: Dict[str, Set[asyncio.Queue]] = defaultdict(set)
        
        self._lock = asyncio.Lock()
    
    async def create_job(self, job: Job) -> Job:
        """Create a new job"""
        async with self._lock:
            self.jobs[job.job_id] = job
            logger.info(f"Created job {job.job_id}: {job.name}")
            return job
    
    async def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID"""
        return self.jobs.get(job_id)
    
    async def update_job(self, job_id: str, state: JobState, message: str = "", progress: int = None):
        """Update job state and notify subscribers"""
        async with self._lock:
            job = self.jobs.get(job_id)
            if not job:
                return None
            
            job.update_state(state, message)
            if progress is not None:
                job.progress = progress
            
            logger.info(f"Job {job_id} updated: {state} - {message}")
            
            # Notify all subscribers
            await self._notify_job_subscribers(job)
            
            return job
    
    async def add_log(self, log_entry: LogEntry):
        """Add a log entry"""
        async with self._lock:
            self.logs[log_entry.job_id].append(log_entry)
    
    async def get_logs(self, job_id: str) -> List[LogEntry]:
        """Get all logs for a job"""
        return self.logs.get(job_id, [])
    
    async def subscribe_to_job(self, job_id: str, callback: Callable[[Job], Awaitable[None]]):
        """Subscribe to job updates"""
        async with self._lock:
            self.job_subscribers[job_id].add(callback)
            logger.info(f"New subscriber for job {job_id}, total: {len(self.job_subscribers[job_id])}")
    
    async def unsubscribe_from_job(self, job_id: str, callback: Callable[[Job], Awaitable[None]]):
        """Unsubscribe from job updates"""
        async with self._lock:
            self.job_subscribers[job_id].discard(callback)
            logger.info(f"Unsubscribed from job {job_id}, remaining: {len(self.job_subscribers[job_id])}")
    
    async def subscribe_to_session(self, job_id: str, queue: asyncio.Queue):
        """Subscribe to session events"""
        async with self._lock:
            self.session_subscribers[job_id].add(queue)
            logger.info(f"New session subscriber for job {job_id}")
    
    async def unsubscribe_from_session(self, job_id: str, queue: asyncio.Queue):
        """Unsubscribe from session events"""
        async with self._lock:
            self.session_subscribers[job_id].discard(queue)
            logger.info(f"Session unsubscribed from job {job_id}")
    
    async def _notify_job_subscribers(self, job: Job):
        """Notify all subscribers of a job update"""
        subscribers = list(self.job_subscribers.get(job.job_id, []))
        for callback in subscribers:
            try:
                await callback(job)
            except Exception as e:
                logger.error(f"Error notifying subscriber: {e}")
    
    async def notify_session_subscribers(self, job_id: str, event_type: str, payload: str):
        """Notify all session subscribers"""
        import time
        subscribers = list(self.session_subscribers.get(job_id, []))
        for queue in subscribers:
            try:
                await queue.put({
                    'job_id': job_id,
                    'event_type': event_type,
                    'payload': payload,
                    'timestamp_ms': int(time.time() * 1000)
                })
            except Exception as e:
                logger.error(f"Error notifying session subscriber: {e}")
    
    def list_all_jobs(self) -> List[Job]:
        """List all jobs"""
        return list(self.jobs.values())
