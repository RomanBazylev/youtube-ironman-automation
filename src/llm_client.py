import requests

from config.settings import GROQ_API_KEY, GROQ_MODEL, OPENAI_API_KEY, OPENAI_MODEL


def _chat_with_openai(system_prompt: str, user_prompt: str, temperature: float) -> str:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": OPENAI_MODEL,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def _chat_with_groq(system_prompt: str, user_prompt: str, temperature: float) -> str:
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not configured")

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": GROQ_MODEL,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def chat_json(system_prompt: str, user_prompt: str, temperature: float = 0.8) -> str:
    # Prefer Groq for speed and lower cost in CI, fallback to OpenAI.
    if GROQ_API_KEY:
        return _chat_with_groq(system_prompt, user_prompt, temperature)
    return _chat_with_openai(system_prompt, user_prompt, temperature)
