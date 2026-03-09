from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from api.dashboard import router as dashboard_router
from api.leads import router as leads_router
from api.agents import router as agents_router
from api.batch import router as batch_router
from api.auth import router as auth_router
from api.tracking import router as tracking_router
from db import create_indexes
from services.scheduler import scheduler_loop
import asyncio
import os
from fastapi.staticfiles import StaticFiles

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize MongoDB Indexes on startup
    await create_indexes()
    
    # Start background scheduler poll
    scheduler_task = asyncio.create_task(scheduler_loop())
    
    yield
    scheduler_task.cancel()

app = FastAPI(title="Strategic Grid API", lifespan=lifespan)

# Ensure public logos directory exists before mounting StaticFiles
os.makedirs("public/logos", exist_ok=True)

# Mount public directory for serving static files like uploaded logos
app.mount("/public", StaticFiles(directory="public"), name="public")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tracking_router,  prefix="/api/track")   # public — no auth
app.include_router(dashboard_router, prefix="/api/dashboard")
app.include_router(leads_router,     prefix="/api/leads")
app.include_router(agents_router,    prefix="/api/agents")
app.include_router(batch_router,     prefix="/api/batch")
app.include_router(auth_router,      prefix="/api/auth")


