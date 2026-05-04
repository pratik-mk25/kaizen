import os
from pathlib import Path
from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader
from dotenv import load_dotenv
from typing import Optional
from database import supabase
import auth
from auth import set_auth_cookie, remove_auth_cookie, get_current_user, admin_required, lead_or_admin_required
import crud
from datetime import datetime

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="Mission Tracker")
env = Environment(loader=FileSystemLoader(str(BASE_DIR / "templates")), autoescape=True)

def render_template(template_name: str, request: Request, **kwargs) -> HTMLResponse:
    template = env.get_template(template_name)
    html_content = template.render(request=request, **kwargs)
    return HTMLResponse(html_content)

def get_username_map():
    """Return dict mapping user_id -> username or display_name."""
    users = crud.get_all_users_detailed()
    return {u["id"]: u["username"] or u["display_name"] or u["id"] for u in users}

# ---------- Public / test routes ----------
@app.get("/")
async def home(request: Request):
    token = request.cookies.get(auth.COOKIE_NAME)
    if token:
        try:
            supabase.auth.get_user(token)
            return RedirectResponse(url="/dashboard")
        except:
            pass
    return RedirectResponse(url="/login")

@app.get("/ping")
async def ping():
    return {"status": "ok"}

# ---------- Auth routes ----------
@app.get("/signup")
async def signup_page(request: Request):
    return render_template("signup.html", request)

@app.post("/signup")
async def signup_post(request: Request, email: str = Form(...), password: str = Form(...)):
    try:
        supabase.auth.sign_up({"email": email, "password": password})
    except Exception as e:
        return render_template("signup.html", request, error=str(e))
    return RedirectResponse(url="/login?message=Account created. Please log in.", status_code=303)

@app.get("/login")
async def login_page(request: Request, message: Optional[str] = None):
    return render_template("login.html", request, message=message)

@app.post("/login")
async def login_post(request: Request, email: str = Form(...), password: str = Form(...)):
    try:
        auth_response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        access_token = auth_response.session.access_token
        response = RedirectResponse(url="/dashboard", status_code=303)
        set_auth_cookie(response, access_token)
        return response
    except Exception as e:
        return render_template("login.html", request, error=str(e))

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login")
    remove_auth_cookie(response)
    return response

# ---------- Dashboard ----------
@app.get("/dashboard")
async def dashboard(request: Request, user: dict = Depends(get_current_user)):
    missions = crud.get_all_missions()
    mission_stats = []
    for m in missions:
        projects = crud.get_projects_for_mission(m["id"])
        task_count = 0
        for p in projects:
            tasks = crud.get_tasks_for_project(p["id"])
            task_count += len(tasks)
        mission_stats.append({
            "mission": m,
            "project_count": len(projects),
            "task_count": task_count
        })
    return render_template("dashboard.html", request, user=user, missions=mission_stats)

# ---------- Mission detail ----------
@app.get("/missions/{mission_id}")
async def mission_detail(request: Request, mission_id: str, user: dict = Depends(get_current_user)):
    mission = crud.get_mission(mission_id)
    projects = crud.get_projects_for_mission(mission_id)
    return render_template("mission_detail.html", request, user=user, mission=mission, projects=projects)

# Admin: mission CRUD
@app.get("/admin/missions/create")
async def create_mission_form(request: Request, user: dict = Depends(admin_required)):
    return render_template("mission_form.html", request, user=user, mission=None)

@app.post("/admin/missions/create")
async def create_mission_action(request: Request, name: str = Form(...), description: str = Form(""), user: dict = Depends(admin_required)):
    crud.create_mission(name, description, user["id"])
    return RedirectResponse(url="/dashboard", status_code=303)

@app.get("/admin/missions/{mission_id}/edit")
async def edit_mission_form(request: Request, mission_id: str, user: dict = Depends(admin_required)):
    mission = crud.get_mission(mission_id)
    return render_template("mission_form.html", request, user=user, mission=mission)

@app.post("/admin/missions/{mission_id}/edit")
async def edit_mission_action(request: Request, mission_id: str, name: str = Form(...), description: str = Form(""), user: dict = Depends(admin_required)):
    crud.update_mission(mission_id, name, description, user["id"])
    return RedirectResponse(url=f"/missions/{mission_id}", status_code=303)

