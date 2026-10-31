"""
FastAPI Application Entry Point (Section 2 & 7):
Regenerative Supercapacitor Elevator Energy Manager
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.db.session import init_db
from backend.services.simulation_service import SimulationService
from backend.routers.api import router as api_router
from backend.routers.websocket import ws_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Startup: Initialize SQLite/Postgres DB
    init_db()
    
    # 2. Start background 1-second simulation & controller loop
    sim_service = SimulationService()
    await sim_service.start()
    
    yield
    
    # 3. Shutdown: Stop background simulation
    await sim_service.stop()

app = FastAPI(
    title="Regenerative Supercapacitor Elevator Energy Manager",
    description="Full-stack energy management, forecasting, safe RL, accounting and diagnostics for PMSM elevators",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration for local React / Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(api_router)
app.include_router(ws_router)

# Mount Frontend static files if built
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
else:
    @app.get("/")
    def index():
        return {
            "name": "Regenerative Supercapacitor Elevator Energy Manager API",
            "version": "1.0.0",
            "docs": "/docs",
            "dashboard": "Frontend running on http://localhost:5173 (or run 'npm run dev' in frontend/)"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=False)
