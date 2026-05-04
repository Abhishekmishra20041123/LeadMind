from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import traceback

from api.dashboard import router as dashboard_router
from api.leads import router as leads_router
from api.agents import router as agents_router
from api.batch import router as batch_router
from api.auth import router as auth_router
from api.tracking import router as tracking_router
from api.templates import router as templates_router
from api.pipeline import router as pipeline_router
from api.campaigns import router as campaigns_router
from api.ab_testing import router as ab_router
from api.api_keys import router as api_keys_router
from api.segments import router as segments_router
from api.reports import router as reports_router
from api.ingest import router as ingest_router
from api.tasks import router as tasks_router         # Phase 6 — Task Management
from api.chat import router as chat_router            # Phase 6 — AI Chatbot
from api.channels import router as channels_router    # Phase 6 — Multi-Channel (Twilio)
from db import create_indexes
from services.scheduler import scheduler_loop
from services.campaign_engine import campaign_engine_loop
from services.auto_pipeline import auto_pipeline_loop
import asyncio
import os
from fastapi.staticfiles import StaticFiles

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize MongoDB Indexes on startup
    await create_indexes()

    # Start background scheduler poll (follow-ups)
    scheduler_task = asyncio.create_task(scheduler_loop())

    # Start campaign engine (drip campaign step processor — Phase 2)
    campaign_task = asyncio.create_task(campaign_engine_loop())

    # Start auto-pipeline (SDK visitor promotion — Phase 3)
    auto_pipeline_task = asyncio.create_task(auto_pipeline_loop())

    yield

    scheduler_task.cancel()
    campaign_task.cancel()
    auto_pipeline_task.cancel()

app = FastAPI(title="LeadMind API", lifespan=lifespan)

# Ensure static directories exist before mounting StaticFiles
os.makedirs("public/logos", exist_ok=True)
os.makedirs("public/sdk",   exist_ok=True)

# Mount public directory for serving static files like uploaded logos
app.mount("/public", StaticFiles(directory="public"), name="public")

# CORS must be registered AFTER the custom middleware so it runs outermost
# (Starlette applies middleware in reverse-registration order)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled 500s, log the traceback, and add CORS headers
    so the browser can read the error detail instead of seeing a CORS block."""
    tb = traceback.format_exc()
    print(f"UNHANDLED EXCEPTION on {request.method} {request.url}:\n{tb}")
    origin = request.headers.get("origin", "")
    allowed = ["http://localhost:3000", "http://127.0.0.1:3000"]
    headers = {}
    if origin in allowed:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
        headers=headers,
    )

@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"DEBUG: Request {request.method} {request.url}")
    response = await call_next(request)
    print(f"DEBUG: Response status {response.status_code}")
    return response

app.include_router(tracking_router,  prefix="/api/track")     # public — pixel tracking (open/click)
app.include_router(ingest_router,    prefix="/api/ingest")    # public — SDK event ingest (Phase 3)
app.include_router(dashboard_router, prefix="/api/dashboard")
app.include_router(leads_router,     prefix="/api/leads")
app.include_router(agents_router,    prefix="/api/agents")
app.include_router(batch_router,     prefix="/api/batch")
app.include_router(auth_router,      prefix="/api/auth")
app.include_router(templates_router, prefix="/api/templates")
app.include_router(pipeline_router,  prefix="/api/pipeline")
app.include_router(campaigns_router, prefix="/api/campaigns")
app.include_router(ab_router,        prefix="/api/ab")
app.include_router(api_keys_router,  prefix="/api/api-keys")  # authenticated — Phase 3
app.include_router(segments_router,  prefix="/api/segments")  # authenticated — Phase 4
app.include_router(reports_router,   prefix="/api/reports")   # authenticated — Phase 4
app.include_router(tasks_router,     prefix="/api/tasks")     # authenticated — Phase 6
app.include_router(chat_router,      prefix="/api/chat")      # API-key + authenticated — Phase 6
app.include_router(channels_router,  prefix="/api/channels")  # authenticated — Phase 6 (Twilio)