@app.post("/admin/missions/{mission_id}/delete")
async def delete_mission(mission_id: str, user: dict = Depends(admin_required)):
    crud.delete_mission(mission_id, user["id"])
    return RedirectResponse(url="/dashboard", status_code=303)

# ---------- Project detail ----------
@app.get("/projects/{project_id}")
async def project_detail(request: Request, project_id: str, user: dict = Depends(get_current_user)):
    project = crud.get_project(project_id)
    tasks = crud.get_tasks_for_project(project_id)
    assignable_users = crud.get_all_users_detailed()
    username_map = get_username_map()
    # Fetch assignees for all tasks
    task_assignees = {}
    for t in tasks:
        task_assignees[t["id"]] = crud.get_assignees(t["id"])
    return render_template("project_detail.html", request, user=user, project=project, tasks=tasks,
                           assignable_users=assignable_users, username_map=username_map, task_assignees=task_assignees)

# Admin: project CRUD
@app.get("/admin/projects/create")
async def create_project_form(request: Request, mission_id: str, user: dict = Depends(admin_required)):
    leads = crud.get_users_by_role("lead")
    return render_template("project_form.html", request, user=user, mission_id=mission_id, project=None, leads=leads)

@app.post("/admin/projects/create")
async def create_project_action(request: Request, mission_id: str = Form(...), name: str = Form(...), description: str = Form(""), lead_id: str = Form(None), user: dict = Depends(admin_required)):
    crud.create_project(name, description, mission_id, lead_id if lead_id else None, user["id"])
    return RedirectResponse(url=f"/missions/{mission_id}", status_code=303)

@app.get("/admin/projects/{project_id}/edit")
async def edit_project_form(request: Request, project_id: str, user: dict = Depends(admin_required)):
    project = crud.get_project(project_id)
    leads = crud.get_users_by_role("lead")
    return render_template("project_form.html", request, user=user, project=project, mission_id=project["mission_id"], leads=leads)

@app.post("/admin/projects/{project_id}/edit")
async def edit_project_action(request: Request, project_id: str, name: str = Form(...), description: str = Form(""), lead_id: str = Form(None), user: dict = Depends(admin_required)):
    crud.update_project(project_id, name, description, lead_id if lead_id else None, user["id"])
    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)

@app.post("/admin/projects/{project_id}/delete")
async def delete_project(project_id: str, user: dict = Depends(admin_required)):
    project = crud.get_project(project_id)
    mission_id = project["mission_id"]
    crud.delete_project(project_id, user["id"])
    return RedirectResponse(url=f"/missions/{mission_id}", status_code=303)

# ---------- Task operations ----------
@app.post("/projects/{project_id}/tasks/create")
async def add_task(request: Request, project_id: str, title: str = Form(...), description: str = Form(""), assignee_id: str = Form(None),
                   user: dict = Depends(lead_or_admin_required)):
    assignee = assignee_id if assignee_id else None
    new_task = crud.create_task(title, description, project_id, assignee, user["id"])
    # If assignee provided, add to junction table
    if assignee:
        crud.assign_users_to_task(new_task["id"], [assignee], user["id"])
    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)

@app.post("/tasks/{task_id}/update-status")
async def update_task_status(task_id: str, new_status: str = Form(...), user: dict = Depends(lead_or_admin_required)):
    try:
        crud.update_task_status(task_id, new_status, user["id"])
    except Exception as e:
        pass
    task = crud.get_task(task_id)
    return RedirectResponse(url=f"/projects/{task['project_id']}", status_code=303)

@app.post("/tasks/{task_id}/assign")
async def assign_task_endpoint(
    task_id: str,
    request: Request,  # need to read form list
    user: dict = Depends(lead_or_admin_required)
):
    # Get selected user IDs as a list from the form
    form_data = await request.form()
    # The multi-select will send multiple values with the same name "assignee_ids"
    assigned = form_data.getlist("assignee_ids")  # returns list of strings
    crud.assign_users_to_task(task_id, assigned, user["id"])
    return RedirectResponse(url=f"/tasks/{task_id}", status_code=303)

@app.get("/tasks/{task_id}")
async def task_detail(request: Request, task_id: str, user: dict = Depends(get_current_user)):
    task = crud.get_task(task_id)
    assignable_users = crud.get_all_users_detailed()
    comments = crud.get_comments_for_task(task_id)
    username_map = get_username_map()
    assignees = crud.get_assignees(task_id)  # list of profiles
    return render_template("task_detail.html", request, user=user, task=task,
                           assignable_users=assignable_users, comments=comments,
                           username_map=username_map, assignees=assignees)

