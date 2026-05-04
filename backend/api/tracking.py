"""
Email Tracking API
------------------
Public endpoints (no auth required) for open pixel and click-through tracking.

Open pixel:  GET /api/track/open?token=<uuid4>
Click track: GET /api/track/click?token=<uuid4>&url=<encoded_destination>
"""

import os
from datetime import datetime
from urllib.parse import unquote

from fastapi import APIRouter, Query, Request, Response
from fastapi.responses import RedirectResponse

from db import email_opens_collection, email_events_collection

router = APIRouter()

# ── 1×1 transparent GIF (standard tracking pixel, 35 bytes) ──────────────────
PIXEL_GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00"
    b"!\xf9\x04\x00\x00\x00\x00\x00"
    b",\x00\x00\x00\x00\x01\x00\x01\x00\x00"
    b"\x02\x02D\x01\x00;"
)


def _no_cache_headers() -> dict:
    """Prevent email clients / proxies caching the pixel. Also bypass ngrok interstitial."""
    return {
        "Cache-Control": "no-store, no-cache, must-revalidate, proxy-revalidate",
        "Pragma":        "no-cache",
        "Expires":       "0",
        "ngrok-skip-browser-warning": "1",
    }


from services.scoring_service import ScoringService

async def _record_event(token: str, event_type: str, request: Request):
    """
    Persist one open/click event (dual-layer pattern):
      • email_opens  — summary document (upserted, fast counts)
      • email_events — individual event document (deep analytics)
    """
    now        = datetime.utcnow()
    ip         = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    # ── Summary layer (upsert) ────────────────────────────────────────────────
    open_inc   = 1 if event_type == "open"  else 0
    click_inc  = 1 if event_type == "click" else 0

    # Get existing record to check state and link to lead
    existing = await email_opens_collection.find_one({"token": token})
    
    set_fields = {}
    if event_type == "open":
        set_fields["last_opened_at"] = now
        if not existing or not existing.get("first_opened_at"):
            set_fields["first_opened_at"] = now
    else:
        # It's a click.
        set_fields["last_clicked_at"] = now
        if not existing or not existing.get("first_clicked_at"):
            set_fields["first_clicked_at"] = now
            
        # 💡 HEURISTIC: A click implies an open. 
        if not existing or existing.get("open_count", 0) == 0:
            open_inc = 1
            if not existing or not existing.get("first_opened_at"):
                set_fields["first_opened_at"] = now
            set_fields["last_opened_at"] = now

    open_update = {
        "$inc": {"open_count": open_inc, "click_count": click_inc},
        "$set": set_fields
    }
    await email_opens_collection.update_one(
        {"token": token},
        open_update,
        upsert=True,
    )

    # ── Event layer (insert) ──────────────────────────────────────────────────
    event_doc = {
        "token":      token,
        "event_type": event_type,
        "timestamp":  now,
        "ip_address": ip,
        "user_agent": user_agent,
    }
    
    # Link to lead if metadata exists in summary document
    if existing:
        lead_id = existing.get("lead_id")
        company_id = existing.get("company_id")
        if lead_id and company_id:
            event_doc["lead_id"] = lead_id
            event_doc["company_id"] = company_id
            
            # ── UPDATE INTENSITY SCORE ──
            if event_type == "open":
                await ScoringService.update_intensity_score(
                    lead_id=lead_id,
                    company_id=str(company_id),
                    signal_type="email_open",
                    weight=5,
                    description="Email opened by lead"
                )
            elif event_type == "click":
                await ScoringService.update_intensity_score(
                    lead_id=lead_id,
                    company_id=str(company_id),
                    signal_type="email_click",
                    weight=15,
                    description="Link clicked in email"
                )

    await email_events_collection.insert_one(event_doc)



# ── Open Pixel Endpoint ───────────────────────────────────────────────────────
@router.get("/open")
async def track_open(request: Request, token: str = Query(...)):
    """
    Returns a 1×1 transparent GIF and records the open event.
    Called automatically when the recipient's email client loads images.
    """
    await _record_event(token, "open", request)
    return Response(
        content=PIXEL_GIF,
        media_type="image/gif",
        headers=_no_cache_headers(),
    )


# ── Click Tracking Endpoint ───────────────────────────────────────────────────
@router.get("/click")
async def track_click(
    request: Request,
    token: str = Query(...),
    url:   str = Query(...),
):
    """
    Records a click event and 302-redirects to the original destination URL.
    Links inside tracked emails are rewritten to pass through this endpoint.
    """
    destination = unquote(url)

    # Basic safety — only allow http/https destinations
    if not destination.startswith(("http://", "https://")):
        return Response(content="Invalid redirect target", status_code=400)

    await _record_event(token, "click", request)
    return RedirectResponse(url=destination, status_code=302,
                            headers=_no_cache_headers())
