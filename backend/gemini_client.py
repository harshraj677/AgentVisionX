"""
gemini_client.py — Google Gemini API Client
=============================================
Provides chat completion using Google's Gemini API.
Returns real token counts and timing from the API response.
"""
import os
import time
import asyncio
import google.generativeai as genai
from typing import Optional

# ── Configure Gemini ──
_model = None
_model_name = "gemini-2.5-flash"


def _get_model():
    """Lazy-init the Gemini model."""
    global _model
    if _model is None:
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set in environment")
        genai.configure(api_key=api_key)
        _model = genai.GenerativeModel(
            model_name=_model_name,
            generation_config={
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 4096,
            },
            system_instruction=(
                "You are a highly knowledgeable AI assistant. "
                "Give clear, accurate, detailed, well-structured answers. "
                "Use markdown formatting: ## headers, ### subheaders, **bold**, "
                "bullet points, numbered lists, code blocks with language tags. "
                "Be comprehensive and precise."
            ),
        )
        print(f"[gemini_client] ✅ Gemini configured — model: {_model_name}")
    return _model


# ── Pricing (Gemini — free tier has no cost) ──
MODEL_PRICING = {
    "gemini-2.5-flash": {"input": 0.0, "output": 0.0},
    "gemini-2.0-flash": {"input": 0.0, "output": 0.0},
    "gemini-1.5-flash": {"input": 0.0, "output": 0.0},
    "gemini-1.5-pro": {"input": 1.25 / 1_000_000, "output": 5.00 / 1_000_000},
    "gemini-2.0-flash-001": {"input": 0.0, "output": 0.0},
}


def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    pricing = MODEL_PRICING.get(model, {"input": 0.0, "output": 0.0})
    return (prompt_tokens * pricing["input"]) + (completion_tokens * pricing["output"])


async def chat_completion(
    query: str,
    model: str = None,
    max_tokens: int = 4096,
    temperature: float = 0.7,
    system_prompt: str = "",
) -> dict:
    """
    Send a request to Google Gemini API.

    Returns:
        {
            "content": str,
            "model": str,
            "provider": "gemini",
            "prompt_tokens": int,
            "completion_tokens": int,
            "total_tokens": int,
            "cost": float,
        }
    """
    model_instance = _get_model()
    use_model = model or _model_name

    start_time = time.time()

    # Run the blocking Gemini call in a thread to keep async
    # Retry up to 3 times on rate limit errors
    response = None
    last_error = None
    for attempt in range(3):
        try:
            response = await asyncio.to_thread(
                model_instance.generate_content, query
            )
            break
        except Exception as e:
            last_error = e
            error_str = str(e)
            if "429" in error_str or "ResourceExhausted" in error_str:
                wait = 15 * (attempt + 1)
                print(f"[gemini_client] ⚠ Rate limited, retrying in {wait}s (attempt {attempt+1}/3)")
                await asyncio.sleep(wait)
            else:
                raise

    if response is None:
        raise last_error

    elapsed = time.time() - start_time

    # Extract real token counts from API response
    usage = response.usage_metadata
    prompt_tokens = usage.prompt_token_count if usage else 0
    completion_tokens = usage.candidates_token_count if usage else 0
    total_tokens = usage.total_token_count if usage else 0

    cost = calculate_cost(use_model, prompt_tokens, completion_tokens)

    content = ""
    if response.parts:
        content = response.text
    elif response.candidates:
        content = response.candidates[0].content.parts[0].text

    print(f"[gemini_client] ✅ Response received — {total_tokens} tokens "
          f"(prompt: {prompt_tokens}, completion: {completion_tokens}) in {elapsed:.2f}s")

    return {
        "content": content,
        "model": use_model,
        "provider": "gemini",
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "cost": cost,
    }


def get_provider() -> str:
    return "gemini"


def get_default_model() -> str:
    return _model_name