# ---------- Comments ----------
@app.post("/tasks/{task_id}/comment")
async def add_comment_endpoint(task_id: str, content: str = Form(...), user: dict = Depends(lead_or_admin_required)):
    crud.add_comment(task_id, content, user["id"])
    return RedirectResponse(url=f"/tasks/{task_id}", status_code=303)

# ---------- Advanced Search ----------
@app.get("/search")
async def search(
    request: Request,
    q: str = "",
    mission_id: str = "",
    project_id: str = "",
    status: str = "",
    start_month: str = "",
    end_month: str = "",
    user: dict = Depends(get_current_user)
):
    # Dropdown data
    missions = crud.get_all_missions()
    mission_id_val = mission_id if mission_id else None
    projects = []
    if mission_id_val:
        projects = crud.get_projects_for_mission(mission_id_val)

    # Build query
    query = supabase.table("tasks").select("*")
    
    if q.strip():
        search_filter = f"%{q.strip()}%"
        query = query.or_(f"title.ilike.{search_filter},description.ilike.{search_filter}")
    
    if project_id:
        query = query.eq("project_id", project_id)
    
    if status in ("todo", "in_progress", "done"):
        query = query.eq("status", status)
    
    if start_month:
        query = query.gte("created_at", f"{start_month}-01T00:00:00Z")
    if end_month:
        y, m = map(int, end_month.split('-'))
        if m == 12:
            next_month = f"{y+1}-01"
        else:
            next_month = f"{y}-{m+1:02d}"
        query = query.lt("created_at", f"{next_month}-01T00:00:00Z")
    
    results = query.execute().data
    
    username_map = get_username_map()
    return render_template(
        "search.html",
        request,
        user=user,
        results=results,
        query=q,
        missions=missions,
        selected_mission=mission_id,
        projects=projects,
        selected_project=project_id,
        selected_status=status,
        start_month=start_month,
        end_month=end_month,
        username_map=username_map
    )

# ---------- Admin: User Management ----------
@app.get("/admin/users")
async def list_users(request: Request, user: dict = Depends(admin_required)):
    profiles = crud.get_all_users_detailed()
    return render_template("admin_users.html", request, user=user, profiles=profiles)

@app.post("/admin/users/{user_id}/role")
async def change_user_role(user_id: str, new_role: str = Form(...), user: dict = Depends(admin_required)):
    if new_role not in ("member", "lead", "admin"):
        return HTMLResponse("Invalid role", status_code=400)
    supabase.table("profiles").update({"role": new_role}).eq("id", user_id).execute()
    crud.log_action(user["id"], "role_updated", "user", user_id,
                    old_values={"role": "..."},
                    new_values={"role": new_role})
    return RedirectResponse(url="/admin/users", status_code=303)

@app.get("/admin/users/add")
async def add_user_form(request: Request, user: dict = Depends(admin_required)):
    return render_template("admin_add_user.html", request, user=user)

@app.post("/admin/users/add")
async def add_user_action(request: Request,
                          email: str = Form(...),
                          password: str = Form(...),
                          username: str = Form(...),
                          display_name: str = Form(...),
                          role: str = Form(...),
                          user: dict = Depends(admin_required)):
    if role not in ("member", "lead", "admin"):
        return HTMLResponse("Invalid role", status_code=400)
    try:
        crud.create_user_by_admin(email, password, username, display_name, role, user["id"])
    except Exception as e:
        return render_template("admin_add_user.html", request, user=user, error=str(e))
    return RedirectResponse(url="/admin/users", status_code=303)

# ---------- Admin: Audit Log ----------
@app.get("/admin/audit-log")
async def audit_log_view(request: Request, user: dict = Depends(admin_required)):
    logs = crud.get_audit_logs(limit=100)
    return render_template("audit_log.html", request, user=user, logs=logs)

# ---------- Progress Dashboard ----------
@app.get("/progress")
async def progress_dashboard(request: Request, month: str = None, user: dict = Depends(get_current_user)):
    if not month:
        now = datetime.utcnow()
        month = now.strftime("%Y-%m")
    mission_stats, assignee_stats = crud.get_monthly_progress(month)
    username_map = get_username_map()
    return render_template("progress.html", request, user=user, month=month, mission_stats=mission_stats,
                           assignee_stats=assignee_stats, username_map=username_map)
