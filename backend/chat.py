import os
import logging

from openai import OpenAI

LOGGER = logging.getLogger("pegasus.chat")

SYSTEM_INSTRUCTION = """You are Pegasus, an AI study companion.
Your goal is to help students understand their course material, reflect on concepts, and prepare for exams.

Guidelines:
- Be encouraging and supportive.
- Use Socratic questioning to help the student find the answer themselves.
- Keep responses concise (under 3 paragraphs) unless asked for a detailed explanation.
- If the user asks about a specific lecture or course, use the provided context.
- Do not hallucinate facts. If the context doesn't have the answer, say so."""


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
        return response.choices[0].message.content
    except Exception as e:
        LOGGER.error(f"OpenAI Chat Error: {e}")
        return "I'm having trouble connecting right now. Please try again later."
