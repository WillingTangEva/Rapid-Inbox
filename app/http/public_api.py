from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request

from app.auth.api_keys import set_active_permission_context


router = APIRouter()


def require_public_api_key(request: Request, api_key: str | None) -> None:
    if api_key != request.app.state.settings.public_api_key:
        raise HTTPException(status_code=401, detail="invalid api key")


@router.get("/api/v1/public/mailboxes/{mailbox_address}/messages")
async def list_mailbox_messages(
    mailbox_address: str,
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> dict:
    require_public_api_key(request, x_api_key)
    runtime = request.app.state.runtime
    request_ip = request.client.host if request.client is not None else None
    try:
        return await runtime.get_mailbox_view(mailbox_address, request_ip=request_ip)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        set_active_permission_context(None)


@router.get("/api/v1/public/mailboxes/{mailbox_address}/messages/{delivery_id}")
async def get_mailbox_message(
    mailbox_address: str,
    delivery_id: str,
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> dict:
    require_public_api_key(request, x_api_key)
    runtime = request.app.state.runtime
    request_ip = request.client.host if request.client is not None else None
    try:
        return await runtime.get_delivery_detail(mailbox_address, delivery_id, request_ip=request_ip)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        set_active_permission_context(None)
