import logging

from fastapi import HTTPException, Request

from app.config import settings

logger = logging.getLogger("greenapi-bot")


def verify_green_api_authorization(request: Request) -> None:
    authorization = request.headers.get("authorization")

    if authorization != settings.expected_authorization_header:
        logger.warning("Rejected webhook with invalid Authorization header")
        raise HTTPException(status_code=403, detail="Invalid webhook authorization")