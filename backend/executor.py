"""Executor — Runs the agent pipeline with live updates."""
import asyncio
import time
import uuid
from typing import List, Optional
from models import AgentStep, StepStatus, ExecutionPlan
from planner import create_execution_plan
from live_thinking_engine import run_thinking_for_step, activate_step, complete_step, fail_step
from chatgpt_client import call_chatgpt
from websocket_manager import manager
from logger import save_step_log


class AgentExecutor:
    def __init__(self):
        self.current_plan: Optional[ExecutionPlan] = None
        self.is_running = False
        self.session_id = ""
        self.simulate_failure_at: Optional[str] = None  # step_id to fail

    async def execute_query(self, query: str, failure_step_id: str = None):
        """Execute a full agent pipeline for a query."""
        self.session_id = str(uuid.uuid4())[:12]
        self.is_running = True
        self.simulate_failure_at = failure_step_id

        # Create execution plan
        steps = create_execution_plan(query)
        self.current_plan = ExecutionPlan(query=query, steps=steps, status="running")

        # Send initial plan to frontend
        plan_data = {
            "query": query,
            "steps": [s.dict() for s in steps],
            "session_id": self.session_id,
            "status": "running",
        }
        await manager.send_plan(plan_data)
        await manager.send_log("INFO", f"Agent started — Session: {self.session_id}")
        await manager.send_log("INFO", f"Query: {query}")
        await manager.send_log("INFO", f"Plan created with {len(steps)} steps")

        total_tokens = 0
        total_time = 0.0
        final_response = ""

        # Execute each step
        for i, step in enumerate(steps):
            if not self.is_running:
                await manager.send_log("WARNING", "Execution cancelled by user")
                break

            start_time = time.time()

            # Check for simulated failure
            if self.simulate_failure_at and step.id == self.simulate_failure_at:
                await activate_step(step)
                await run_thinking_for_step(step)
                await asyncio.sleep(0.5)
                await fail_step(step, "Simulated failure — reasoning chain broken")
                self.current_plan.status = "error"
                await manager.send_log("ERROR", "Pipeline halted due to step failure")
                break

            # Activate step
            await activate_step(step)
            await asyncio.sleep(0.3)

            # Run thinking animation
            await run_thinking_for_step(step)

            # Call LLM for the last few steps (response generation)
            if step.name == "Response Generation":
                result = await call_chatgpt(query)
                step_output = result["content"]
                step_tokens = result["tokens"]
                final_response = step_output

                # Stream response chunks
                words = step_output.split()
                chunk = ""
                for j, word in enumerate(words):
                    chunk += word + " "
                    if j % 5 == 0:
                        await manager.send_response_chunk(chunk)
                        chunk = ""
                        await asyncio.sleep(0.05)
                if chunk:
                    await manager.send_response_chunk(chunk)
            else:
                # Simulate step execution
                await asyncio.sleep(0.8)
                step_output = f"Completed {step.name} analysis"
                step_tokens = 50 + (i * 30)

            exec_time = time.time() - start_time
            total_tokens += step_tokens
            total_time += exec_time

            # Complete step
            await complete_step(step, step_output, step_tokens, exec_time)

            # Save to logs
            save_step_log(self.session_id, step.dict())

            await asyncio.sleep(0.2)

        # Send completion
        cost = total_tokens * 0.000002  # rough estimate
        self.current_plan.total_tokens = total_tokens
        self.current_plan.total_cost = cost
        self.current_plan.total_time = total_time
        if self.current_plan.status != "error":
            self.current_plan.status = "complete"

        await manager.send_complete({
            "total_tokens": total_tokens,
            "total_cost": round(cost, 6),
            "total_time": round(total_time, 2),
            "status": self.current_plan.status,
            "final_response": final_response,
            "session_id": self.session_id,
        })
        await manager.send_log("INFO",
            f"Execution complete — {total_tokens} tokens, ${cost:.6f}, {total_time:.1f}s")

        self.is_running = False
        return self.current_plan

    async def rerun_step(self, step_id: str):
        """Re-run a specific step."""
        if not self.current_plan:
            return

        target_step = None
        for step in self.current_plan.steps:
            if step.id == step_id:
                target_step = step
                break

        if not target_step:
            await manager.send_error(f"Step {step_id} not found")
            return

        await manager.send_log("INFO", f"Re-running step: {target_step.name}")

        start_time = time.time()
        target_step.status = StepStatus.WAITING
        await manager.send_step_update(target_step.dict())
        await asyncio.sleep(0.3)

        await activate_step(target_step)
        await run_thinking_for_step(target_step)

        result = await call_chatgpt(target_step.prompt)
        exec_time = time.time() - start_time

        await complete_step(target_step, result["content"], result["tokens"], exec_time)
        save_step_log(self.session_id, target_step.dict())

    def cancel(self):
        """Cancel current execution."""
        self.is_running = False


executor = AgentExecutor()
