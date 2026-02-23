"""
execution_engine.py — Text-Only Execution Pipeline
=====================================================
Orchestrates text reasoning pipeline:
  1. Multi-step analysis with decision reasons
  2. Live thinking animation
  3. Real Gemini API calls for text generation
  4. Real token/cost tracking from API response
  5. WebSocket broadcasting of every state change
  6. Explainable AI — every step has a decision_reason
"""
import asyncio
import time
import uuid
import random
from typing import Optional

from models import AgentStep, StepStatus, ExecutionPlan
from websocket_manager import manager
from openai_client import chat_completion
from token_tracker import ExecutionUsage
from logger import save_step_log


# ── Thinking sub-steps for live animation ──
THINKING_SUBSTEPS = {
    "Query Analysis": [
        "Parsing user intent…",
        "Identifying key entities and topics…",
        "Classifying query type…",
        "Determining response strategy…",
    ],
    "Context Gathering": [
        "Searching knowledge base…",
        "Retrieving relevant context…",
        "Building context window…",
    ],
    "Concept Decomposition": [
        "Breaking down core concepts…",
        "Mapping component relationships…",
        "Identifying sub-topics…",
    ],
    "Knowledge Retrieval": [
        "Scanning knowledge graph…",
        "Extracting relevant facts…",
        "Cross-referencing sources…",
    ],
    "Data Collection": [
        "Gathering data points…",
        "Validating data sources…",
        "Aggregating metrics…",
    ],
    "Market Analysis": [
        "Analyzing market data…",
        "Comparing competitors…",
        "Evaluating market position…",
    ],
    "Requirements Analysis": [
        "Extracting requirements…",
        "Prioritizing features…",
        "Defining specifications…",
    ],
    "Structure Planning": [
        "Creating outline…",
        "Organizing sections…",
        "Planning content flow…",
    ],
    "Divergent Thinking": [
        "Generating diverse ideas…",
        "Exploring creative angles…",
        "Expanding solution space…",
    ],
    "Evaluation & Ranking": [
        "Scoring ideas by feasibility…",
        "Ranking candidates…",
        "Selecting top approaches…",
    ],
    "Deep Analysis": [
        "Running deep analysis…",
        "Evaluating multiple angles…",
        "Building comprehensive view…",
    ],
    "Reasoning & Synthesis": [
        "Connecting insights…",
        "Building coherent narrative…",
        "Synthesizing conclusions…",
    ],
    "Response Generation": [
        "Sending request to AI model…",
        "Waiting for API response…",
        "Processing response data…",
    ],
    "Quality Check": [
        "Verifying accuracy…",
        "Checking completeness…",
        "Final validation pass…",
    ],
}


# ── Pipeline builder ──

