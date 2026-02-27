from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.dashboard import router as dashboard_router
from api.leads import router as leads_router
from api.agents import router as agents_router
from api.batch import router as batch_router
from api.auth import router as auth_router

app = FastAPI(title="Strategic Grid API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard_router, prefix="/api/dashboard")
app.include_router(leads_router, prefix="/api/leads")
app.include_router(agents_router, prefix="/api/agents")
app.include_router(batch_router, prefix="/api/batch")
app.include_router(auth_router, prefix="/api/auth")
