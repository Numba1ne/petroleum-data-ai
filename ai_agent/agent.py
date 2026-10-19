"""
Simple tool-calling agent for Volve field analytics.
Uses an OpenAI-compatible API (OpenRouter by default, OpenAI also works).
"""

import json
import os
from typing import Any, Dict, List, Optional

from ai_agent.prompts import SYSTEM_PROMPT
from ai_agent.tools import TOOL_REGISTRY

# Optional: load .env if present
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Defaults for OpenRouter + a free DeepSeek model. Override via env:
#   LLM_BASE_URL, LLM_API_KEY, LLM_MODEL
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "deepseek/deepseek-chat-v3.1:free"


def _client():
    """Create an OpenAI-compatible client (OpenRouter by default)."""
    from openai import OpenAI

    api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "No API key found. Set LLM_API_KEY (OpenRouter) or OPENAI_API_KEY "
            "in your environment or .env file."
        )
    base_url = os.getenv("LLM_BASE_URL", DEFAULT_BASE_URL)
    return OpenAI(api_key=api_key, base_url=base_url)


def _model_name(default: str = DEFAULT_MODEL) -> str:
    return os.getenv("LLM_MODEL", default)


def _tool_schemas() -> List[Dict]:
    """Convert TOOL_REGISTRY into OpenAI function schemas."""
    schemas = []
    for name, meta in TOOL_REGISTRY.items():
        props = {}
        required = []
        for param, desc in meta.get("parameters", {}).items():
            # Simple type inference from description
            if "int" in desc.lower():
                ptype = "integer"
            elif "bool" in desc.lower():
                ptype = "boolean"
            elif "list" in desc.lower():
                ptype = "array"
            else:
                ptype = "string"
            props[param] = {"type": ptype, "description": desc}
            if "optional" not in desc.lower() and "default" not in desc.lower():
                required.append(param)

        schemas.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": meta["description"],
                    "parameters": {
                        "type": "object",
                        "properties": props,
                        "required": required,
                    },
                },
            }
        )
    return schemas


def _execute_tool(name: str, arguments: Dict[str, Any]) -> str:
    """Run a tool and return JSON string result."""
    if name not in TOOL_REGISTRY:
        return json.dumps({"error": f"Unknown tool: {name}"})

    fn = TOOL_REGISTRY[name]["fn"]
    try:
        # Filter to valid kwargs
        import inspect

        sig = inspect.signature(fn)
        valid = {k: v for k, v in arguments.items() if k in sig.parameters}
        result = fn(**valid)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def chat(
    user_message: str,
    history: Optional[List[Dict]] = None,
    model: Optional[str] = None,
    max_tool_rounds: int = 5,
) -> str:
    """
    Send a user message, let the model call tools as needed, return final answer.
    """
    client = _client()
    model = model or _model_name()
    messages: List[Dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

    if history:
        messages.extend(history)

    messages.append({"role": "user", "content": user_message})

    tools = _tool_schemas()

    for _ in range(max_tool_rounds):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        msg = response.choices[0].message

        # No tool calls → final answer
        if not msg.tool_calls:
            return msg.content or ""

        # Append assistant message with tool calls
        messages.append(
            {
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ],
            }
        )

        # Execute each tool and append results
        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            result = _execute_tool(name, args)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                }
            )

    return (
        "Sorry — I reached the tool-call limit without a final answer. "
        "Please try a simpler question."
    )


def chat_with_history(
    user_message: str,
    history: Optional[List[Dict]] = None,
    model: Optional[str] = None,
) -> tuple:
    """
    Same as chat(), but also returns updated history for multi-turn use.
    History stores only user/assistant text turns (tool internals stay internal).
    """
    answer = chat(user_message, history=history, model=model)
    new_history = list(history or [])
    new_history.append({"role": "user", "content": user_message})
    new_history.append({"role": "assistant", "content": answer})
    return answer, new_history
