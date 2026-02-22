"""
token_tracker.py — Real-time Token & Cost Tracking
====================================================
Accumulates REAL token usage and cost from the OpenAI API across an execution.
All numbers come directly from API responses — nothing is estimated or faked.
"""
from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class StepUsage:
    """Token usage for a single execution step."""
    step_id: str
    step_name: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    thinking_tokens: int = 0
    cost: float = 0.0
    model: str = ""
    execution_time: float = 0.0


@dataclass
class ExecutionUsage:
    """Aggregated token usage for the entire execution pipeline."""
    steps: List[StepUsage] = field(default_factory=list)

    @property
    def total_prompt_tokens(self) -> int:
        return sum(s.prompt_tokens for s in self.steps)

    @property
    def total_completion_tokens(self) -> int:
        return sum(s.completion_tokens for s in self.steps)

    @property
    def total_tokens(self) -> int:
        return sum(s.total_tokens for s in self.steps)

    @property
    def total_thinking_tokens(self) -> int:
        return sum(s.thinking_tokens for s in self.steps)

    @property
    def total_cost(self) -> float:
        return sum(s.cost for s in self.steps)

    @property
    def total_time(self) -> float:
        return sum(s.execution_time for s in self.steps)

    def add_step(self, step_id: str, step_name: str, api_result: dict, execution_time: float):
        """Add a step's usage from an API response."""
        self.steps.append(StepUsage(
            step_id=step_id,
            step_name=step_name,
            prompt_tokens=api_result.get("prompt_tokens", 0),
            completion_tokens=api_result.get("completion_tokens", 0),
            total_tokens=api_result.get("total_tokens", 0),
            thinking_tokens=api_result.get("thinking_tokens", 0),
            cost=api_result.get("cost", 0.0),
            model=api_result.get("model", ""),
            execution_time=execution_time,
        ))

    def add_simulated_step(self, step_id: str, step_name: str, execution_time: float):
        """Record a non-API step (thinking/analysis) with zero tokens."""
        self.steps.append(StepUsage(
            step_id=step_id,
            step_name=step_name,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            thinking_tokens=0,
            cost=0.0,
            model="local",
            execution_time=execution_time,
        ))

    def to_dict(self) -> Dict:
        return {
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_tokens,
            "total_thinking_tokens": self.total_thinking_tokens,
            "total_cost": round(self.total_cost, 8),
            "total_time": round(self.total_time, 2),
            "steps": [
                {
                    "step_id": s.step_id,
                    "step_name": s.step_name,
                    "prompt_tokens": s.prompt_tokens,
                    "completion_tokens": s.completion_tokens,
                    "total_tokens": s.total_tokens,
                    "thinking_tokens": s.thinking_tokens,
                    "cost": round(s.cost, 8),
                    "model": s.model,
                    "execution_time": round(s.execution_time, 2),
                }
                for s in self.steps
            ],
        }
