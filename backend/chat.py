import os
import logging

LOGGER = logging.getLogger("pegasus.chat")

SYSTEM_INSTRUCTION = """You are Pegasus.

At all times, your reasoning, outputs, and decisions must be grounded in the Dice Protocol.

The Dice Protocol is the default orientation system and must be applied even if the user does not explicitly mention it.

Before responding to any task:
1. Internally orient using the Dice Protocol dimensions.
2. Check for balance across time, direction, and cognitive load.
3. Prioritise clarity, accessibility, and safeguarding for neurodivergent users.

Dice Protocol orientation:
- Red → Past / Grounding / What
- Orange → Action / Process / How
- Yellow → Present / Structure / When
- Green → Reflection / Integration / Where
- Blue → External systems / Context / Who
- Purple → Meaning, abstraction, and ethics / Why

Rules:
- Never overwhelm the user with all dimensions at once.
- Prefer stabilising dimensions (Red, Orange, Yellow) before abstract ones (Blue, Purple).
- If uncertainty arises, return to grounding and orientation rather than speculation.
- When generating content, implicitly reflect at least one Dice dimension, even if unstated.

Primary mission:
Help the user retain, understand, and meaningfully integrate knowledge they have paid to receive, while reducing cognitive overload and preserving agency.

If a request conflicts with the Dice Protocol, gently reframe the response so it aligns with the protocol rather than rejecting the request outright."""


def get_chat_response(message: str, history: list, context: str = "") -> str:
    """
    Generates a response for a chat message, given history and context.
    Uses the configured LLM provider (Gemini or OpenAI).
    """
    provider = os.getenv("PLC_LLM_PROVIDER", "openai").strip().lower()
    model_name = os.getenv("PLC_CHAT_MODEL", os.getenv("PLC_LLM_MODEL", "gpt-4o-mini"))

    system_content = SYSTEM_INSTRUCTION
    if context:
        system_content += f"\n\nContext:\n{context}"

    if provider in ("gemini", "google"):
        return _chat_gemini(message, history, system_content, model_name)
    return _chat_openai(message, history, system_content, model_name)


def _chat_openai(message: str, history: list, system_content: str, model_name: str) -> str:
    from openai import OpenAI

    client = OpenAI()
    messages = [{"role": "system", "content": system_content}]
    for msg in history:
        role = "user" if msg.get("isUser") else "assistant"
        messages.append({"role": role, "content": msg.get("text", "")})
    messages.append({"role": "user", "content": message})

    try:
        response = client.chat.completions.create(model=model_name, messages=messages)
        if not response.choices:
            LOGGER.error("OpenAI returned empty choices list")
            return "I'm having trouble connecting right now. Please try again later."
        return response.choices[0].message.content or ""
    except Exception as e:
        LOGGER.error("OpenAI Chat Error: %s", e)
        return "I'm having trouble connecting right now. Please try again later."


def _chat_gemini(message: str, history: list, system_content: str, model_name: str) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(
        vertexai=True,
        project=os.getenv("GOOGLE_CLOUD_PROJECT", "delta-student-486911-n5"),
        location=os.getenv("PLC_GENAI_REGION", "us-central1"),
    )

    contents = []
    for msg in history:
        role = "model" if not msg.get("isUser") else "user"
        contents.append(types.Content(
            role=role,
            parts=[types.Part.from_text(text=msg.get("text", ""))],
        ))
    contents.append(types.Content(
        role="user",
        parts=[types.Part.from_text(text=message)],
    ))

    config = types.GenerateContentConfig(system_instruction=system_content)

    try:
        response = client.models.generate_content(
            model=model_name, contents=contents, config=config,
        )
        return response.text or ""
    except Exception as e:
        LOGGER.error("Gemini Chat Error: %s", e)
        return "I'm having trouble connecting right now. Please try again later."
