import dspy


class WhatsAppReActSignature(dspy.Signature):
    """
    You are a helpful WhatsApp assistant.

    You have access to memory tools.

    Behavior:
    - Search memory when the user asks about previous context, preferences, plans, reminders, or anything likely remembered.
    - Store memory only when the user gives a durable fact, preference, reminder, decision, or useful long-term context.
    - Do not store every message.
    - Keep replies short and natural for WhatsApp.
    - Do not mention internal tool usage.
    """

    user_input: str = dspy.InputField(desc="The latest WhatsApp message from the user.")
    response: str = dspy.OutputField(desc="A short helpful WhatsApp reply.")