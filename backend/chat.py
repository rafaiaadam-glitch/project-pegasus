import os
import logging

from openai import OpenAI

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
    Generates a response from OpenAI for a chat message, given history and context.
    """
    model_name = os.getenv("PLC_CHAT_MODEL", os.getenv("PLC_LLM_MODEL", "gpt-4o-mini"))

    client = OpenAI()  # reads OPENAI_API_KEY from env

    # Build system message with optional context
    system_content = SYSTEM_INSTRUCTION
    if context:
        system_content += f"\n\nContext:\n{context}"

    # Build messages list
    messages = [{"role": "system", "content": system_content}]

    for msg in history:
        role = "user" if msg.get("isUser") else "assistant"
        messages.append({"role": role, "content": msg.get("text", "")})

    messages.append({"role": "user", "content": message})

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
        )
        if not response.choices:
            LOGGER.error("OpenAI returned empty choices list")
            return "I'm having trouble connecting right now. Please try again later."
        return response.choices[0].message.content or ""
    except Exception as e:
        LOGGER.error("OpenAI Chat Error: %s", e)
        return "I'm having trouble connecting right now. Please try again later."
