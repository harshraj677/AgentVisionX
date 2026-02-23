"""Data models for AgentVision X."""
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime
import uuid


class StepStatus(str, Enum):
    WAITING = "waiting"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"


class AgentStep(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    description: str = ""
    prompt: str = ""
    input_data: str = ""
    output_data: str = ""
    reasoning: str = ""
    tokens: int = 0
    status: StepStatus = StepStatus.WAITING
    execution_time: float = 0.0
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    order: int = 0
    decision_reason: str = ""
    pipeline_type: str = "text"
    model_name: str = ""


class ExecutionPlan(BaseModel):
    query: str
    steps: List[AgentStep] = []
    total_tokens: int = 0
    total_cost: float = 0.0
    total_time: float = 0.0
    status: str = "idle"


class QueryRequest(BaseModel):
    query: str
    step_id: Optional[str] = None  # For simulate failure
    model: Optional[str] = None    # Model selection from frontend


class WSMessage(BaseModel):
    type: str  # step_update, log, response_chunk, plan, complete, error
    data: dict = {}
