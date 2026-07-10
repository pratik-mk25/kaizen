import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from database import supabase
import auth
from templates_utils import render_template
from routers import auth as auth_router, missions, projects, tasks, admin, dashboard, settings, equipment, members, budget, docs, attendance_kiosk

# Force absolute path for .env loading
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

app = FastAPI(title="MISSION AVINYA", docs_url=None, redoc_url=None)

# 401 Exception Handler
@app.exception_handler(401)
async def unauthorized_exception_handler(request: Request, exc):
    return RedirectResponse(url="/login", status_code=303)

# Include Routers
app.include_router(auth_router.router)
app.include_router(missions.router)
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(admin.router)
app.include_router(dashboard.router)
app.include_router(settings.router)
app.include_router(equipment.router)
app.include_router(members.router)
app.include_router(budget.router)
app.include_router(docs.router)
app.include_router(attendance_kiosk.router)

@app.get("/")
async def home(request: Request):
    token = request.cookies.get(auth.COOKIE_NAME)
    if token:
        try:
            supabase.auth.get_user(token)
            return RedirectResponse(url="/dashboard")
        except:
            pass
    return render_template("landing.html", request)

@app.get("/ping")
async def ping():
    return {"status": "ok"}