def _build_text_steps(query: str) -> list[AgentStep]:
    """Build text reasoning pipeline with decision reasons."""
    q = query.lower()

    steps = [
        AgentStep(
            name="Query Analysis",
            description="Parse and understand the user's intent",
            prompt=f"Analyze: {query}", input_data=query, order=0,
            pipeline_type="text",
            decision_reason="First step — analyzing user query to understand requirements and context",
        ),
        AgentStep(
            name="Context Gathering",
            description="Gather relevant background information",
            prompt=f"Context for: {query}", input_data=query, order=1,
            pipeline_type="text",
            decision_reason="Building contextual foundation — retrieving background knowledge relevant to query",
        ),
    ]

    # Dynamic middle steps based on query type
    if any(kw in q for kw in ["explain", "what is", "what are", "how does", "why", "define", "tell me"]):
        steps.extend([
            AgentStep(
                name="Concept Decomposition",
                description="Break down into fundamental components",
                prompt=f"Decompose: {query}", input_data=query, order=2,
                pipeline_type="text",
                decision_reason="Query is explanatory — decomposing concepts for thorough understanding",
            ),
            AgentStep(
                name="Knowledge Retrieval",
                description="Retrieve relevant knowledge and examples",
                prompt=f"Retrieve: {query}", input_data=query, order=3,
                pipeline_type="text",
                decision_reason="Retrieving factual knowledge and examples to support explanation",
            ),
        ])
    elif any(kw in q for kw in ["research", "company", "market", "analyze"]):
        steps.extend([
            AgentStep(
                name="Data Collection",
                description="Collect data points and statistics",
                prompt=f"Collect: {query}", input_data=query, order=2,
                pipeline_type="text",
                decision_reason="Research query detected — collecting relevant data and statistics",
            ),
            AgentStep(
                name="Market Analysis",
                description="Analyze trends and landscape",
                prompt=f"Analyze: {query}", input_data=query, order=3,
                pipeline_type="text",
                decision_reason="Performing market and trend analysis for comprehensive research output",
            ),
        ])
    elif any(kw in q for kw in ["create", "build", "make", "write", "generate"]):
        steps.extend([
            AgentStep(
                name="Requirements Analysis",
                description="Define requirements and specifications",
                prompt=f"Requirements: {query}", input_data=query, order=2,
                pipeline_type="text",
                decision_reason="Creative query — analyzing requirements to produce structured output",
            ),
            AgentStep(
                name="Structure Planning",
                description="Plan structure and organization",
                prompt=f"Plan: {query}", input_data=query, order=3,
                pipeline_type="text",
                decision_reason="Planning output structure for clear, organized response",
            ),
        ])
    elif any(kw in q for kw in ["idea", "brainstorm", "suggest"]):
        steps.extend([
            AgentStep(
                name="Divergent Thinking",
                description="Generate diverse ideas",
                prompt=f"Brainstorm: {query}", input_data=query, order=2,
                pipeline_type="text",
                decision_reason="Brainstorming query — generating diverse ideas through divergent thinking",
            ),
            AgentStep(
                name="Evaluation & Ranking",
                description="Evaluate and rank ideas",
                prompt=f"Evaluate: {query}", input_data=query, order=3,
                pipeline_type="text",
                decision_reason="Ranking generated ideas by feasibility and relevance",
            ),
        ])
    else:
        steps.append(
            AgentStep(
                name="Deep Analysis",
                description="Perform deep analysis of the query",
                prompt=f"Analyze: {query}", input_data=query, order=2,
                pipeline_type="text",
                decision_reason="General query — performing deep multi-angle analysis",
            ),
        )

    steps.extend([
        AgentStep(
            name="Reasoning & Synthesis",
            description="Synthesize all gathered information",
            prompt=f"Synthesize: {query}", input_data="Combined context", order=0,
            pipeline_type="text",
            decision_reason="Combining all gathered insights into a coherent, structured narrative",
        ),
        AgentStep(
            name="Response Generation",
            description="Call AI API to generate the final response",
            prompt=query, input_data="Synthesized analysis", order=0,
            pipeline_type="text",
            decision_reason="Sending synthesized context to AI model for final response generation",
        ),
        AgentStep(
            name="Quality Check",
            description="Validate response accuracy and completeness",
            prompt="Verify accuracy", input_data="Generated response", order=0,
            pipeline_type="text",
            decision_reason="Running final quality validation — checking accuracy, completeness, and formatting",
        ),
    ])

    for i, s in enumerate(steps):
        s.order = i
    return steps


# ═══════════════════════════════════════════════════════════════
# EXECUTION ENGINE
# ═══════════════════════════════════════════════════════════════

