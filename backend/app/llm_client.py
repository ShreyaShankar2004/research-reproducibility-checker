"""
LLM Client - wraps Groq API (free tier, fast Llama 3.3 70B / Llama 3.1 8B)
Get a free API key at https://console.groq.com/keys
"""
import os
import re
import json
from groq import AsyncGroq

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
MODEL_LARGE = "llama-3.3-70b-versatile"   # for reasoning-heavy tasks
MODEL_FAST = "llama-3.1-8b-instant"       # for quick extraction tasks

_client = None


def get_client() -> AsyncGroq:
    global _client
    if _client is None:
        if not GROQ_API_KEY:
            raise RuntimeError(
                "GROQ_API_KEY not set. Get a free key at https://console.groq.com/keys "
                "and set it in your .env file."
            )
        _client = AsyncGroq(api_key=GROQ_API_KEY)
    return _client


async def llm_call(prompt: str, system: str = "", model: str = MODEL_LARGE,
                    json_mode: bool = False, temperature: float = 0.2,
                    max_tokens: int | None = None) -> str:
    """Make a single LLM call with automatic retry on rate limit."""
    import asyncio
    client = get_client()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    kwargs = {}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    if max_tokens is None:
        max_tokens = 2000 if model == MODEL_FAST else 8000

    for attempt in range(3):
        try:
            resp = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            return resp.choices[0].message.content
        except Exception as e:
            error_str = str(e)
            if '429' in error_str and attempt < 2:
                wait = (attempt + 1) * 2
                await asyncio.sleep(wait)
                continue
            raise


async def llm_json_call(prompt: str, system: str = "", model: str = MODEL_LARGE,
                         temperature: float = 0.2, max_tokens: int | None = None) -> dict:
    """LLM call that returns parsed JSON. Robust to leading/trailing junk and retries on failure."""
    text = await llm_call(prompt, system=system, model=model,
                           json_mode=True, temperature=temperature, max_tokens=max_tokens)
    result = _try_parse_json(text)
    if result is not None:
        return result

    # Retry once without json_mode (some models echo content before JSON in strict mode)
    text = await llm_call(prompt, system=system, model=model,
                           json_mode=False, temperature=temperature, max_tokens=max_tokens)
    result = _try_parse_json(text)
    if result is not None:
        return result

    raise ValueError(f"LLM did not return valid JSON. Raw output: {text[:500]}")


def _try_parse_json(text: str) -> dict | None:
    """Try direct parse, then extract the outermost {...} block."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strip markdown fences
    cleaned = re.sub(r'^```(?:json)?\s*|\s*```$', '', text, flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Extract the last balanced {...} block (handles leading prose/echoed content)
    start = text.rfind('{')
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                candidate = text[start:i + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    next_start = text.rfind('{', 0, start)
                    if next_start == -1:
                        return None
                    start = next_start
                    depth = 0
    return None