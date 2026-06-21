# scripts/run_agent.py

import argparse
import asyncio
import logging

from app.agent.main import process_message

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("message", nargs="+")
    parser.add_argument(
        "--chat-id",
        default="local-dev-chat",
        help="Fake chat id for local agent testing",
    )
    args = parser.parse_args()

    text = " ".join(args.message)

    print(f"\nUSER: {text}\n")

    response = await process_message(
        chat_id=args.chat_id,
        text=text,
    )

    print(f"AGENT: {response}\n")


if __name__ == "__main__":
    asyncio.run(main())