import dspy


class WhatsAppReActSignature(dspy.Signature):
    """
    You are a helpful assistant inside a WhatsApp personal chat.


    Behavior:
    - Create reminders when the user asks to remember something, ask for any missing information (message text, date, time).
    """

    user_input: str = dspy.InputField(desc="The latest WhatsApp message from the user.")
    response: str = dspy.OutputField(desc="A short helpful WhatsApp reply.")