from fastapi import APIRouter, Request, Depends, HTTPException
from datetime import date, datetime
import crud
from auth import get_current_user
from templates_utils import render_template, get_username_map
from database import supabase

router = APIRouter(tags=["dashboard"])

@router.get("/dashboard")
async def dashboard(request: Request, user: dict = Depends(get_current_user)):
    org_id = user.get("organization_id")
    
    # Optimized fetch to fix N+1
    missions_query = supabase.table("missions").select("*")
    if org_id:
        missions_query = missions_query.eq("organization_id", org_id)
    missions = missions_query.execute().data
    
    projects_query = supabase.table("projects").select("id, mission_id")
    if org_id:
        projects_query = projects_query.eq("organization_id", org_id)
    projects = projects_query.execute().data
    
    tasks_query = supabase.table("tasks").select("id, project_id")
    if org_id:
        tasks_query = tasks_query.eq("organization_id", org_id)
    tasks = tasks_query.execute().data
    
    project_map = {} 
    for p in projects:
        mid = p["mission_id"]
        if mid not in project_map:
            project_map[mid] = []
        project_map[mid].append(p["id"])
        
    task_map = {}
    for t in tasks:
        pid = t["project_id"]
        task_map[pid] = task_map.get(pid, 0) + 1
        
    mission_stats = []
    for m in missions:
        m_projects = project_map.get(m["id"], [])
        t_count = sum(task_map.get(pid, 0) for pid in m_projects)
        mission_stats.append({
            "mission": m,
            "project_count": len(m_projects),
            "task_count": t_count
        })
        
    return render_template("dashboard.html", request, user=user, missions=mission_stats)

@router.get("/my-tasks")
async def my_tasks(request: Request, user: dict = Depends(get_current_user)):
    org_id = user.get("organization_id")
    tasks = crud.get_tasks_for_user(user["id"], org_id)
    username_map = get_username_map(org_id)
    today = date.today()
    overdue = []
    due_today = []
    due_this_week = []
    upcoming = []
    no_due = []
    for t in tasks:
        proj = crud.get_project(t["project_id"], org_id)
        if not proj: continue
        mission = crud.get_mission(proj["mission_id"], org_id)
        if not mission: continue
        t["_project_name"] = proj["name"]
        t["_mission_name"] = mission["name"]
        if t.get("due_date"):
            try:
                due = date.fromisoformat(t["due_date"])
                diff = (due - today).days
                if diff < 0:
                    overdue.append(t)
                elif diff == 0:
                    due_today.append(t)
                elif diff <= 7:
                    due_this_week.append(t)
                else:
                    upcoming.append(t)
            except:
                no_due.append(t)
        else:
            no_due.append(t)
    groups = [
        ("Overdue", overdue),
        ("Due Today", due_today),
        ("Due This Week", due_this_week),
        ("Upcoming", upcoming),
        ("No Due Date", no_due),
    ]
    return render_template("my_tasks.html", request, user=user, groups=groups, username_map=username_map)

@router.get("/progress")
async def progress_dashboard(request: Request, month: str = None, user: dict = Depends(get_current_user)):
    if not month:
        now = datetime.utcnow()
        month = now.strftime("%Y-%m")
    org_id = user.get("organization_id")
    mission_stats, assignee_stats = crud.get_monthly_progress(month, org_id)
    username_map = get_username_map(org_id)
    return render_template("progress.html", request, user=user, month=month,
                           mission_stats=mission_stats, assignee_stats=assignee_stats,
                           username_map=username_map)

@router.get("/search")
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
    org_id = user.get("organization_id")
    missions_query = supabase.table("missions").select("*")
    if org_id:
        missions_query = missions_query.eq("organization_id", org_id)
    missions = missions_query.execute().data
    
    mission_id_val = mission_id if mission_id else None
    projects = []
    if mission_id_val:
        projects = crud.get_projects_for_mission(mission_id_val, org_id)

    query = supabase.table("tasks").select("*")
    if org_id:
        query = query.eq("organization_id", org_id)
        
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
    username_map = get_username_map(org_id)
    return render_template(
        "search.html", request, user=user, results=results, query=q,
        missions=missions, selected_mission=mission_id, projects=projects,
        selected_project=project_id, selected_status=status,
        start_month=start_month, end_month=end_month, username_map=username_map
    )
