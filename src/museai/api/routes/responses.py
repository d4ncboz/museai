"""OpenAI Responses API (``/v1/responses``) — reserved.

TODO(contributors): map ``input`` / ``instructions`` onto ``flatten_messages``
and emit ``response.output_text.delta`` events from ``Gateway.chat_stream``.
"""

from fastapi import APIRouter, Depends

from ...errors import FeatureNotImplemented
from ..deps import require_api_key

router = APIRouter(tags=["responses"], dependencies=[Depends(require_api_key)])


@router.post("/v1/responses")
async def create_response() -> None:
    raise FeatureNotImplemented("/v1/responses is planned; use /v1/chat/completions for now")
