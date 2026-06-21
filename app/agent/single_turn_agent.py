import json
import logging
from typing import Any, Callable

import dspy

from app.agent.tool_metadata import (
    functions_metadata,
    wrap_function_with_timeout,
)
from app.agent.tools import AVAILABLE_FUNCTIONS

logger = logging.getLogger("greenapi-bot")


class ToolSelectionSignature(dspy.Signature):
    """
    You are a WhatsApp personal assistant.

    Decide the next function to call for this single user message.

    Domain:
    - Create reminders.
    - Ask clarification when required reminder fields are missing.
    - Finish when the user is greeting, asking what you can do, or not asking for an action.

    Required fields for create_reminder:
    - reminder_text
    - remind_date
    - remind_time

    Date/time rules:
    - Use `now` to resolve relative dates like today, tomorrow, Sunday.
    - Format dates as YYYY-MM-DD.
    - Format times as HH:MM, 24-hour time.
    - If date is missing, ask for date.
    - If time is missing, ask for time.
    - If reminder text is missing, ask what to remind.

    Function choice rules:
    - Use create_reminder only when all required fields are present or inferable.
    - Use ask_clarification when a reminder intent is clear but required fields are missing.
    - Use finish for non-reminder messages.

    Output rules:
    - next_selected_fn must be exactly one of the available function names.
    - args_json must be valid JSON.
    """

    user_input: str = dspy.InputField(desc="Latest WhatsApp message.")
    now: str = dspy.InputField(desc="Current local datetime, ISO-like string.")
    timezone: str = dspy.InputField(desc="User timezone.")
    trajectory_json: str = dspy.InputField(desc="Previous tool calls in this turn as JSON.")
    functions_json: str = dspy.InputField(desc="Available functions and schemas as JSON.")

    next_selected_fn: str = dspy.OutputField(desc="Function name to call next.")
    args_json: str = dspy.OutputField(desc="JSON object of arguments for the selected function.")


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
    ) -> dspy.Prediction:
        tools_json = functions_metadata(self.functions)
        trajectory: list[dict[str, Any]] = []
        fn_output: dict[str, Any] = {"return_value": ""}

        for _ in range(self.max_steps):
            pred = self.react(
                user_input=user_input,
                now=now,
                timezone=timezone,
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

            try:
                fn_output = wrap_function_with_timeout(
                    self.functions[selected_fn]
                )(**args)
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