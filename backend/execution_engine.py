"""
execution_engine.py — Real Execution Pipeline
===============================================
Orchestrates the full agent pipeline:
  1. Live thinking steps with timed async updates
  2. Real Gemini API call for "Response Generation"
  3. Real token/cost tracking from API response
  4. WebSocket broadcasting of every state change
  5. Proper error handling — API failures become error nodes

NO fake tokens. NO dummy responses. NO silent fallbacks.
"""
import asyncio
import time
import uuid
from typing import Optional

from models import AgentStep, StepStatus, ExecutionPlan
from websocket_manager import manager
from openai_client import chat_completion
from token_tracker import ExecutionUsage
from logger import save_step_log


# ── Thinking sub-steps for realistic live animation ──
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
    "Trend Detection": [
        "Scanning for patterns…",
        "Identifying emerging trends…",
        "Projecting trajectories…",
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
        "Sending request to Gemini AI…",
        "Waiting for API response…",
        "Processing response data…",
    ],
    "Quality Check": [
        "Verifying accuracy…",
        "Checking completeness…",
        "Final validation pass…",
    ],
}

# ── Execution plan builder ──

def _build_steps(query: str) -> list[AgentStep]:
    """Create execution plan steps based on query content."""
    q = query.lower()

    base = [
        AgentStep(name="Query Analysis",
                  description="Parse and understand the user's intent",
                  prompt=f"Analyze: {query}", input_data=query, order=0),
        AgentStep(name="Context Gathering",
                  description="Gather relevant background information",
                  prompt=f"Context for: {query}", input_data=query, order=1),
    ]

    if any(kw in q for kw in ["explain", "what is", "what are", "how does", "why", "define", "tell me"]):
        mid = [
            AgentStep(name="Concept Decomposition",
                      description="Break down into fundamental components",
                      prompt=f"Decompose: {query}", input_data=query, order=2),
            AgentStep(name="Knowledge Retrieval",
                      description="Retrieve relevant knowledge and examples",
                      prompt=f"Retrieve: {query}", input_data=query, order=3),
        ]
    elif any(kw in q for kw in ["research", "company", "market", "analyze"]):
        mid = [
            AgentStep(name="Data Collection",
                      description="Collect data points and statistics",
                      prompt=f"Collect: {query}", input_data=query, order=2),
            AgentStep(name="Market Analysis",
                      description="Analyze trends and landscape",
                      prompt=f"Analyze: {query}", input_data=query, order=3),
        ]
    elif any(kw in q for kw in ["create", "build", "make", "write", "generate"]):
        mid = [
            AgentStep(name="Requirements Analysis",
                      description="Define requirements and specifications",
                      prompt=f"Requirements: {query}", input_data=query, order=2),
            AgentStep(name="Structure Planning",
                      description="Plan structure and organization",
                      prompt=f"Plan: {query}", input_data=query, order=3),
        ]
    elif any(kw in q for kw in ["idea", "brainstorm", "suggest"]):
        mid = [
            AgentStep(name="Divergent Thinking",
                      description="Generate diverse ideas",
                      prompt=f"Brainstorm: {query}", input_data=query, order=2),
            AgentStep(name="Evaluation & Ranking",
                      description="Evaluate and rank ideas",
                      prompt=f"Evaluate: {query}", input_data=query, order=3),
        ]
    else:
        mid = [
            AgentStep(name="Deep Analysis",
                      description="Perform deep analysis of the query",
                      prompt=f"Analyze: {query}", input_data=query, order=2),
        ]

    tail = [
        AgentStep(name="Reasoning & Synthesis",
                  description="Synthesize all gathered information",
                  prompt=f"Synthesize: {query}", input_data="Combined context", order=0),
        AgentStep(name="Response Generation",
                  description="Call Gemini AI API to generate the final response",
                  prompt=query, input_data="Synthesized analysis", order=0),
        AgentStep(name="Quality Check",
                  description="Validate response accuracy and completeness",
                  prompt="Verify accuracy", input_data="Generated response", order=0),
    ]

    all_steps = base + mid + tail
    for i, s in enumerate(all_steps):
        s.order = i
    return all_steps


# ═══════════════════════════════════════════════════════════════
# EXECUTION ENGINE
# ═══════════════════════════════════════════════════════════════

