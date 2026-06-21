import logging

import dspy

from app.config import settings

logger = logging.getLogger("greenapi-bot")

_is_configured = False


def configure_dspy_once() -> None:
    global _is_configured

    if _is_configured:
        return

    logger.info("Configuring DSPy LM: %s", settings.dspy_model)

    lm = dspy.LM(model=settings.dspy_model)
    dspy.configure(lm=lm)

    _is_configured = True