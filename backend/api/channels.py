"""
Phase 6 — Multi-Channel Outreach API (Redesigned)
Pattern: AI auto-generates personalized drafts for all leads → admin reviews queue → bulk approve → Twilio sends

Endpoints:
  POST /api/channels/generate-queue   → AI drafts personalized SMS/WhatsApp/Voice for all leads
  GET  /api/channels/queue            → List pending drafts in queue
  POST /api/channels/approve          → Bulk approve + send selected items
  DELETE /api/channels/queue/{id}     → Discard a draft
  GET  /api/channels/settings         → Get Twilio config
  POST /api/channels/settings         → Save Twilio config
  GET  /api/channels/logs             → Sent outreach history
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
import os, uuid, json as _json

from bson import ObjectId
from db import (
    channel_settings_collection,
    leads_collection,
    agent_activity_collection,
    companies_collection,
    database,
)
from dependencies import get_current_user

router = APIRouter()

# Lazy collection for outreach queue
outreach_queue_col = database.get_collection("outreach_queue")

DEFAULT_FALLBACK_PHONE = "+917777039470"


# ── Pydantic ──────────────────────────────────────────────────────────────────

class ChannelSettings(BaseModel):
    twilio_account_sid:          Optional[str]  = None
    twilio_auth_token:           Optional[str]  = None
    twilio_phone_number:         Optional[str]  = None   # E.164 e.g. +15551234567
    twilio_whatsapp_number:      Optional[str]  = None   # e.g. whatsapp:+14155238886
    sms_prompt:                  Optional[str]  = None
    whatsapp_prompt:             Optional[str]  = None
    sms_template_blocks:         Optional[List[dict]] = None   # Block-based SMS message template
    whatsapp_template_blocks:    Optional[List[dict]] = None   # Block-based WhatsApp message template


class GenerateQueuePayload(BaseModel):
    channel: str = "sms"          # sms | whatsapp | voice
    lead_ids: Optional[List[str]] = None   # None = all leads
    template_hint: Optional[str] = None   # optional context for the AI


class ApprovePayload(BaseModel):
    item_ids: List[str]           # outreach_queue _id strings


# ── Twilio send helpers ────────────────────────────────────────────────────────

async def _get_twilio_cfg(company_id: str) -> dict:
    from db import companies_collection
    cfg = await channel_settings_collection.find_one({
        "$or": [
            {"company_id": company_id},
            {"company_id": str(company_id)}
        ]
    })
    if not cfg:
        cfg = {}
        
    # Twilio keys are often saved globally in the company settings
    comp = await companies_collection.find_one({
        "$or": [
            {"company_id": company_id},
            {"company_id": str(company_id)}
        ]
    })
    
    if comp and comp.get("settings"):
        for key in ["twilio_account_sid", "twilio_auth_token", "twilio_phone_number", "twilio_whatsapp_number"]:
            if comp["settings"].get(key):
                cfg[key] = comp["settings"][key]
                
    if not cfg:
        raise HTTPException(404, "Twilio not configured — go to Settings → Twilio")
    return cfg


async def _send_sms(cfg: dict, to_phone: str, body: str) -> str:
    try:
        from twilio.rest import Client
        client = Client(cfg["twilio_account_sid"], cfg["twilio_auth_token"])
        clean_phone = to_phone.replace(" ", "").replace("-", "")
        if len(clean_phone) == 10 and clean_phone.isdigit():
            clean_phone = f"+91{clean_phone}"
        elif not clean_phone.startswith("+"):
            clean_phone = f"+{clean_phone}"
        msg = client.messages.create(body=body, from_=cfg["twilio_phone_number"], to=clean_phone)
        return f"{msg.sid} (to {clean_phone})"
    except ImportError:
        return f"SIMULATED_SID_{uuid.uuid4().hex[:8]}"


async def _send_whatsapp(cfg: dict, to_phone: str, body: str) -> str:
    try:
        from twilio.rest import Client
        client = Client(cfg["twilio_account_sid"], cfg["twilio_auth_token"])
        wa_from = cfg.get("twilio_whatsapp_number") or f"whatsapp:{cfg['twilio_phone_number']}"
        if not wa_from.startswith("whatsapp:"):
            wa_from = f"whatsapp:{wa_from}"
            
        # Sandbox Override: Force all WhatsApp messages to the verified default receiver
        to_phone = DEFAULT_FALLBACK_PHONE
            
        clean_phone = to_phone.replace(" ", "").replace("-", "")
        if len(clean_phone) == 10 and clean_phone.isdigit():
            clean_phone = f"+91{clean_phone}"
        elif not clean_phone.startswith("+"):
            clean_phone = f"+{clean_phone}"
            
        to = f"whatsapp:{clean_phone}" if not clean_phone.startswith("whatsapp:") else clean_phone
        msg = client.messages.create(body=body, from_=wa_from, to=to)
        return f"{msg.sid} (to {to})"
    except ImportError:
        return f"SIMULATED_SID_{uuid.uuid4().hex[:8]}"


async def _make_call(cfg: dict, to_phone: str, script: str, lead_id: str = None) -> str:
    try:
        from twilio.rest import Client
        from twilio.twiml.voice_response import VoiceResponse, Gather
        client = Client(cfg["twilio_account_sid"], cfg["twilio_auth_token"])
        vr = VoiceResponse()
        
        base_url = os.getenv("BACKEND_BASE_URL", "").rstrip("/")
        if base_url:
            action_url = f"{base_url}/api/channels/voice-reply"
            if lead_id:
                action_url += f"?lead_id={lead_id}"
            gather = Gather(input="speech", action=action_url, speechTimeout="auto", language="en-IN", enhanced="true")
            gather.say(script, voice="Polly.Aditi", language="en-IN")
            vr.append(gather)
        else:
            vr.say(script, voice="Polly.Aditi", language="en-IN")
        
        clean_phone = to_phone.replace(" ", "").replace("-", "")
        if len(clean_phone) == 10 and clean_phone.isdigit():
            clean_phone = f"+91{clean_phone}"
        elif not clean_phone.startswith("+"):
            clean_phone = f"+{clean_phone}"
            
        call = client.calls.create(
            twiml=str(vr), from_=cfg["twilio_phone_number"], to=clean_phone
        )
        return f"{call.sid} (to {clean_phone})"
    except ImportError:
        return f"SIMULATED_CALL_{uuid.uuid4().hex[:8]}"


# ── AI draft generator (Ollama — same model as pipeline agents) ───────────────

def _sync_ollama_draft(prompt: str) -> str:
    """Blocking Ollama call — run via asyncio.to_thread in async context."""
    from api.agents import OllamaWrapper
    llm = OllamaWrapper()
    resp = llm.generate_content(prompt)
    return (resp.text or "").strip()



async def _ai_draft(channel: str, lead: dict, template_hint: str = "") -> str:
    """
    Use Ollama (minimax-m2.5:cloud) to generate a personalized channel message.
    Pulls from profile, sdk_activity, intel, activity, and raw_data for full behavioral context.
    """
    import asyncio as _aio
    from api.agents import _build_channel_prompt, _extract_channel_media
    
    company_id = lead.get("company_id")
    cfg = await channel_settings_collection.find_one({"company_id": company_id}) if company_id else {}
    custom_prompt = cfg.get(f"{channel}_prompt") if cfg else None
    
    # Extract media context
    all_links, all_images = _extract_channel_media(lead)
    has_image = bool(all_images)

    prompt = _build_channel_prompt(channel, lead, custom_prompt=custom_prompt, has_image=has_image)
    if template_hint:
        prompt += f"\nEXTRA INSTRUCTIONS/HINT: {template_hint}\n"


    result = await _aio.to_thread(_sync_ollama_draft, prompt)

    # Fallback if Ollama is offline
    if not result:
        name = lead.get("profile", {}).get("name", "there")
        company = lead.get("profile", {}).get("company", "your company")
        if channel == "sms":
            result = f"Hi {name}! Noticed your interest in our platform for {company}. Would a quick 15-min call make sense this week?"
        elif channel == "whatsapp":
            result = f"Hi {name} 👋 We saw your interest in what we offer and wanted to reach out personally. Would love to show you how we can help {company}. Free for a quick chat?"
        else:
            result = f"Hi {name}, this is a quick call from our team. We noticed your engagement with our platform and wanted to personally reach out to see how we can help {company} achieve its goals. Do you have a moment to chat?"

    if channel == "sms":
        result = result[:160]

    return result


def _serialize_item(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    for f in ("created_at", "approved_at"):
        if isinstance(doc.get(f), datetime):
            doc[f] = doc[f].isoformat()
    return doc


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/settings")
async def get_settings(user=Depends(get_current_user)):
    try:
        company_id = str(user["company_id"])
        cfg = await channel_settings_collection.find_one({"company_id": company_id})
        if not cfg:
            return {"configured": False}
        cfg.pop("_id", None)
        # Mask the Twilio auth token for security
        if cfg.get("twilio_auth_token") and len(cfg["twilio_auth_token"]) > 4:
            cfg["twilio_auth_token"] = "••••" + cfg["twilio_auth_token"][-4:]
        # Return all fields at top level so frontend can read data.sms_prompt etc. directly
        return {"configured": True, **cfg}
    except Exception as e:
        import traceback
        with open("error_log.txt", "w") as f:
            f.write(traceback.format_exc())
        raise

@router.post("/settings")
@router.put("/settings")
async def save_settings(payload: ChannelSettings, user=Depends(get_current_user)):
    try:
        company_id = str(user["company_id"])
        updates = {k: v for k, v in payload.dict().items() if v is not None}
        updates.update({"company_id": company_id, "updated_at": datetime.now(timezone.utc)})
        await channel_settings_collection.update_one(
            {"company_id": company_id}, {"$set": updates}, upsert=True
        )
        return {"success": True}
    except Exception as e:
        import traceback
        with open("error_log.txt", "a") as f:
            f.write(traceback.format_exc())
        raise


@router.post("/generate-queue")
async def generate_queue(payload: GenerateQueuePayload, user=Depends(get_current_user)):
    """
    AI drafts personalized messages for all leads (or the selected subset).
    Creates pending items in outreach_queue — no messages sent yet.
    """
    company_id = str(user["company_id"])

    # Build lead filter
    lead_filter: dict = {"company_id": company_id}
    if payload.lead_ids:
        lead_filter["lead_id"] = {"$in": payload.lead_ids}
    # Removed the profile.phone filter to allow leads without numbers to be queued with fallback
    
    leads = []
    async for lead in leads_collection.find(lead_filter).limit(200):
        leads.append(lead)

    if not leads:
        return {"generated": 0, "message": "No eligible leads found."}

    # Remove already-queued pending items for this channel to avoid duplicates
    existing_leads = set()
    async for q in outreach_queue_col.find(
        {"company_id": company_id, "channel": payload.channel, "status": "pending"},
        {"lead_id": 1}
    ):
        existing_leads.add(q["lead_id"])

    generated = 0
    for lead in leads:
        lead_id = lead.get("lead_id", "")
        if lead_id in existing_leads:
            continue

        phone = lead.get("profile", {}).get("phone", "")
        if not phone:
            phone = DEFAULT_FALLBACK_PHONE

        try:
            draft = await _ai_draft(payload.channel, lead, payload.template_hint or "")
        except Exception as e:
            draft = f"[AI error: {e}] Hi {lead.get('profile',{}).get('name','there')}, reaching out to connect."

        item = {
            "company_id":  company_id,
            "lead_id":     lead_id,
            "lead_name":   lead.get("profile", {}).get("name", "Unknown"),
            "lead_company": lead.get("profile", {}).get("company", ""),
            "lead_phone":  phone,
            "intent_score": lead.get("intel", {}).get("intent_score", 0),
            "channel":     payload.channel,
            "draft":       draft,
            "status":      "pending",   # pending | approved | discarded
            "created_at":  datetime.now(timezone.utc),
            "source":      lead.get("source", ""),
        }
        await outreach_queue_col.insert_one(item)
        generated += 1

    return {"generated": generated, "channel": payload.channel}


@router.get("/queue")
async def get_queue(
    channel: Optional[str] = None,
    status: str = "pending",
    user=Depends(get_current_user)
):
    """Return the outreach draft queue for admin review."""
    company_id = str(user["company_id"])
    filt: dict = {"company_id": company_id, "status": status}
    if channel:
        filt["channel"] = channel

    items = []
    async for item in outreach_queue_col.find(filt).sort("intent_score", -1).limit(500):
        items.append(_serialize_item(item))
    return {"items": items, "count": len(items)}


@router.post("/approve")
async def approve_and_send(payload: ApprovePayload, user=Depends(get_current_user)):
    """
    Bulk approve: mark items as approved and immediately send via Twilio.
    """
    from bson import ObjectId

    company_id = str(user["company_id"])

    try:
        cfg = await _get_twilio_cfg(company_id)
    except HTTPException:
        cfg = None  # Will run in simulation mode

    sent = 0
    failed = 0
    errors = []

    for item_id in payload.item_ids:
        try:
            oid = ObjectId(item_id)
        except Exception:
            continue

        item = await outreach_queue_col.find_one({"_id": oid, "company_id": company_id})
        if not item or item.get("status") != "pending":
            continue

        phone   = item.get("lead_phone") or DEFAULT_FALLBACK_PHONE
        draft   = item["draft"]
        channel = item["channel"]
        sid     = None

        try:
            has_creds = cfg and cfg.get("twilio_account_sid") and cfg.get("twilio_auth_token")
            
            if has_creds:
                if channel == "sms":
                    sid = await _send_sms(cfg, phone, draft)
                elif channel == "whatsapp":
                    sid = await _send_whatsapp(cfg, phone, draft)
                elif channel == "voice":
                    sid = await _make_call(cfg, phone, draft, lead_id=item["lead_id"])
            else:
                sid = f"SIMULATED_{channel.upper()}_{uuid.uuid4().hex[:8]}"

            await outreach_queue_col.update_one(
                {"_id": oid},
                {"$set": {"status": "approved", "approved_at": datetime.now(timezone.utc), "twilio_sid": sid}}
            )

            # Log to agent_activity for the lead timeline
            await agent_activity_collection.insert_one({
                "company_id": company_id,
                "lead_id":    item["lead_id"],
                "agent":      f"{channel}_outreach",
                "status":     "sent",
                "summary":    f"{channel.upper()} sent to {phone}: \"{draft[:80]}...\" | SID: {sid}",
                "timestamp":  datetime.now(timezone.utc),
            })
            sent += 1

        except Exception as e:
            failed += 1
            errors.append(str(e))
            await outreach_queue_col.update_one(
                {"_id": oid},
                {"$set": {"status": "failed", "error": str(e)}}
            )

    return {"sent": sent, "failed": failed, "errors": errors[:5]}


@router.delete("/queue/{item_id}")
async def discard_draft(item_id: str, user=Depends(get_current_user)):
    from bson import ObjectId
    company_id = str(user["company_id"])
    await outreach_queue_col.update_one(
        {"_id": ObjectId(item_id), "company_id": company_id},
        {"$set": {"status": "discarded"}}
    )
    return {"success": True}


@router.patch("/queue/{item_id}/edit")
async def edit_draft(item_id: str, body: dict, user=Depends(get_current_user)):
    """Allow admin to edit a draft before approving."""
    from bson import ObjectId
    company_id = str(user["company_id"])
    new_text = body.get("draft", "")
    if not new_text:
        raise HTTPException(400, "draft field required")
    await outreach_queue_col.update_one(
        {"_id": ObjectId(item_id), "company_id": company_id},
        {"$set": {"draft": new_text, "edited": True}}
    )
    return {"success": True}


from fastapi import Request, Form
from fastapi.responses import HTMLResponse

@router.post("/voice-reply")
async def voice_reply(
    request: Request,
    lead_id: Optional[str] = None,
    SpeechResult: Optional[str] = Form(None)
):
    """
    Twilio Webhook for live interactive Voice AI.
    Receives SpeechResult, queries Ollama, and returns new TwiML to continue the conversation.
    """
    from twilio.twiml.voice_response import VoiceResponse, Gather
    vr = VoiceResponse()
    base_url = os.getenv("BACKEND_BASE_URL", "").rstrip("/")
    action_url = f"{base_url}/api/channels/voice-reply?lead_id={lead_id}" if lead_id else f"{base_url}/api/channels/voice-reply"

    print(f"\n==================================================")
    print(f"[VOICE AI] Incoming Speech Detected from Call!")
    print(f"  SpeechResult: \"{SpeechResult}\"")
    print(f"  Lead ID: {lead_id}")
    print(f"==================================================\n")

    if not SpeechResult:
        gather = Gather(input="speech", action=action_url, speechTimeout="3", language="en-IN", enhanced="true")
        gather.say("I didn't quite catch that. Are you still there?", voice="Polly.Aditi", language="en-IN")
        vr.append(gather)
        return HTMLResponse(content=str(vr), media_type="application/xml")

    # Fetch lead context if available
    lead_context = ""
    company_id = ""
    if lead_id:
        lead = await leads_collection.find_one({"lead_id": lead_id})
        if lead:
            company_id = lead.get("company_id")
            name = lead.get("profile", {}).get("name", "the customer")
            company = lead.get("profile", {}).get("company", "")
            intel = lead.get("intel", {})
            scraped = intel.get("scraped_media", [])
            product = scraped[0].get("name", "") if scraped else ""
            lead_context = f"Customer Name: {name}. Company: {company}. Product of interest: {product}."

    # Log Customer Speech
    if lead_id and company_id:
        from datetime import datetime, timezone
        await agent_activity_collection.insert_one({
            "company_id": company_id,
            "lead_id": lead_id,
            "agent": "VOICE_AGENT_LIVE",
            "action": f"Customer said: \"{SpeechResult}\"",
            "status": "SUCCESS",
            "timestamp": datetime.now(timezone.utc)
        })

    prompt = f"""
    You are an AI Sales Assistant on a live phone call. 
    Context: {lead_context}
    
    The customer just said: "{SpeechResult}"
    
    Provide a very brief, natural, conversational response (1-2 sentences maximum).
    Keep the tone friendly, professional, and persuasive. 
    Do NOT use markdown, emojis, or symbols, as this will be spoken aloud by a text-to-speech engine.
    Just output the exact words you will speak over the phone.
    """
    
    print(f"[VOICE AI] Querying LLM with transcribed speech...")
    import asyncio as _aio
    reply = await _aio.to_thread(_sync_ollama_draft, prompt)
    
    print(f"[VOICE AI] LLM Reply Generated:")
    print(f"  --> \"{reply}\"\n")
    
    if not reply:
        reply = "I understand. Could you tell me more about what you are looking for?"

        
    # Log AI Reply
    if lead_id and company_id:
        from datetime import datetime, timezone
        await agent_activity_collection.insert_one({
            "company_id": company_id,
            "lead_id": lead_id,
            "agent": "VOICE_AGENT_LIVE",
            "action": f"AI responded: \"{reply}\"",
            "status": "SUCCESS",
            "timestamp": datetime.now(timezone.utc)
        })
        
    gather = Gather(input="speech", action=action_url, speechTimeout="auto", language="en-IN", enhanced="true")
    gather.say(reply, voice="Polly.Aditi", language="en-IN")
    vr.append(gather)
    
    return HTMLResponse(content=str(vr), media_type="application/xml")

@router.get("/logs")
async def outreach_logs(channel: Optional[str] = None, user=Depends(get_current_user)):
    company_id = str(user["company_id"])
    filt: dict = {
        "company_id": company_id,
        "agent": {"$regex": "_outreach$"}
    }
    if channel:
        filt["agent"] = f"{channel}_outreach"

    logs = []
    async for log in agent_activity_collection.find(filt).sort("timestamp", -1).limit(200):
        log["id"] = str(log.pop("_id"))
        if isinstance(log.get("timestamp"), datetime):
            log["timestamp"] = log["timestamp"].isoformat()
        logs.append(log)
    return {"logs": logs}
