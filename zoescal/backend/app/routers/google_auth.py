from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from ..services import google_integration


router = APIRouter()


@router.get("/login")
def google_login():
    try:
        return RedirectResponse(google_integration.create_login_url(), status_code=302)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/callback")
async def google_callback(
    code: str | None = None, state: str | None = None, error: str | None = None
):
    if error:
        raise HTTPException(status_code=400, detail=f"Google OAuth failed: {error}")
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing OAuth code or state")
    try:
        tokens = await google_integration.exchange_code(code, state)
        await google_integration.sync_google_events()
        return {"ok": True, "connected": True, "expiry": tokens.get("expiry")}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/status")
def google_status():
    return google_integration.connection_status()


@router.delete("/revoke", status_code=204)
async def google_revoke():
    await google_integration.revoke_and_delete()
