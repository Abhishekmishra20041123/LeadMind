"""
Phase 6 — AI Chatbot API
POST /api/chat/message   — handle visitor message (API-key auth)
GET  /api/chat/sessions  — list chat sessions (authenticated dashboard)
GET  /api/chat/history/{session_id} — full message history
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import uuid, os, json as _json

from db import (
    chat_sessions_collection,
    chat_messages_collection,
    api_keys_collection,
    leads_collection,
)
from dependencies import get_current_user

router = APIRouter()

# ── API-key auth helper ───────────────────────────────────────────────────────

async def _verify_api_key(x_api_key: str = Header(..., alias="X-Api-Key")):
    key_doc = await api_keys_collection.find_one({"key": x_api_key, "is_active": True})
    if not key_doc:
        raise HTTPException(401, "Invalid or revoked API key")
    return key_doc


# ── Pydantic ──────────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    session_id: str
    message: str
    visitor_name: Optional[str] = None
    visitor_email: Optional[str] = None


# ── Gemini conversation helper ────────────────────────────────────────────────

async def _run_chat_agent(company_id: str, session_id: str, user_message: str,
                           visitor_name: Optional[str], visitor_email: Optional[str]) -> dict:
    """
    Multi-turn chat agent: maintains history in DB, calls Minimax 2.7 (Ollama) for response,
    detects name/email to capture lead.
    """
    from api.agents import OllamaWrapper

    # Initialize Minimax model
    llm = OllamaWrapper()

    # Load history (last 20 messages)
    history = []
    async for msg in chat_messages_collection.find(
        {"session_id": session_id},
        sort=[("timestamp", 1)]
    ).limit(20):
        history.append({"role": msg["role"], "content": msg["content"]})

    # Session info
    session = await chat_sessions_collection.find_one({"session_id": session_id})
    captured_email = (session or {}).get("captured_email") or visitor_email
    captured_name  = (session or {}).get("captured_name")  or visitor_name

    system_prompt = f"""You are a friendly, professional AI sales assistant embedded on a company website.
Your goals (in order):
1. Greet warmly and understand the visitor's interest/problem.
2. If you don't yet have their name, ask for it naturally.
3. If you don't yet have their email, ask politely.
4. Once you have name + email, say you'll have someone follow up shortly.
5. Keep replies short (2-3 sentences max). Be helpful, never pushy.

Known visitor info: name="{captured_name or 'unknown'}", email="{captured_email or 'unknown'}"

Previous conversation:
{_json.dumps(history)}

Visitor says: "{user_message}"

Reply as the AI assistant. If the visitor just provided an email or name, acknowledge it warmly.
Return ONLY the reply text — no JSON, no markdown.
"""
    resp = llm.generate_content(system_prompt)
    reply = resp.text.strip()

    # Extract email from message if present
    import re
    if not captured_email and visitor_email:
        captured_email = visitor_email
    if not captured_email:
        email_match = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", user_message)
        if email_match:
            captured_email = email_match.group(0)

    # Update session
    lead_created = False
    update_fields: dict = {"last_message_at": datetime.now(timezone.utc)}
    if captured_email:
        update_fields["captured_email"] = captured_email
    if captured_name or visitor_name:
        update_fields["captured_name"] = captured_name or visitor_name

    # Auto-create lead once we have email
    if captured_email and (not session or not session.get("lead_created")):
        existing = await leads_collection.find_one(
            {"profile.email": captured_email, "company_id": company_id}
        )
        if not existing:
            lead_doc = {
                "lead_id":    f"L_CHAT_{uuid.uuid4().hex[:6].upper()}",
                "company_id": company_id,
                "source":     "chatbot",
                "profile": {
                    "name":    captured_name or visitor_name or "Chat Visitor",
                    "email":   captured_email,
                    "company": "Unknown",
                    "title":   "",
                    "phone":   "",
                },
                "intel": {"intent_score": 50, "summary": "Captured via AI chatbot widget."},
                "status": "new",
                "pipeline_stage": "New Lead",
                "created_at": datetime.now(timezone.utc),
            }
            await leads_collection.insert_one(lead_doc)
            lead_created = True
            update_fields["lead_created"] = True

    await chat_sessions_collection.update_one(
        {"session_id": session_id},
        {"$set": update_fields}
    )

    return {"reply": reply, "lead_created": lead_created}


# ── Routes ───────────────────────────────────────────────────────────────────

@router.post("/message")
async def chat_message(payload: ChatMessage, key_doc=Depends(_verify_api_key)):
    company_id = str(key_doc["company_id"])
    session_id = payload.session_id

    # Upsert session
    await chat_sessions_collection.update_one(
        {"session_id": session_id},
        {"$setOnInsert": {
            "session_id":  session_id,
            "company_id":  company_id,
            "created_at":  datetime.now(timezone.utc),
            "lead_created": False,
        }},
        upsert=True
    )

    # Persist visitor message
    await chat_messages_collection.insert_one({
        "session_id": session_id,
        "company_id": company_id,
        "role":       "user",
        "content":    payload.message,
        "timestamp":  datetime.now(timezone.utc),
    })

    # Run agent
    result = await _run_chat_agent(
        company_id, session_id, payload.message,
        payload.visitor_name, payload.visitor_email
    )

    # Persist agent reply
    await chat_messages_collection.insert_one({
        "session_id": session_id,
        "company_id": company_id,
        "role":       "assistant",
        "content":    result["reply"],
        "timestamp":  datetime.now(timezone.utc),
    })

    return {"reply": result["reply"], "lead_created": result["lead_created"]}


@router.get("/sessions")
async def list_sessions(user=Depends(get_current_user)):
    company_id = str(user["company_id"])
    sessions = []
    async for s in chat_sessions_collection.find(
        {"company_id": company_id},
        sort=[("last_message_at", -1)]
    ).limit(50):
        s["id"] = str(s.pop("_id", ""))
        for f in ("created_at", "last_message_at"):
            if isinstance(s.get(f), datetime):
                s[f] = s[f].isoformat()
        sessions.append(s)
    return {"sessions": sessions}


@router.get("/history/{session_id}")
async def chat_history(session_id: str, user=Depends(get_current_user)):
    messages = []
    async for m in chat_messages_collection.find(
        {"session_id": session_id},
        sort=[("timestamp", 1)]
    ):
        m.pop("_id", None)
        if isinstance(m.get("timestamp"), datetime):
            m["timestamp"] = m["timestamp"].isoformat()
        messages.append(m)
    return {"messages": messages}
