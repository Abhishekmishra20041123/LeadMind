"""
Email Templates API
-------------------
CRUD endpoints for managing reusable email layout templates.

Routes:
  GET    /api/templates/         → list all templates for the company
  POST   /api/templates/         → create a new template
  GET    /api/templates/{id}     → fetch a single template
  PUT    /api/templates/{id}     → update an existing template
  DELETE /api/templates/{id}     → delete a template
"""

from datetime import datetime
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends, Body

from db import email_templates_collection
from dependencies import get_current_user

router = APIRouter()


def _serialize(doc: dict) -> dict:
    """Convert MongoDB document to JSON-serializable dict."""
    doc["_id"] = str(doc["_id"])
    if "company_id" in doc and isinstance(doc["company_id"], ObjectId):
        doc["company_id"] = str(doc["company_id"])
    return doc


@router.get("/")
async def list_templates(user=Depends(get_current_user)):
    """List all saved templates for the current company."""
    company_id = ObjectId(user["company_id"])
    cursor = email_templates_collection.find(
        {"company_id": company_id},
        {"blocks": 0}  # exclude block data for list view (performance)
    ).sort("updated_at", -1)
    docs = await cursor.to_list(length=200)
    return {"templates": [_serialize(d) for d in docs]}


@router.post("/")
async def create_template(payload: dict = Body(...), user=Depends(get_current_user)):
    """Save a new email template."""
    name = payload.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Template name is required")

    now = datetime.utcnow()
    doc = {
        "company_id": ObjectId(user["company_id"]),
        "name": name,
        "blocks": payload.get("blocks", []),
        "global_styles": payload.get("global_styles", {}),
        "created_at": now,
        "updated_at": now,
    }
    result = await email_templates_collection.insert_one(doc)
    return {"status": "created", "template_id": str(result.inserted_id)}


