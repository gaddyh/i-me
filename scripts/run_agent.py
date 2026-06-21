import argparse
import asyncio
import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from app.agent.dspy_config import configure_dspy_once
from app.agent.single_turn_agent import WhatsAppSingleTurnAgent

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("message", nargs="+")
    parser.add_argument("--timezone", default="Asia/Jerusalem")
    args = parser.parse_args()

    text = " ".join(args.message)

    configure_dspy_once()

    now = datetime.now(ZoneInfo(args.timezone)).strftime("%Y-%m-%d %H:%M:%S")

    agent = WhatsAppSingleTurnAgent(max_steps=1)

    pred = await asyncio.to_thread(
        agent,
        user_input=text,
        now=now,
        timezone=args.timezone,
    )

    print("\nUSER:")
    print(text)

    print("\nSELECTED FN:")
    print(pred.selected_fn)

    print("\nARGS:")
    print(json.dumps(pred.args, ensure_ascii=False, indent=2))

    print("\nRESPONSE:")
    print(pred.response)

    print("\nTRAJECTORY:")
    print(json.dumps(pred.trajectory, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())