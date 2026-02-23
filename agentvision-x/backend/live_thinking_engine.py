"""Live Thinking Engine — Sends progressive thinking steps with timed updates."""
import asyncio
import time
from typing import List
from models import AgentStep, StepStatus
from websocket_manager import manager


THINKING_MESSAGES = {
    "Query Analysis": [
        "Parsing user intent...",
        "Identifying key entities...",
        "Classifying query type...",
    ],
    "Context Gathering": [
        "Searching knowledge base...",
        "Retrieving relevant context...",
        "Building context window...",
    ],
    "Concept Decomposition": [
        "Breaking down concepts...",
        "Identifying sub-components...",
        "Mapping relationships...",
    ],
    "Knowledge Retrieval": [
        "Scanning knowledge graph...",
        "Extracting relevant facts...",
        "Cross-referencing sources...",
    ],
    "Data Collection": [
        "Gathering data points...",
        "Validating data sources...",
        "Aggregating metrics...",
    ],
    "Market Analysis": [
        "Analyzing market data...",
        "Comparing competitors...",
        "Evaluating market position...",
    ],
    "Trend Detection": [
        "Scanning for patterns...",
        "Identifying emerging trends...",
        "Projecting trajectories...",
    ],
    "Requirements Analysis": [
        "Extracting requirements...",
        "Prioritizing features...",
        "Defining specifications...",
    ],
    "Structure Planning": [
        "Creating outline...",
        "Organizing sections...",
        "Planning content flow...",
    ],
    "Divergent Thinking": [
        "Generating ideas...",
        "Exploring possibilities...",
        "Expanding solution space...",
    ],
    "Evaluation & Ranking": [
        "Scoring ideas...",
        "Ranking by feasibility...",
        "Selecting top candidates...",
    ],
    "Deep Analysis": [
        "Running deep analysis...",
        "Evaluating multiple angles...",
        "Building comprehensive view...",
    ],
    "Reasoning & Synthesis": [
        "Connecting insights...",
        "Building coherent narrative...",
        "Synthesizing conclusions...",
    ],
    "Response Generation": [
        "Composing response...",
        "Formatting output...",
        "Applying structure...",
    ],
    "Quality Check": [
        "Verifying accuracy...",
        "Checking completeness...",
        "Final validation pass...",
    ],
}


async def run_thinking_for_step(step: AgentStep):
    """Send progressive thinking messages for a step."""
    messages = THINKING_MESSAGES.get(step.name, [
        "Processing...",
        "Analyzing...",
        "Computing results...",
    ])

    for msg in messages:
        await manager.send_log("STEP", f"[{step.name}] {msg}", step.name)
        await asyncio.sleep(0.6)


async def activate_step(step: AgentStep):
    """Mark step as running and send update."""
    step.status = StepStatus.RUNNING
    step.timestamp = __import__("datetime").datetime.utcnow().isoformat()
    await manager.send_step_update(step.dict())
    await manager.send_log("INFO", f"Starting step: {step.name}", step.name)


async def complete_step(step: AgentStep, output: str, tokens: int, exec_time: float):
    """Mark step as success and send update."""
    step.status = StepStatus.SUCCESS
    step.output_data = output
    step.tokens = tokens
    step.execution_time = exec_time
    await manager.send_step_update(step.dict())
    await manager.send_log("INFO", f"Completed: {step.name} ({exec_time:.1f}s, {tokens} tokens)", step.name)


async def fail_step(step: AgentStep, error: str):
    """Mark step as error and send update."""
    step.status = StepStatus.ERROR
    step.output_data = f"ERROR: {error}"
    await manager.send_step_update(step.dict())
    await manager.send_log("ERROR", f"Failed: {step.name} — {error}", step.name)
    await manager.send_error(error, step.id)
