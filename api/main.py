from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from api.routers import environments, sync_pairs

app = FastAPI(
    title="LDAP Group Sync Manager",
    description="Web interface for managing LDAP/AD/EntraID group synchronization",
    version="1.0.0",
)

# ── Register API routers ────────────────────────────────────────────────────
app.include_router(environments.router)
app.include_router(sync_pairs.router)

# ── Serve frontend static files ─────────────────────────────────────────────
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/", include_in_schema=False)
def serve_frontend():
    return FileResponse(FRONTEND_DIR / "index.html")
