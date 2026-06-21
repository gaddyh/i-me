import inspect
import json
import logging
from typing import Any, Callable

import dspy

from app.agent.signatures import ToolSelectionSignature
from app.agent.tool_metadata import functions_metadata
from app.agent.tools import AVAILABLE_FUNCTIONS

logger = logging.getLogger("greenapi-bot")


class WhatsAppSingleTurnAgent(dspy.Module):
    def __init__(
        self,
        functions: dict[str, Callable[..., dict[str, Any]]] | None = None,
        max_steps: int = 1,
    ):
        super().__init__()

        self.functions = functions or AVAILABLE_FUNCTIONS
        self.max_steps = max_steps
        self.react = dspy.ChainOfThought(ToolSelectionSignature)

    def forward(
        self,
        user_input: str,
        now: str,
        timezone: str = "Asia/Jerusalem",
        conversation_history: str = "[]",
        chat_id: str = "",
    ) -> dspy.Prediction:
        tools_json = functions_metadata(self.functions)
        trajectory: list[dict[str, Any]] = []
        fn_output: dict[str, Any] = {"return_value": ""}

        for _ in range(self.max_steps):
            pred = self.react(
                user_input=user_input,
                now=now,
                timezone=timezone,
                conversation_history=conversation_history,
                trajectory_json=json.dumps(trajectory, ensure_ascii=False),
                functions_json=tools_json,
            )

            selected_fn = clean_fn_name(pred.next_selected_fn)

            if selected_fn not in self.functions:
                selected_fn = "ask_clarification"
                args = {
                    "question": "I’m not sure what to do. Can you clarify?",
                    "missing_fields": ["intent"],
                }
            else:
                args = parse_args_json(pred.args_json)
                _inject_context(self.functions[selected_fn], args, chat_id=chat_id)

            try:
                fn_output = self.functions[selected_fn](**args)
            except TypeError as e:
                logger.exception("Tool args mismatch")
                selected_fn = "ask_clarification"
                args = {
                    "question": "I’m missing some details. Can you clarify?",
                    "missing_fields": ["tool_args"],
                }
                fn_output = self.functions[selected_fn](**args)

            trajectory.append(
                {
                    "reasoning": getattr(pred, "reasoning", ""),
                    "selected_fn": selected_fn,
                    "args": args,
                    "tool_output": fn_output,
                }
            )

        return dspy.Prediction(
            response=fn_output.get("return_value", ""),
            answer=fn_output.get("return_value", ""),
            selected_fn=trajectory[-1]["selected_fn"] if trajectory else "",
            args=trajectory[-1]["args"] if trajectory else {},
            trajectory=trajectory,
        )


def _inject_context(fn: Callable[..., Any], args: dict[str, Any], **context: Any) -> None:
    sig = inspect.signature(fn)
    for key, value in context.items():
        if key in sig.parameters and key not in args:
            args[key] = value


def clean_fn_name(value: str) -> str:
    return value.strip().strip('"').strip("'")


def parse_args_json(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    return {}