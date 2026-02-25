"""
openai_client.py — Multi-Provider AI API Integration (Gemini-first)
=====================================================================
Auto-detects which provider is available:
  1. If GEMINI_API_KEY is set  → use Google Gemini (primary)
  2. If GROQ_API_KEY is set    → use Groq  (free, fast)
  3. If OPENAI_API_KEY is set  → use OpenAI
  4. Neither                   → returns error (no built-in fallback)

All token counts, timing, and cost come directly from the API response.
"""
import os
import re
import asyncio
from typing import Optional
from dotenv import load_dotenv

# ── Provider detection & client setup ──
_client = None
_provider: str = ""
_default_model: str = ""
_gemini_model = None

# ── Multi-key rotation state ──
# Tracks which Gemini API keys are currently quota-exhausted this session
_exhausted_keys: set = set()


def _reload_env():
    """Re-read backend/.env so new keys are picked up without server restart."""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path, override=True)


def _get_all_gemini_keys() -> list[str]:
    """
    Collect every Gemini API key defined in the environment.
    Reads: GEMINI_API_KEY, GEMINI_API_KEY_2, GEMINI_API_KEY_3 … GEMINI_API_KEY_10
    Returns only non-empty, non-exhausted keys.
    """
    _reload_env()  # hot-reload .env on every call
    candidates = []
    # Primary key
    k = os.getenv("GEMINI_API_KEY", "").strip()
    if k:
        candidates.append(k)
    # Extra keys
    for i in range(2, 11):
        k = os.getenv(f"GEMINI_API_KEY_{i}", "").strip()
        if k:
            candidates.append(k)
    # Return non-exhausted keys first, exhausted ones last as a final retry
    active = [k for k in candidates if k not in _exhausted_keys]
    fallbacks = [k for k in candidates if k in _exhausted_keys]
    return active + fallbacks


def _detect_provider() -> tuple[str, str, Optional[str], str]:
    """Detect available provider. Returns (provider, api_key, base_url, default_model)."""
    _reload_env()  # hot-reload .env to pick up any new keys
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    openrouter_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()

    if gemini_key:
        return ("gemini", gemini_key, None, "gemini-2.0-flash")
    if groq_key:
        return ("groq", groq_key,
                "https://api.groq.com/openai/v1",
                "llama-3.3-70b-versatile")
    if openrouter_key:
        return ("openrouter", openrouter_key,
                "https://openrouter.ai/api/v1",
                "openrouter/auto")
    if openai_key:
        return ("openai", openai_key, None, "gpt-4o-mini")

    # No API key
    return ("none", "", None, "")


def _get_client():
    """Lazy-init the API client for the detected provider."""
    global _client, _provider, _default_model, _gemini_model
    if _client is None:
        provider, api_key, base_url, default_model = _detect_provider()
        _provider = provider
        _default_model = default_model

        if provider == "gemini":
            _client = True  # sentinel — Gemini uses REST API via httpx
            print(f"[openai_client] ✅ Using provider: GEMINI | model: {_default_model}")
        elif provider == "none":
            _client = True  # sentinel
            print("[openai_client] ❌ No API key found!")
            print("[openai_client]    Add GEMINI_API_KEY to backend/.env")
        else:
            from openai import AsyncOpenAI
            kwargs = {"api_key": api_key}
            if base_url:
                kwargs["base_url"] = base_url
            _client = AsyncOpenAI(**kwargs)
            print(f"[openai_client] Using provider: {_provider} | model: {_default_model}")
    return _client


def get_provider() -> str:
    if not _provider:
        _get_client()
    return _provider


def get_default_model() -> str:
    if not _default_model:
        _get_client()
    return _default_model


# ── Frontend model name → actual API model mapping ──
MODEL_MAP = {
    "gemini-flash": "gemini-2.0-flash",
    "gemini-pro": "gemini-2.5-pro",
    "sambanova": "DeepSeek-R1-Distill-Llama-70B",
    "openrouter": None,             # resolved dynamically via OPENROUTER_MODEL env
    "gpt-placeholder": None,       # placeholder — will error
    "local": None,                  # no local model
}

