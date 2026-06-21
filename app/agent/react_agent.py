import dspy

from app.agent.signatures import WhatsAppReActSignature
from app.agent.tools import create_reminder

class WhatsAppReActAgent(dspy.Module):
    def __init__(self):
        super().__init__()

        self.react = dspy.ReAct(
            signature=WhatsAppReActSignature,
            tools=[create_reminder],
            max_iters=6,
        )

    def forward(self, user_input: str):
        return self.react(user_input=user_input)
