"""Data models for job orchestrator"""
from dataclasses import dataclass, field
from typing import Dict, List
from enum import Enum
import time


class JobState(str, Enum):
    """Job execution states"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class Job:
    """Job data model"""
    job_id: str
    name: str
    params: Dict[str, str]
    state: JobState = JobState.PENDING
    message: str = ""
    created_at: int = field(default_factory=lambda: int(time.time() * 1000))
    updated_at: int = field(default_factory=lambda: int(time.time() * 1000))
    progress: int = 0
    log_level: str = "INFO"
    
    def update_state(self, state: JobState, message: str = ""):
        """Update job state and timestamp"""
        self.state = state
        self.message = message
        self.updated_at = int(time.time() * 1000)


@dataclass
class LogEntry:
    """Log entry model"""
    job_id: str
    line: str
    timestamp_ms: int
    level: str = "INFO"
