import dspy


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
    conversation_history: str = dspy.InputField(
        desc="Recent conversation turns as a JSON array of {role, content} objects. Empty array if none."
    )
    trajectory_json: str = dspy.InputField(desc="Previous tool calls in this turn as JSON.")
    functions_json: str = dspy.InputField(desc="Available functions and schemas as JSON.")

    next_selected_fn: str = dspy.OutputField(desc="Function name to call next.")
    args_json: str = dspy.OutputField(desc="JSON object of arguments for the selected function.")