@router.get("/{template_id}")
async def get_template(template_id: str, user=Depends(get_current_user)):
    """Fetch a single template by ID (includes full blocks array)."""
    try:
        oid = ObjectId(template_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid template ID")

    doc = await email_templates_collection.find_one({
        "_id": oid,
        "company_id": ObjectId(user["company_id"])
    })
    if not doc:
        raise HTTPException(status_code=404, detail="Template not found")
    return _serialize(doc)


@router.put("/{template_id}")
async def update_template(template_id: str, payload: dict = Body(...), user=Depends(get_current_user)):
    """Update an existing template."""
    try:
        oid = ObjectId(template_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid template ID")

    updates: dict = {"updated_at": datetime.utcnow()}
    if "name" in payload:
        updates["name"] = payload["name"]
    if "blocks" in payload:
        updates["blocks"] = payload["blocks"]
    if "global_styles" in payload:
        updates["global_styles"] = payload["global_styles"]

    result = await email_templates_collection.update_one(
        {"_id": oid, "company_id": ObjectId(user["company_id"])},
        {"$set": updates}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"status": "updated"}


@router.delete("/{template_id}")
async def delete_template(template_id: str, user=Depends(get_current_user)):
    """Delete a template."""
    try:
        oid = ObjectId(template_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid template ID")

    result = await email_templates_collection.delete_one({
        "_id": oid,
        "company_id": ObjectId(user["company_id"])
    })
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"status": "deleted"}


def render_block_html(block: dict, gs: dict) -> str:
    bg = block.get("bgColor") or gs.get("contentBgColor", "#ffffff")
    def wrap(inner: str, bgcol: str) -> str:
        return f'<tr><td style="background:{bgcol};padding:0 24px;">{inner}</td></tr>'

    btype = block.get("type")
    
    if btype == "logo":
        align = block.get("align", "center")
        src = block.get("src", "")
        width = block.get("width", 150)
        alt = block.get("alt", "Logo")
        inner = f'<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="{align}" style="padding:16px 0;">'
        if src:
            inner += f'<img src="{src}" width="{width}" alt="{alt}" style="display:block;border:0;max-width:100%;" />'
        else:
            inner += f'<div style="width:{width}px;height:60px;background:#e0e0e0;display:inline-flex;align-items:center;justify-content:center;color:#999;font-size:13px;font-family:Arial,sans-serif;">Logo Placeholder</div>'
        inner += '</td></tr></table>'
        return wrap(inner, bg)
        
    elif btype == "banner":
        src = block.get("src", "")
        max_h = block.get("maxHeight", 220)
        link = block.get("link", "#")
        alt = block.get("alt", "Banner")
        if src:
            inner = f'<a href="{link}" style="display:block;line-height:0;"><img src="{src}" style="display:block;width:100%;max-height:{max_h}px;object-fit:cover;border:0;" alt="{alt}" /></a>'
        else:
            inner = f'<div style="width:100%;height:{max_h}px;background:linear-gradient(135deg,#667eea,#764ba2);display:flex;align-items:center;justify-content:center;"><span style="color:white;font-size:20px;font-family:Arial,sans-serif;opacity:0.7;">Banner Image</span></div>'
        return wrap(inner, bg)
        
    elif btype == "heading":
        fs = block.get("fontSize", 26)
        col = block.get("color", "#1a1a1a")
        align = block.get("align", "left")
        wgt = "700" if block.get("bold", True) else "400"
        stl = "italic" if block.get("italic", False) else "normal"
        ff = gs.get("fontFamily", "Arial, sans-serif")
        text = block.get("text", "Your Headline Here")
        inner = f'<h2 style="margin:20px 0 10px;font-size:{fs}px;color:{col};text-align:{align};font-weight:{wgt};font-style:{stl};font-family:{ff};">{text}</h2>'
        return wrap(inner, bg)
        
    elif btype == "text":
        fs = block.get("fontSize", 15)
        col = block.get("color", "#333333")
        align = block.get("align", "left")
        lh = block.get("lineHeight", 1.7)
        ff = gs.get("fontFamily", "Arial, sans-serif")
        text = block.get("text", "").replace("\\n", "<br/>")
        inner = f'<p style="margin:0 0 16px;font-size:{fs}px;color:{col};text-align:{align};line-height:{lh};font-family:{ff};">{text}</p>'
        return wrap(inner, bg)
        
    elif btype == "ai_body":
        fs = block.get("fontSize", 15)
        col = block.get("color", "#333333")
        align = block.get("align", "left")
        lh = block.get("lineHeight", 1.7)
        ff = gs.get("fontFamily", "Arial, sans-serif")
        inner = f'<div style="font-size:{fs}px;color:{col};text-align:{align};line-height:{lh};font-family:{ff};">{{{{personalized_message}}}}</div>'
        return wrap(inner, bg)
        
    elif btype == "greeting":
        fs = block.get("fontSize", 18)
        col = block.get("color", "#1a1a1a")
        wgt = "700" if block.get("bold", True) else "400"
        ff = gs.get("fontFamily", "Arial, sans-serif")
        pref = block.get("prefix", "Hi")
        name = block.get("name", "{{customer_name}}")
        suff = block.get("suffix", ",")
        inner = f'<p style="margin:20px 0 10px;font-size:{fs}px;color:{col};font-weight:{wgt};font-family:{ff};">{pref} {name}{suff}</p>'
        return wrap(inner, bg)
        
    elif btype == "desc":
        fs = block.get("fontSize", 15)
        col = block.get("color", "#333333")
        align = block.get("align", "left")
        lh = block.get("lineHeight", 1.7)
        ff = gs.get("fontFamily", "Arial, sans-serif")
        text = block.get("text", "").replace("\\n", "<br/>")
        inner = f'<p style="margin:0 0 16px;font-size:{fs}px;color:{col};text-align:{align};line-height:{lh};font-family:{ff};background:{bg};padding:16px;border-left:4px solid #0a0a0a;">{text}</p>'
        return wrap(inner, bg)
        
    elif btype == "cta":
        url = block.get("url", "https://")
        btc = block.get("bgColor", "#0a0a0a")
        tc = block.get("textColor", "#ffffff")
        fs = block.get("fontSize", 15)
        ff = gs.get("fontFamily", "Arial, sans-serif")
        rad = block.get("borderRadius", 4)
        lbl = block.get("label", "Book a Call")
        cta = f'<a href="{url}" style="display:inline-block;padding:14px 32px;background:{btc};color:{tc};font-size:{fs}px;font-family:{ff};font-weight:700;text-decoration:none;border-radius:{rad}px;">{lbl}</a>'
        align = block.get("align", "center")
        return wrap(f'<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="{align}" style="padding:20px 0;">{cta}</td></tr></table>', "#ffffff")
        
    elif btype == "divider":
        my = block.get("marginY", 16)
        th = block.get("thickness", 1)
        st = block.get("style", "solid")
        col = block.get("color", "#e0e0e0")
        return f'<tr><td style="padding:{my}px 24px;"><hr style="border:none;border-top:{th}px {st} {col};margin:0;" /></td></tr>'
        
    elif btype == "footer":
        align = block.get("align", "center")
        fs = block.get("fontSize", 12)
        col = block.get("color", "#888888")
        ff = gs.get("fontFamily", "Arial, sans-serif")
        text = block.get("text", "").replace("\\n", "<br/>")
        unsub = block.get("unsubscribeUrl", "https://")
        inner = f'<div style="padding:20px 0;text-align:{align};font-size:{fs}px;color:{col};font-family:{ff};line-height:1.6;">{text}<br/><a href="{unsub}" style="color:{col};text-decoration:underline;font-size:{fs-1}px;">Unsubscribe</a></div>'
        return wrap(inner, bg)
        
    return ""

def render_blocks_to_html(blocks: list, gs: dict) -> str:
    rows = "\\n".join(render_block_html(b, gs) for b in blocks)
    obg = gs.get("outerBgColor", "#e8e8e8")
    cbg = gs.get("contentBgColor", "#ffffff")
    ff = gs.get("fontFamily", "Arial, sans-serif")
    mw = gs.get("maxWidth", 600)
    
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:{obg};font-family:{ff};">
<table width="100%" cellpadding="0" cellspacing="0" style="background:{obg};">
<tr><td align="center" style="padding:24px 12px;">
<table width="{mw}" cellpadding="0" cellspacing="0" style="background:{cbg};border-radius:4px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
{rows}
</table>
</td></tr></table>
</body></html>"""