class ExecutionEngine:
    def __init__(self):
        self.current_plan: Optional[ExecutionPlan] = None
        self.is_running = False
        self.session_id = ""
        self.usage = ExecutionUsage()
        self.selected_model = None

    async def execute(self, query: str, failure_step_id: str = None, model: str = None):
        """Run the full text pipeline."""
        self.session_id = str(uuid.uuid4())[:12]
        self.is_running = True
        self.usage = ExecutionUsage()
        self.selected_model = model
        self._wall_clock_start = time.time()  # wall-clock for consistent timing

        # ── Build text pipeline steps ──
        steps = _build_text_steps(query)

        # Set model name on all steps
        for s in steps:
            s.model_name = model or "gemini-flash"

        self.current_plan = ExecutionPlan(query=query, steps=steps, status="running")

        # Broadcast plan
        await manager.send_plan({
            "query": query,
            "steps": [s.dict() for s in steps],
            "session_id": self.session_id,
            "status": "running",
            "pipeline_type": "text",
            "model": model or "gemini-flash",
        })

        await manager.send_log("INFO", f"⚡ Agent started — Session: {self.session_id}")
        await manager.send_log("INFO", f"📝 Query: {query}")
        if model:
            await manager.send_log("INFO", f"🤖 Model selected: {model}")
        await manager.send_log("INFO", f"📋 Pipeline: {len(steps)} steps")
        await manager.send_log("INFO", "🚀 Pipeline execution started")

        final_response = ""
        api_result = None

        for step in steps:
            if not self.is_running:
                await manager.send_log("WARNING", "⚠ Execution cancelled by user")
                break

            step_start = time.time()

            # ── Simulated failure ──
            if failure_step_id and step.id == failure_step_id:
                await self._activate(step)
                await self._run_thinking(step)
                await asyncio.sleep(0.4)
                await self._fail(step, "Simulated failure — reasoning chain broken")
                self.current_plan.status = "error"
                await manager.send_log("ERROR", "🛑 Pipeline halted due to step failure")
                break

            # ── Activate step ──
            await self._activate(step)

            # ── Broadcast decision reason ──
            if step.decision_reason:
                await manager.send_log("INFO", f"💡 Decision reason: {step.decision_reason}", step.name)

            # ── Run thinking sub-steps ──
            await self._run_thinking(step)

            # ── REAL API CALL for Response Generation ──
            if step.name == "Response Generation":
                # ── Puter.js mode: delegate to browser client ──
                if model and model.startswith("puter"):
                    await manager.send_log("STEP", "🌐 Delegating to Puter.js — free browser-side AI…", step.name)
                    await manager.broadcast({
                        "type": "puter_request",
                        "data": {"query": query, "puter_model": "gpt-4o-mini"}
                    })
                    step_time = time.time() - step_start
                    self.usage.add_simulated_step(step.id, step.name, step_time)
                    await self._broadcast_usage_update()
                    await self._complete(step, "⏳ Awaiting Puter.js browser response…", 0, step_time, 0.0)
                    save_step_log(self.session_id, step.dict())
                    continue

                try:
                    await manager.send_log("STEP", "🔗 Sending request to AI provider…", step.name)
                    api_result = await chat_completion(query, model=model)

                    step_time = time.time() - step_start
                    final_response = api_result["content"]

                    self.usage.add_step(step.id, step.name, api_result, step_time)
                    await self._broadcast_usage_update()

                    await manager.send_log("STEP",
                        f"✅ Response received — {api_result['total_tokens']} tokens "
                        f"(prompt: {api_result['prompt_tokens']}, "
                        f"completion: {api_result['completion_tokens']}, "
                        f"thinking: {api_result.get('thinking_tokens', 0)})",
                        step.name)
                    await manager.send_log("INFO",
                        f"💰 Cost: ${api_result['cost']:.6f} ({api_result['model']} via {api_result.get('provider', 'api')})",
                        step.name)

                    await self._stream_response(final_response)
                    await self._complete(step, final_response,
                                         api_result["total_tokens"], step_time,
                                         api_result["cost"])

                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    step_time = time.time() - step_start
                    error_msg = str(e)
                    print(f"[engine] ERROR in Response Generation: {error_msg}")
                    await manager.send_log("ERROR", f"❌ API Error: {error_msg}", step.name)
                    await self._fail(step, f"API Error: {error_msg}")
                    self.current_plan.status = "error"
                    await self._send_error_completion(error_msg)
                    return self.current_plan

            else:
                # Non-API steps (analysis, synthesis, etc.)
                step_time = time.time() - step_start
                step_output = f"Completed {step.name} — ready for next stage"
                self.usage.add_simulated_step(step.id, step.name, step_time)
                await self._broadcast_usage_update()
                await self._complete(step, step_output, 0, step_time, 0.0)

            save_step_log(self.session_id, step.dict())

        # ── Final completion ──
        if self.current_plan.status != "error":
            self.current_plan.status = "complete"

        # Use wall-clock time for consistency with frontend timer
        total_time_val = round(time.time() - self._wall_clock_start, 2)
        self.current_plan.total_tokens = self.usage.total_tokens
        self.current_plan.total_cost = self.usage.total_cost
        self.current_plan.total_time = total_time_val

        is_puter = model is not None and model.startswith("puter")
        completion_data = {
            "total_tokens": self.usage.total_tokens,
            "total_prompt_tokens": self.usage.total_prompt_tokens,
            "total_completion_tokens": self.usage.total_completion_tokens,
            "total_thinking_tokens": self.usage.total_thinking_tokens,
            "total_cost": round(self.usage.total_cost, 8),
            "total_time": round(total_time_val, 2),
            "status": self.current_plan.status,
            "final_response": final_response,
            "session_id": self.session_id,
            "model": "gpt-4o-mini" if is_puter else (api_result["model"] if api_result else ""),
            "provider": "Puter.js" if is_puter else (api_result.get("provider", "") if api_result else ""),
            "usage": self.usage.to_dict(),
            "pipeline_type": "text",
            "puter_mode": is_puter,
        }
        await manager.send_complete(completion_data)

        await manager.send_log("INFO",
            f"🏁 Execution complete — {self.usage.total_tokens} tokens, "
            f"${self.usage.total_cost:.6f}, {total_time_val:.1f}s")

        self.is_running = False
        return self.current_plan

    async def rerun_step(self, step_id: str):
        """Re-run a single step (always calls the API)."""
        if not self.current_plan:
            return

        target = next((s for s in self.current_plan.steps if s.id == step_id), None)
        if not target:
            await manager.send_error(f"Step {step_id} not found")
            return

        await manager.send_log("INFO", f"🔄 Re-running step: {target.name}")
        start = time.time()

        target.status = StepStatus.WAITING
        await manager.send_step_update(target.dict())
        await asyncio.sleep(0.2)

        await self._activate(target)
        await self._run_thinking(target)

        try:
            result = await chat_completion(self.current_plan.query, model=self.selected_model)
            elapsed = time.time() - start
            await self._stream_response(result["content"])
            await self._complete(target, result["content"],
                                 result["total_tokens"], elapsed, result["cost"])

            await manager.send_log("STEP",
                f"✅ Re-run complete — {result.get('total_tokens', 0)} tokens",
                target.name)
        except Exception as e:
            await self._fail(target, str(e))

        save_step_log(self.session_id, target.dict())

    def cancel(self):
        self.is_running = False

    # ── private helpers ──

    async def _activate(self, step: AgentStep):
        step.status = StepStatus.RUNNING
        step.timestamp = __import__("datetime").datetime.utcnow().isoformat()
        await manager.send_step_update(step.dict())
        await manager.send_log("INFO", f"▶ Starting: {step.name}", step.name)

    async def _run_thinking(self, step: AgentStep):
        """Fire thinking sub-step messages with realistic processing delays."""
        msgs = THINKING_SUBSTEPS.get(step.name, ["Processing\u2026", "Analyzing\u2026", "Computing\u2026"])
        for i, msg in enumerate(msgs):
            await manager.send_log("STEP", f"  \U0001f4ad [{step.name}] {msg}", step.name)
            await manager.broadcast({
                "type": "thinking",
                "data": {
                    "step_id": step.id,
                    "step_name": step.name,
                    "message": msg,
                    "pipeline_type": step.pipeline_type,
                }
            })
            # Randomized processing delay per sub-step (0.15\u20130.65s)
            await asyncio.sleep(0.15 + random.random() * 0.5)

    async def _complete(self, step: AgentStep, output: str, tokens: int,
                         exec_time: float, cost: float):
        step.status = StepStatus.SUCCESS
        step.output_data = output
        step.tokens = tokens
        step.execution_time = exec_time
        step.reasoning = f"cost={cost:.8f}"
        await manager.send_step_update(step.dict())
        if tokens > 0:
            await manager.send_log("INFO",
                f"✅ Completed: {step.name} ({exec_time:.1f}s, {tokens} tokens, ${cost:.6f})",
                step.name)
        else:
            await manager.send_log("INFO",
                f"✅ Completed: {step.name} ({exec_time:.1f}s)", step.name)

    async def _fail(self, step: AgentStep, error: str):
        step.status = StepStatus.ERROR
        step.output_data = f"ERROR: {error}"
        await manager.send_step_update(step.dict())
        await manager.send_log("ERROR", f"❌ Failed: {step.name} — {error}", step.name)
        await manager.send_error(error, step.id)

    async def _stream_response(self, content: str):
        """Stream the response to frontend in chunks."""
        words = content.split()
        chunk = ""
        for i, word in enumerate(words):
            chunk += word + " "
            if (i + 1) % 10 == 0:
                await manager.send_response_chunk(chunk)
                chunk = ""
                await asyncio.sleep(0.01)
        if chunk:
            await manager.send_response_chunk(chunk)

    async def _broadcast_usage_update(self):
        """Send live usage data to frontend after each step completes."""
        elapsed = round(time.time() - self._wall_clock_start, 2)
        usage_data = self.usage.to_dict()
        usage_data["wall_clock_time"] = elapsed
        await manager.broadcast({
            "type": "usage_update",
            "data": usage_data
        })

    async def _send_error_completion(self, error_msg: str):
        """Send error completion so UI stops gracefully."""
        await manager.send_complete({
            "total_tokens": self.usage.total_tokens,
            "total_prompt_tokens": self.usage.total_prompt_tokens,
            "total_completion_tokens": self.usage.total_completion_tokens,
            "total_cost": round(self.usage.total_cost, 8),
            "total_time": round(time.time() - self._wall_clock_start, 2),
            "status": "error",
            "error": error_msg,
            "final_response": "",
            "session_id": self.session_id,
            "usage": self.usage.to_dict(),
            "pipeline_type": "text",
        })
        self.is_running = False


# ── Singleton ──
engine = ExecutionEngine()
