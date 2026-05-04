"""
A/B Test Agent — AI-powered email variant generator (Phase 2)

Uses Gemini/Ollama to generate subject line and tone variants for A/B tests.
Can also auto-evaluate statistical significance and recommend a winner.
"""

import os
import json
import math
import httpx
from datetime import datetime
from bson import ObjectId

from db import ab_tests_collection

from api.agents import OllamaWrapper

# ── Statistical Helper ─────────────────────────────────────────────────────────

def _z_score(opens_a: int, sent_a: int, opens_b: int, sent_b: int) -> float:
    if sent_a == 0 or sent_b == 0:
        return 0.0
    p_a     = opens_a / sent_a
    p_b     = opens_b / sent_b
    p_pool  = (opens_a + opens_b) / (sent_a + sent_b)
    if p_pool in (0, 1):
        return 0.0
    se = math.sqrt(p_pool * (1 - p_pool) * (1 / sent_a + 1 / sent_b))
    return abs(p_a - p_b) / se if se else 0.0


# ── Variant Generation ─────────────────────────────────────────────────────────

async def generate_ab_variants(
    original_subject: str,
    original_content: str,
    context: str = "",
) -> dict:
    """
    Generate two email variants (A and B) from an original subject/content.
    Returns {"variant_a": {...}, "variant_b": {...}} or fallback stubs.
    """
    prompt = f"""You are an expert email copywriter. Given an original sales email, generate TWO different variants for an A/B test.

Variant A: Rephrase the subject line to be curiosity-driven and short (<8 words).
Variant B: Rephrase the subject line to be benefit-driven with a clear value prop.

Also lightly rewrite the opening two sentences for each variant to match the tone.

Original subject: {original_subject}
Original content (first 400 chars): {original_content[:400]}
{f"Additional context: {context}" if context else ""}

Respond ONLY with valid JSON in this exact shape:
{{
  "variant_a": {{"subject": "...", "content": "..."}},
  "variant_b": {{"subject": "...", "content": "..."}}
}}"""

    # ── USE CENTRALIZED OLLAMA WRAPPER ─────────────────────────────────────
    ollama = OllamaWrapper()
    response = ollama.generate_content(prompt)

    raw = response.text if hasattr(response, "text") else ""


    try:
        # Extract JSON from response (handle markdown fences)
        raw = raw.strip()
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)
        return {
            "variant_a": {
                "id":      "A",
                "subject": data["variant_a"]["subject"],
                "content": data["variant_a"]["content"],
            },
            "variant_b": {
                "id":      "B",
                "subject": data["variant_b"]["subject"],
                "content": data["variant_b"]["content"],
            },
        }
    except Exception as exc:
        print(f"[ABTestAgent] Failed to parse variant JSON: {exc}")
        # Fallback: return slight rewrites
        return {
            "variant_a": {
                "id":      "A",
                "subject": original_subject,
                "content": original_content,
            },
            "variant_b": {
                "id":      "B",
                "subject": f"RE: {original_subject}",
                "content": original_content,
            },
        }


# ── Auto-Winner Evaluation ─────────────────────────────────────────────────────

async def auto_evaluate_and_declare_winner(test_id: str | ObjectId):
    """
    Fetch a running A/B test, compute statistical significance, and
    auto-declare a winner if z-score >= 1.96 (95% confidence).

    Called by a periodic task or manually via the API.
    Returns {"declared": bool, "winner": str | None, "z_score": float}
    """
    oid = ObjectId(str(test_id))
    doc = await ab_tests_collection.find_one({"_id": oid})
    if not doc or doc.get("status") != "running":
        return {"declared": False, "winner": None, "z_score": 0.0}

    variants = doc.get("variants", [])
    if len(variants) < 2:
        return {"declared": False, "winner": None, "z_score": 0.0}

    v_a = variants[0]
    v_b = variants[1]

    z = _z_score(
        v_a.get("opens", 0), max(v_a.get("sent", 1), 1),
        v_b.get("opens", 0), max(v_b.get("sent", 1), 1),
    )

    if z >= 1.96:
        # Determine winner by higher open rate
        rate_a = v_a.get("opens", 0) / max(v_a.get("sent", 1), 1)
        rate_b = v_b.get("opens", 0) / max(v_b.get("sent", 1), 1)
        winner_id = v_a["id"] if rate_a >= rate_b else v_b["id"]

        await ab_tests_collection.update_one(
            {"_id": oid},
            {"$set": {
                "status":       "completed",
                "winner":       winner_id,
                "significance": round(z, 3),
                "completed_at": datetime.utcnow(),
                "auto_declared": True,
            }}
        )
        print(f"[ABTestAgent] Auto-declared winner: Variant {winner_id} (z={z:.3f})")
        return {"declared": True, "winner": winner_id, "z_score": round(z, 3)}

    print(f"[ABTestAgent] Not yet significant (z={z:.3f}). Needs more data.")
    return {"declared": False, "winner": None, "z_score": round(z, 3)}