# ── Model pricing (per token) ──
# Market-rate / equivalent pricing so users always see meaningful cost.
# Even free-tier APIs have a real compute cost — these reflect published rates.
MODEL_PRICING = {
    # Google Gemini — pay-as-you-go published rates (per token)
    "gemini-2.0-flash":            {"input": 0.10 / 1_000_000, "output": 0.40 / 1_000_000},
    "gemini-2.5-flash":            {"input": 0.15 / 1_000_000, "output": 0.60 / 1_000_000},
    "gemini-2.5-flash-lite":       {"input": 0.075 / 1_000_000, "output": 0.30 / 1_000_000},
    "gemini-2.5-pro":              {"input": 1.25 / 1_000_000, "output": 10.00 / 1_000_000},
    "gemini-2.0-flash-001":        {"input": 0.10 / 1_000_000, "output": 0.40 / 1_000_000},
    "gemini-2.0-flash-lite":       {"input": 0.075 / 1_000_000, "output": 0.30 / 1_000_000},
    "gemini-1.5-flash":            {"input": 0.075 / 1_000_000, "output": 0.30 / 1_000_000},
    "gemini-1.5-pro":              {"input": 1.25 / 1_000_000, "output": 5.00 / 1_000_000},
    # OpenAI
    "gpt-4o":        {"input": 2.50 / 1_000_000, "output": 10.00 / 1_000_000},
    "gpt-4o-mini":   {"input": 0.15 / 1_000_000, "output": 0.60  / 1_000_000},
    "gpt-3.5-turbo": {"input": 0.50 / 1_000_000, "output": 1.50  / 1_000_000},
    # Groq — free tier, but equivalent market rate shown
    "llama-3.3-70b-versatile": {"input": 0.59 / 1_000_000, "output": 0.79 / 1_000_000},
    "llama-3.1-8b-instant":    {"input": 0.05 / 1_000_000, "output": 0.08 / 1_000_000},
    "mixtral-8x7b-32768":      {"input": 0.24 / 1_000_000, "output": 0.24 / 1_000_000},
    "gemma2-9b-it":            {"input": 0.20 / 1_000_000, "output": 0.20 / 1_000_000},
    # SambaNova — DeepSeek R1 equivalent pricing
    "DeepSeek-R1-Distill-Llama-70B": {"input": 0.55 / 1_000_000, "output": 2.19 / 1_000_000},
    # OpenRouter models — equivalent market rate
    "deepseek/deepseek-chat:free":          {"input": 0.27 / 1_000_000, "output": 1.10 / 1_000_000},
    "deepseek/deepseek-r1:free":            {"input": 0.55 / 1_000_000, "output": 2.19 / 1_000_000},
    "openrouter/auto":                      {"input": 0.15 / 1_000_000, "output": 0.60 / 1_000_000},
    "meta-llama/llama-4-maverick:free":      {"input": 0.20 / 1_000_000, "output": 0.30 / 1_000_000},
}


def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    pricing = MODEL_PRICING.get(model, {"input": 0.0, "output": 0.0})
    return (prompt_tokens * pricing["input"]) + (completion_tokens * pricing["output"])


# NOTE: _count_tokens() was removed — all token counts come from API responses only.


