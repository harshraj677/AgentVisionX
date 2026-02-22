"""Agent Planner — Creates reasoning steps from user queries."""
from models import AgentStep, StepStatus
from typing import List


def create_execution_plan(query: str) -> List[AgentStep]:
    """Generate a list of reasoning steps based on the user query."""
    query_lower = query.lower()

    # Base steps every query goes through
    steps = [
        AgentStep(
            name="Query Analysis",
            description="Parse and understand the user's intent",
            prompt=f"Analyze the following query and identify the user's intent: {query}",
            input_data=query,
            status=StepStatus.WAITING,
            order=0,
        ),
        AgentStep(
            name="Context Gathering",
            description="Gather relevant context and background information",
            prompt=f"Gather context relevant to: {query}",
            input_data=query,
            status=StepStatus.WAITING,
            order=1,
        ),
    ]

    # Add task-specific steps based on query type
    if any(kw in query_lower for kw in ["explain", "what is", "how does", "why"]):
        steps.extend(_explanation_steps(query))
    elif any(kw in query_lower for kw in ["research", "company", "market", "analyze"]):
        steps.extend(_research_steps(query))
    elif any(kw in query_lower for kw in ["report", "create", "build", "make"]):
        steps.extend(_creation_steps(query))
    elif any(kw in query_lower for kw in ["idea", "generate", "brainstorm", "suggest"]):
        steps.extend(_ideation_steps(query))
    else:
        steps.extend(_general_steps(query))

    # Always end with synthesis and output
    steps.extend([
        AgentStep(
            name="Reasoning & Synthesis",
            description="Synthesize all gathered information into a coherent response",
            prompt=f"Synthesize findings for: {query}",
            input_data="Combined context from previous steps",
            status=StepStatus.WAITING,
            order=len(steps),
        ),
        AgentStep(
            name="Response Generation",
            description="Generate the final formatted response",
            prompt=f"Generate a comprehensive response for: {query}",
            input_data="Synthesized analysis",
            status=StepStatus.WAITING,
            order=len(steps) + 1,
        ),
        AgentStep(
            name="Quality Check",
            description="Validate response accuracy and completeness",
            prompt="Verify the response is accurate, complete, and well-formatted",
            input_data="Generated response",
            status=StepStatus.WAITING,
            order=len(steps) + 2,
        ),
    ])

    # Re-index orders
    for i, step in enumerate(steps):
        step.order = i

    return steps


def _explanation_steps(query: str) -> List[AgentStep]:
    return [
        AgentStep(
            name="Concept Decomposition",
            description="Break down the concept into fundamental components",
            prompt=f"Decompose the concept in: {query}",
            input_data=query,
            status=StepStatus.WAITING,
            order=2,
        ),
        AgentStep(
            name="Knowledge Retrieval",
            description="Retrieve relevant knowledge and examples",
            prompt=f"Retrieve knowledge for: {query}",
            input_data=query,
            status=StepStatus.WAITING,
            order=3,
        ),
    ]


def _research_steps(query: str) -> List[AgentStep]:
    return [
        AgentStep(
            name="Data Collection",
            description="Collect relevant data points and statistics",
            prompt=f"Collect data for: {query}",
            input_data=query,
            status=StepStatus.WAITING,
            order=2,
        ),
        AgentStep(
            name="Market Analysis",
            description="Analyze market trends and competitive landscape",
            prompt=f"Analyze market for: {query}",
            input_data=query,
            status=StepStatus.WAITING,
            order=3,
        ),
        AgentStep(
            name="Trend Detection",
            description="Identify emerging trends and patterns",
            prompt=f"Detect trends for: {query}",
            input_data=query,
            status=StepStatus.WAITING,
            order=4,
        ),
    ]


def _creation_steps(query: str) -> List[AgentStep]:
    return [
        AgentStep(
            name="Requirements Analysis",
            description="Define requirements and specifications",
            prompt=f"Analyze requirements for: {query}",
            input_data=query,
            status=StepStatus.WAITING,
            order=2,
        ),
        AgentStep(
            name="Structure Planning",
            description="Plan the structure and organization",
            prompt=f"Plan structure for: {query}",
            input_data=query,
            status=StepStatus.WAITING,
            order=3,
        ),
    ]


def _ideation_steps(query: str) -> List[AgentStep]:
    return [
        AgentStep(
            name="Divergent Thinking",
            description="Generate diverse ideas without constraint",
            prompt=f"Brainstorm ideas for: {query}",
            input_data=query,
            status=StepStatus.WAITING,
            order=2,
        ),
        AgentStep(
            name="Evaluation & Ranking",
            description="Evaluate and rank generated ideas",
            prompt=f"Evaluate ideas for: {query}",
            input_data=query,
            status=StepStatus.WAITING,
            order=3,
        ),
    ]


def _general_steps(query: str) -> List[AgentStep]:
    return [
        AgentStep(
            name="Deep Analysis",
            description="Perform deep analysis of the query",
            prompt=f"Deep analyze: {query}",
            input_data=query,
            status=StepStatus.WAITING,
            order=2,
        ),
    ]
