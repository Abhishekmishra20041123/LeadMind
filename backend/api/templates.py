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

import os
import cloudinary
import cloudinary.uploader
from datetime import datetime
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends, Body, File, UploadFile

from db import email_templates_collection
from dependencies import get_current_user

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

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


@router.post("/upload")
async def upload_image(file: UploadFile = File(...), user=Depends(get_current_user)):
    """Upload an image to Cloudinary and return the secure URL."""
    try:
        upload_result = cloudinary.uploader.upload(file.file, folder="email_templates")
        return {"url": upload_result.get("secure_url")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


from services.templating import render_blocks_to_html, render_block_html