async def _try_fallback_provider(
    query: str,
    max_tokens: int,
    temperature: float,
    system_prompt: str,
) -> Optional[dict]:
    """
    Called when Gemini fails/quota exhausted.
    Attempts GROQ first, then OpenAI, returns result dict or None.
    """
    from openai import AsyncOpenAI

    sys_msg = system_prompt or (
        "You are a highly knowledgeable AI assistant. "
        "Give clear, accurate, detailed, well-structured answers. "
        "Use markdown formatting: ## headers, **bold**, bullet points, "
        "numbered lists, code blocks with language tags. Be comprehensive and precise."
    )
    messages = [
        {"role": "system", "content": sys_msg},
        {"role": "user", "content": query},
    ]

    providers_to_try = []
    sambanova_key = os.getenv("SAMBANOVA_API_KEY", "").strip()
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    openrouter_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()

    if sambanova_key:
        providers_to_try.append(("sambanova", sambanova_key, "https://api.sambanova.ai/v1", "DeepSeek-R1-Distill-Llama-70B"))
    if openrouter_key:
        or_model = os.getenv("OPENROUTER_MODEL", "openrouter/auto").strip()
        providers_to_try.append(("openrouter", openrouter_key, "https://openrouter.ai/api/v1", or_model))
    if groq_key:
        providers_to_try.append(("groq", groq_key, "https://api.groq.com/openai/v1", "llama-3.3-70b-versatile"))
    if openai_key:
        providers_to_try.append(("openai", openai_key, None, "gpt-4o-mini"))

    for (prov, key, base_url, model) in providers_to_try:
        try:
            kwargs = {"api_key": key}
            if base_url:
                kwargs["base_url"] = base_url
            client = AsyncOpenAI(**kwargs)
            print(f"[openai_client] ↩ Gemini quota exhausted — falling back to {prov.upper()} ({model})")
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            usage = response.usage
            prompt_tokens = usage.prompt_tokens
            completion_tokens = usage.completion_tokens
            total_tokens = usage.total_tokens
            actual_model = response.model or model
            cost = calculate_cost(actual_model, prompt_tokens, completion_tokens)
            print(f"[openai_client] ✅ Fallback success via {prov.upper()} ({actual_model})")
            return {
                "content": response.choices[0].message.content,
                "model": actual_model,
                "provider": prov,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "thinking_tokens": 0,
                "cost": cost,
            }
        except Exception as e:
            print(f"[openai_client] ⚠ Fallback {prov} failed: {e}")
            continue

    return None


# ═══════════════════════════════════════════════════
# SAMBANOVA — DeepSeek-R1 via OpenAI-compatible API
# ═══════════════════════════════════════════════════

async def _sambanova_chat(
    query: str,
    max_tokens: int = 2048,
    temperature: float = 0.7,
    system_prompt: str = "",
) -> dict:
    """Call SambaNova's OpenAI-compatible endpoint for DeepSeek-R1."""
    from openai import AsyncOpenAI
    import time as _time

    _reload_env()
    api_key = os.getenv("SAMBANOVA_API_KEY", "").strip()
    if not api_key:
        raise Exception(
            "SAMBANOVA_API_KEY is not set in backend/.env. "
            "Get a free key at https://cloud.sambanova.ai"
        )

    model = "DeepSeek-R1-Distill-Llama-70B"
    sys_msg = system_prompt or (
        "You are a highly knowledgeable AI assistant. "
        "Give clear, accurate, detailed, well-structured answers. "
        "Use markdown formatting: ## headers, **bold**, bullet points, "
        "numbered lists, code blocks with language tags. Be comprehensive and precise."
    )

    messages = [
        {"role": "system", "content": sys_msg},
        {"role": "user", "content": query},
    ]

    client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://api.sambanova.ai/v1",
    )

    start = _time.time()
    print(f"[openai_client] 🧠 Calling SambaNova — {model}")

    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        stream=False,
    )

    elapsed = _time.time() - start

    usage = response.usage
    prompt_tokens = usage.prompt_tokens if usage else 0
    completion_tokens = usage.completion_tokens if usage else 0
    total_tokens_api = usage.total_tokens if usage else 0

    # SAFETY: warn if usage data is missing
    if not usage:
        print("[openai_client] ⚠ WARNING: Token usage not returned by API")

    actual_model = response.model or model
    raw_content = response.choices[0].message.content or ""

    # Strip <think>...</think> reasoning from visible response
    import re as _re
    content = _re.sub(r"<think>.*?</think>\s*", "", raw_content, flags=_re.DOTALL).strip()

    # Check if API provides reasoning_tokens breakdown (some DeepSeek APIs do)
    thinking_tokens = 0
    if hasattr(usage, 'completion_tokens_details') and usage.completion_tokens_details:
        thinking_tokens = getattr(usage.completion_tokens_details, 'reasoning_tokens', 0) or 0

    # Use API values directly — accurate and authoritative
    total_tokens = total_tokens_api or (prompt_tokens + completion_tokens)

    cost = calculate_cost(actual_model, prompt_tokens, completion_tokens)

    print(f"[openai_client] ✅ SambaNova {actual_model} — "
          f"prompt: {prompt_tokens}, completion: {completion_tokens}, "
          f"thinking: {thinking_tokens}, total: {total_tokens} in {elapsed:.2f}s")

    return {
        "content": content,
        "model": actual_model,
        "provider": "sambanova",
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "thinking_tokens": thinking_tokens,
        "cost": cost,
    }