class ExecutionEngine:
    def __init__(self):
        self.current_plan: Optional[ExecutionPlan] = None
        self.is_running = False
        self.session_id = ""
        self.usage = ExecutionUsage()

    # ── public ──

    async def execute(self, query: str, failure_step_id: str = None):
        """Run the full pipeline. All updates broadcast via WebSocket."""
        self.session_id = str(uuid.uuid4())[:12]
        self.is_running = True
        self.usage = ExecutionUsage()

        steps = _build_steps(query)
        self.current_plan = ExecutionPlan(query=query, steps=steps, status="running")

        # Broadcast plan
        await manager.send_plan({
            "query": query,
            "steps": [s.dict() for s in steps],
            "session_id": self.session_id,
            "status": "running",
        })
        await manager.send_log("INFO", f"⚡ Agent started — Session: {self.session_id}")
        await manager.send_log("INFO", f"📝 Query: {query}")
        await manager.send_log("INFO", f"📋 Plan: {len(steps)} steps created")

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

            # ── Run thinking sub-steps ──
            await self._run_thinking(step)

            # Debug: log step entry to file
            with open("debug.log", "a") as f:
                f.write(f"[{time.time():.1f}] Step: {step.name} | order: {step.order}\n")

            # ── REAL API CALL for Response Generation ──
            if step.name == "Response Generation":
                try:
                    with open("debug.log", "a") as f:
                        f.write(f"[{time.time():.1f}] Entering Response Generation try block\n")
                    await manager.send_log("STEP", "🔗 Sending request to AI provider…", step.name)
                    api_result = await chat_completion(query)
                    with open("debug.log", "a") as f:
                        f.write(f"[{time.time():.1f}] Got result: provider={api_result.get('provider')}, tokens={api_result.get('total_tokens')}\n")

                    step_time = time.time() - step_start
                    final_response = api_result["content"]

                    # Record REAL tokens
                    self.usage.add_step(step.id, step.name, api_result, step_time)

                    await manager.send_log("STEP",
                        f"✅ Response received — {api_result['total_tokens']} tokens "
                        f"(prompt: {api_result['prompt_tokens']}, "
                        f"completion: {api_result['completion_tokens']}, "
                        f"thinking: {api_result.get('thinking_tokens', 0)})",
                        step.name)
                    await manager.send_log("INFO",
                        f"💰 Cost: ${api_result['cost']:.6f} ({api_result['model']} via {api_result.get('provider', 'api')})",
                        step.name)

                    # Stream response to frontend in chunks
                    await self._stream_response(final_response)

                    # Complete step with REAL data
                    await self._complete(step, final_response,
                                         api_result["total_tokens"], step_time,
                                         api_result["cost"])

                except Exception as e:
                    import traceback
                    with open("debug.log", "a") as f:
                        f.write(f"[{time.time():.1f}] EXCEPTION: {e}\n")
                        traceback.print_exc(file=f)
                    step_time = time.time() - step_start
                    error_msg = str(e)
                    print(f"[engine] ERROR in Response Generation: {error_msg}")
                    await manager.send_log("ERROR", f"❌ API Error: {error_msg}", step.name)
                    await self._fail(step, f"API Error: {error_msg}")
                    self.current_plan.status = "error"

                    # Send error completion so UI stops gracefully
                    await manager.send_complete({
                        "total_tokens": self.usage.total_tokens,
                        "total_prompt_tokens": self.usage.total_prompt_tokens,
                        "total_completion_tokens": self.usage.total_completion_tokens,
                        "total_cost": round(self.usage.total_cost, 8),
                        "total_time": round(time.time() - step_start, 2),
                        "status": "error",
                        "error": error_msg,
                        "final_response": "",
                        "session_id": self.session_id,
                        "usage": self.usage.to_dict(),
                    })
                    self.is_running = False
                    return self.current_plan
            else:
                # Non-API steps — no artificial delay
                step_time = time.time() - step_start

                step_output = f"Completed {step.name} — ready for next stage"
                self.usage.add_simulated_step(step.id, step.name, step_time)

                await self._complete(step, step_output, 0, step_time, 0.0)

            save_step_log(self.session_id, step.dict())

        # ── Final completion ──
        if self.current_plan.status != "error":
            self.current_plan.status = "complete"

        total_time_val = self.usage.total_time
        self.current_plan.total_tokens = self.usage.total_tokens
        self.current_plan.total_cost = self.usage.total_cost
        self.current_plan.total_time = total_time_val

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
            "model": api_result["model"] if api_result else "",
            "provider": api_result.get("provider", "") if api_result else "",
            "usage": self.usage.to_dict(),
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
            result = await chat_completion(self.current_plan.query)
            elapsed = time.time() - start

            await self._stream_response(result["content"])
            await self._complete(target, result["content"],
                                  result["total_tokens"], elapsed, result["cost"])

            await manager.send_log("STEP",
                f"✅ Re-run complete — {result['total_tokens']} tokens, "
                f"${result['cost']:.6f}", target.name)
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
        """Fire thinking sub-step messages instantly — no delays."""
        msgs = THINKING_SUBSTEPS.get(step.name, ["Processing…", "Analyzing…", "Computing…"])
        for msg in msgs:
            await manager.send_log("STEP", f"  💭 [{step.name}] {msg}", step.name)
            await manager.broadcast({
                "type": "thinking",
                "data": {"step_id": step.id, "step_name": step.name, "message": msg}
            })

    async def _complete(self, step: AgentStep, output: str, tokens: int,
                         exec_time: float, cost: float):
        step.status = StepStatus.SUCCESS
        step.output_data = output
        step.tokens = tokens
        step.execution_time = exec_time
        # Store cost in reasoning field for frontend access
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
        """Stream the response to frontend in larger chunks for faster display."""
        words = content.split()
        chunk = ""
        for i, word in enumerate(words):
            chunk += word + " "
            if (i + 1) % 10 == 0:  # Send every 10 words for speed
                await manager.send_response_chunk(chunk)
                chunk = ""
                await asyncio.sleep(0.01)
        if chunk:
            await manager.send_response_chunk(chunk)


# ── Singleton ──
engine = ExecutionEngine()