# ═══════════════════════════════════════════════════
# OPENROUTER — Configurable model via OpenRouter API
# ═══════════════════════════════════════════════════

async def _openrouter_chat(
    query: str,
    max_tokens: int = 2048,
    temperature: float = 0.7,
    system_prompt: str = "",
) -> dict:
    """
    Call OpenRouter's OpenAI-compatible endpoint.

    Model is configurable via OPENROUTER_MODEL env var.
    Defaults to openrouter/auto (safe, always-available model).
    Falls back to openrouter/auto on 404 model errors.
    Token usage is read directly from the API response — no estimation.
    """
    from openai import AsyncOpenAI
    import time as _time

    _reload_env()
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise Exception(
            "OPENROUTER_API_KEY is not set in backend/.env. "
            "Get a free key at https://openrouter.ai/keys"
        )

    # ── Model is loaded from env — never hardcoded ──
    # Default: openrouter/auto (always available, auto-routes to best model)
    # DeepSeek models can be set via OPENROUTER_MODEL env var when available
    model = os.getenv("OPENROUTER_MODEL", "openrouter/auto").strip()

    # ── Model fallback list: openrouter/auto is the guaranteed safe fallback ──
    OPENROUTER_FALLBACKS = [model]
    if "openrouter/auto" not in OPENROUTER_FALLBACKS:
        OPENROUTER_FALLBACKS.append("openrouter/auto")

    sys_msg = system_prompt or (
        "You are a highly knowledgeable AI assistant. "
        "Give clear, accurate, detailed, well-structured answers. "
        "Use markdown formatting: ## headers, **bold**, bullet points, "
        "numbered lists, code blocks with language tags. Be comprehensive and precise."
    )

    messages = [
        {"role": "system", "content": sys_msg},
        {"role": "user", "content": query},
    ]

    client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
    )

    # ── Try each model in fallback list; handle 404 model errors ──
    last_error = None
    for try_model in OPENROUTER_FALLBACKS:
        start = _time.time()
        print(f"[openai_client] 🌐 Calling OpenRouter — {try_model}")

        try:
            response = await client.chat.completions.create(
                model=try_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=False,
            )
        except Exception as e:
            error_str = str(e)
            # ── Handle 404 model not found — try next model in fallback list ──
            if "404" in error_str or "not_found" in error_str.lower() or "invalid model" in error_str.lower():
                print(f"[openai_client] ⚠ Model not found, switching to fallback model. ('{try_model}' → 404)")
                last_error = f"Model '{try_model}' not found (404)"
                continue
            raise  # re-raise non-404 errors

        elapsed = _time.time() - start

        # ── Parse REAL token usage from OpenRouter API response ──
        # OpenRouter returns standard OpenAI-compatible usage object:
        #   usage.prompt_tokens     → Input Tokens  (prompt_tokens)
        #   usage.completion_tokens → Output Tokens  (completion_tokens)
        #   usage.total_tokens      → Total Tokens   (total_tokens)
        usage = response.usage

        if usage:
            prompt_tokens = getattr(usage, 'prompt_tokens', 0) or 0
            completion_tokens = getattr(usage, 'completion_tokens', 0) or 0
            total_tokens_api = getattr(usage, 'total_tokens', 0) or 0
        else:
            # ── SAFETY: Token usage not returned by API — log warning, show 0 ──
            print("[openai_client] ⚠ WARNING: Token usage not returned by API")
            prompt_tokens = 0
            completion_tokens = 0
            total_tokens_api = 0

        # Derive total: total_tokens = prompt_tokens + completion_tokens
        total_tokens = total_tokens_api or (prompt_tokens + completion_tokens)

        actual_model = response.model or try_model
        raw_content = response.choices[0].message.content or ""

        # Strip <think>...</think> reasoning tags if present (some models emit these)
        import re as _re
        content = _re.sub(r"<think>.*?</think>\s*", "", raw_content, flags=_re.DOTALL).strip()

        # Check for reasoning/thinking tokens breakdown
        thinking_tokens = 0
        if usage and hasattr(usage, 'completion_tokens_details') and usage.completion_tokens_details:
            thinking_tokens = getattr(usage.completion_tokens_details, 'reasoning_tokens', 0) or 0

        cost = calculate_cost(actual_model, prompt_tokens, completion_tokens)

        print(f"[openai_client] ✅ OpenRouter {actual_model} — "
              f"prompt: {prompt_tokens}, completion: {completion_tokens}, "
              f"thinking: {thinking_tokens}, total: {total_tokens} in {elapsed:.2f}s")

        return {
            "content": content,
            "model": actual_model,
            "provider": "openrouter",
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "thinking_tokens": thinking_tokens,
            "cost": cost,
        }

    # All fallback models failed
    raise Exception(
        f"All OpenRouter models failed. Last error: {last_error}. "
        f"Check OPENROUTER_MODEL in backend/.env or use openrouter/auto"
    )


# ═══════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════

async def chat_completion(
    query: str,
    model: str = None,
    max_tokens: int = 2048,
    temperature: float = 0.7,
    system_prompt: str = "",
) -> dict:
    """
    Send a request to the best available provider.

    Returns:
        {
            "content": str,
            "model": str,
            "provider": str,          # "gemini", "groq", or "openai"
            "prompt_tokens": int,
            "completion_tokens": int,
            "total_tokens": int,
            "cost": float,
        }

    Raises Exception if no provider is available or API fails.
    """
    _get_client()  # ensure provider is detected

    # ── SambaNova provider — direct route regardless of detected provider ──
    if model == "sambanova":
        return await _sambanova_chat(query, max_tokens, temperature, system_prompt)

    # ── OpenRouter provider — direct route regardless of detected provider ──
    if model == "openrouter":
        return await _openrouter_chat(query, max_tokens, temperature, system_prompt)

    # ── No API key at all ──
    if _provider == "none":
        raise Exception(
            "No API key configured. Add GEMINI_API_KEY to backend/.env file. "
            "Get a free key at https://aistudio.google.com/app/apikey"
        )

    # ── Resolve frontend model name to actual API model ──
    resolved_model = None
    if model:
        resolved_model = MODEL_MAP.get(model)
        if model in ("local", "gpt-placeholder") and not resolved_model:
            raise Exception(
                f"Model '{model}' is not available. Please select Gemini Flash or Gemini Pro."
            )

    # ── Gemini provider (REST via httpx) ──
    if _provider == "gemini":
        import time as _time
        import httpx
        import json as _json

        # ── Collect all Gemini keys (supports rotation) ──
        all_keys = _get_all_gemini_keys()
        if not all_keys:
            raise Exception("GEMINI_API_KEY is not set in backend/.env")

        start_time = _time.time()

        # Use resolved model as primary, then fall back to reliable models
        if resolved_model:
            GEMINI_FALLBACKS = [resolved_model, "gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.0-flash-lite", "gemini-2.5-flash-lite", "gemini-2.0-flash-001"]
        else:
            GEMINI_FALLBACKS = ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.0-flash-lite", "gemini-2.5-flash-lite", "gemini-2.0-flash-001"]

        # De-duplicate while preserving order
        seen = set()
        unique_fallbacks = []
        for m in GEMINI_FALLBACKS:
            if m not in seen:
                seen.add(m)
                unique_fallbacks.append(m)
        GEMINI_FALLBACKS = unique_fallbacks

        system_instruction = system_prompt or (
            "You are an expert AI assistant. "
            "Always give accurate, complete, and well-structured answers. "
            "Use markdown: ## headers, **bold**, bullet lists, numbered steps, "
            "and code blocks with language tags where relevant. "
            "Never make up facts. Be precise and helpful."
        )

        payload = {
            "system_instruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"role": "user", "parts": [{"text": query}]}],
            "generationConfig": {
                "temperature": temperature,
                "topP": 0.95,
                "maxOutputTokens": max_tokens,
            },
        }

        content = None
        used_model = GEMINI_FALLBACKS[0]
        prompt_tokens = 0
        completion_tokens = 0
        total_from_api = 0
        last_error = None
        all_keys_exhausted = False

        async with httpx.AsyncClient(timeout=60.0, verify=False) as client:
            # ── Outer loop: rotate through API keys ──
            for api_key in all_keys:
                key_quota_exhausted = False

                # ── Inner loop: try each model with this key ──
                for fallback_model in GEMINI_FALLBACKS:
                    if key_quota_exhausted:
                        break

                    url = (
                        f"https://generativelanguage.googleapis.com/v1beta/models/"
                        f"{fallback_model}:generateContent?key={api_key}"
                    )

                    # Try up to 3 attempts per model with exponential backoff on rate limit
                    for attempt in range(3):
                        try:
                            resp = await client.post(url, json=payload)

                            if resp.status_code == 429:
                                resp_text = resp.text
                                if "limit: 0" in resp_text or "quota" in resp_text.lower():
                                    key_short = api_key[:12] + "..."
                                    print(f"[openai_client] ❌ Key {key_short} quota exhausted — rotating to next key")
                                    _exhausted_keys.add(api_key)
                                    last_error = "API key quota exhausted."
                                    key_quota_exhausted = True
                                    break
                                if attempt < 2:
                                    wait_time = (attempt + 1) * 5
                                    print(f"[openai_client] ⚠ {fallback_model} rate limited — waiting {wait_time}s (attempt {attempt+1}/3)")
                                    await asyncio.sleep(wait_time)
                                    continue
                                else:
                                    print(f"[openai_client] ⚠ {fallback_model} rate limited after 3 attempts — trying next model")
                                    last_error = f"{fallback_model} rate limited (429)"
                                    break

                            if resp.status_code != 200:
                                error_body = resp.text[:300]
                                print(f"[openai_client] ⚠ {fallback_model} error {resp.status_code}: {error_body}")
                                last_error = f"{fallback_model} returned HTTP {resp.status_code}: {error_body}"
                                break

                            data = resp.json()

                            cands = data.get("candidates", [])
                            if not cands:
                                print(f"[openai_client] ⚠ {fallback_model} returned no candidates")
                                last_error = f"{fallback_model} returned no candidates"
                                break

                            parts = cands[0].get("content", {}).get("parts", [])
                            if not parts or "text" not in parts[0]:
                                print(f"[openai_client] ⚠ {fallback_model} returned no text content")
                                last_error = f"{fallback_model} returned no text content"
                                break

                            content = parts[0]["text"]
                            used_model = fallback_model

                            # ── Parse REAL token counts from Gemini usageMetadata ──
                            # Keys: promptTokenCount, candidatesTokenCount, totalTokenCount
                            usage_meta = data.get("usageMetadata", {})
                            print(f"[openai_client] 🔍 RAW usageMetadata: {usage_meta}")
                            prompt_tokens = int(usage_meta.get("promptTokenCount", 0) or 0)
                            completion_tokens = int(usage_meta.get("candidatesTokenCount", 0) or 0)
                            total_from_api = int(usage_meta.get("totalTokenCount", 0) or 0)

                            # SAFETY: warn if usage data is missing
                            if not usage_meta:
                                print("[openai_client] ⚠ WARNING: Token usage not returned by API")

                            # Fallback: if API omitted any field, derive from others
                            if not total_from_api and (prompt_tokens or completion_tokens):
                                total_from_api = prompt_tokens + completion_tokens
                            if not prompt_tokens and not completion_tokens and total_from_api:
                                # Can't split — leave both zero, total is still accurate
                                pass

                            key_short = api_key[:12] + "..."
                            print(f"[openai_client] ✅ Success with {fallback_model} (key: {key_short})")
                            break

                        except httpx.TimeoutException:
                            last_error = f"{fallback_model} timed out"
                            print(f"[openai_client] ⚠ {fallback_model} timed out — trying next")
                            break
                        except httpx.HTTPStatusError as e:
                            last_error = f"{fallback_model} HTTP error: {e}"
                            print(f"[openai_client] ⚠ {fallback_model} error {e.response.status_code} — trying next")
                            break
                        except Exception as e:
                            last_error = f"{fallback_model} exception: {e}"
                            print(f"[openai_client] ⚠ {fallback_model} exception: {e} — trying next")
                            break

                    if content is not None:
                        break

                if content is not None:
                    break

            all_keys_exhausted = len(_exhausted_keys) >= len(all_keys)

        if content is None:
            # ── Auto-fallback to GROQ or OpenAI when all Gemini keys fail ──
            fallback_result = await _try_fallback_provider(
                query, max_tokens, temperature, system_prompt
            )
            if fallback_result:
                return fallback_result

            if all_keys_exhausted:
                raise Exception(
                    f"All {len(all_keys)} Gemini API key(s) have exhausted their quota. "
                    "Fix: Add GEMINI_API_KEY_2=<new_key> to backend/.env (keys rotate automatically). "
                    "Or add GROQ_API_KEY (free at https://console.groq.com) as an instant fallback."
                )
            raise Exception(
                f"All Gemini models failed. Last error: {last_error}. "
                "Check your GEMINI_API_KEY in backend/.env or try again."
            )

        elapsed = _time.time() - start_time
        total_tokens = total_from_api if total_from_api else (prompt_tokens + completion_tokens)
        cost = calculate_cost(used_model, prompt_tokens, completion_tokens)

        print(f"[openai_client] ✅ Gemini REST via {used_model} — "
              f"prompt: {prompt_tokens}, completion: {completion_tokens}, "
              f"total: {total_tokens} in {elapsed:.2f}s")

        return {
            "content": content,
            "model": used_model,
            "provider": "gemini",
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "thinking_tokens": 0,
            "cost": cost,
        }

    # ── API providers (Groq / OpenAI) ──
    from openai import AsyncOpenAI
    use_model = resolved_model or _default_model

    sys_msg = system_prompt or (
        "You are a highly knowledgeable AI assistant. "
        "Give clear, accurate, detailed, well-structured answers. "
        "Use markdown formatting: ## headers, ### subheaders, **bold**, "
        "bullet points, numbered lists, code blocks with language tags. "
        "Be comprehensive and precise."
    )

    messages = [
        {"role": "system", "content": sys_msg},
        {"role": "user", "content": query},
    ]

    response = await _client.chat.completions.create(
        model=use_model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )

    # ── Parse token usage safely (handles missing data gracefully) ──
    usage = response.usage
    if usage:
        prompt_tokens = getattr(usage, 'prompt_tokens', 0) or 0
        completion_tokens = getattr(usage, 'completion_tokens', 0) or 0
        total_tokens_api = getattr(usage, 'total_tokens', 0) or 0
    else:
        # SAFETY: Token usage not returned by API — log warning, show 0
        print("[openai_client] ⚠ WARNING: Token usage not returned by API")
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens_api = 0
    # Derive total: total_tokens = prompt_tokens + completion_tokens
    total_tokens = total_tokens_api or (prompt_tokens + completion_tokens)
    actual_model = response.model or use_model
    cost = calculate_cost(actual_model, prompt_tokens, completion_tokens)

    return {
        "content": response.choices[0].message.content,
        "model": actual_model,
        "provider": _provider,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "thinking_tokens": 0,
        "cost": cost,
    }
