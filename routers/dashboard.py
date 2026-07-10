from fastapi import APIRouter, Request, Depends, HTTPException
from datetime import date, datetime
import crud
from auth import get_current_user
from templates_utils import render_template, get_username_map
from database import supabase

router = APIRouter(tags=["dashboard"])

@router.get("/dashboard")
async def dashboard(
    request: Request, 
    mission_id: str = None,
    project_id: str = None,
    user: dict = Depends(get_current_user)
):
    today = date.today()
    
    try:
        missions_query = supabase.table("missions").select("*")
        if mission_id:
            missions_query = missions_query.eq("id", mission_id)
        missions_data = missions_query.execute().data or []
        
        projects_query = supabase.table("projects").select("*")
        if mission_id:
            projects_query = projects_query.eq("mission_id", mission_id)
        if project_id:
            projects_query = projects_query.eq("id", project_id)
        projects_data = projects_query.execute().data or []
        
        tasks_query = supabase.table("tasks").select("*")
        if project_id:
            tasks_query = tasks_query.eq("project_id", project_id)
        elif mission_id:
            p_ids = [p["id"] for p in projects_data]
            if p_ids:
                tasks_query = tasks_query.in_("project_id", p_ids)
            else:
                tasks_query = tasks_query.eq("project_id", "00000000-0000-0000-0000-000000000000")
        tasks_data = tasks_query.execute().data or []

        all_missions_query = supabase.table("missions").select("id, name")
        all_missions = all_missions_query.execute().data or []

        all_projects = []
        if mission_id:
            all_projects_query = supabase.table("projects").select("id, name").eq("mission_id", mission_id)
            all_projects = all_projects_query.execute().data or []
        
        profiles_query = supabase.table("profiles").select("id", count="exact")
        profiles_res = profiles_query.execute()
        active_users_count = profiles_res.count if hasattr(profiles_res, 'count') else len(profiles_res.data)
        
        project_map = {} 
        for p in projects_data:
            mid = p["mission_id"]
            if mid not in project_map:
                project_map[mid] = []
            project_map[mid].append(p["id"])
            
        task_map = {}
        completed_task_map = {}
        overdue_tasks = []
        due_soon_tasks = []
        completed_this_month = 0
        
        this_month_start = date(today.year, today.month, 1).isoformat()
        
        for t in tasks_data:
            pid = t["project_id"]
            task_map[pid] = task_map.get(pid, 0) + 1
            
            if t["status"] == "done":
                completed_task_map[pid] = completed_task_map.get(pid, 0) + 1
                if t.get("updated_at") and t["updated_at"] >= this_month_start:
                    completed_this_month += 1
            else:
                if t.get("due_date"):
                    try:
                        due = date.fromisoformat(t["due_date"])
                        diff = (due - today).days
                        if diff < 0:
                            overdue_tasks.append(t)
                        elif 0 <= diff <= 3:
                            due_soon_tasks.append(t)
                    except:
                        pass
            
        mission_stats = []
        for m in missions_data:
            m_projects = project_map.get(m["id"], [])
            t_count = sum(task_map.get(pid, 0) for pid in m_projects)
            c_count = sum(completed_task_map.get(pid, 0) for pid in m_projects)
            progress = (c_count / t_count * 100) if t_count > 0 else 0
            
            mission_stats.append({
                "mission": m,
                "project_count": len(m_projects),
                "task_count": t_count,
                "completed_task_count": c_count,
                "progress": int(progress)
            })
            
        stats = {
            "total_tasks": len(tasks_data),
            "completed_this_month": completed_this_month,
            "overdue_count": len(overdue_tasks),
            "active_users": active_users_count
        }

        recent_logs = crud.get_audit_logs(limit=10)
            
        return render_template("dashboard.html", request, user=user, 
                               missions=mission_stats, 
                               stats=stats,
                               alerts=overdue_tasks + due_soon_tasks,
                               recent_activities=recent_logs,
                               all_missions=all_missions,
                               all_projects=all_projects,
                               selected_mission=mission_id,
                               selected_project=project_id)
    except Exception as e:
        return render_template("dashboard.html", request, user=user, missions=[], stats={}, alerts=[], error=str(e))

@router.get("/my-tasks")
async def my_tasks(request: Request, user: dict = Depends(get_current_user)):
    tasks = crud.get_tasks_for_user(user["id"])
    username_map = get_username_map()
    today = date.today()
    overdue = []
    due_today = []
    due_this_week = []
    upcoming = []
    no_due = []
    for t in tasks:
        proj = crud.get_project(t["project_id"])
        if not proj: continue
        mission = crud.get_mission(proj["mission_id"])
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
        ("overdue", overdue),
        ("due_today", due_today),
        ("due_this_week", due_this_week),
        ("upcoming", upcoming),
        ("no_due", no_due),
    ]
    return render_template("my_tasks.html", request, user=user, groups=groups, username_map=username_map)

@router.get("/progress")
async def progress_dashboard(request: Request, month: str = None, user: dict = Depends(get_current_user)):
    if not month:
        now = datetime.utcnow()
        month = now.strftime("%Y-%m")
    mission_stats, assignee_stats = crud.get_monthly_progress(month)
    username_map = get_username_map()
    return render_template("progress.html", request, user=user, month=month,
                           mission_stats=mission_stats, assignee_stats=assignee_stats,
                           username_map=username_map)

@router.get("/progress/operative/{user_id}")
async def operative_drilldown(request: Request, user_id: str, month: str = None, user: dict = Depends(get_current_user)):
    if not month:
        now = datetime.utcnow()
        month = now.strftime("%Y-%m")
    
    assignee_rows = supabase.table("task_assignees").select("task_id").eq("user_id", user_id).execute().data
    task_ids = [r["task_id"] for r in assignee_rows]
    
    if not task_ids:
        return render_template("_operative_stats.html", request, stats={})

    start_date = f"{month}-01T00:00:00Z"
    y, m = map(int, month.split("-"))
    next_month = f"{y+1}-01" if m == 12 else f"{y}-{m+1:02d}"
    end_date = f"{next_month}-01T00:00:00Z"

    query = supabase.table("tasks").select("*, projects(name, mission_id, missions(name))").in_("id", task_ids).eq("status", "done").gte("updated_at", start_date).lt("updated_at", end_date)
    
    tasks = query.execute().data or []
    
    stats = {}
    for t in tasks:
        p = t.get("projects")
        m = p.get("missions")
        m_name = m.get("name") if m else "Unknown Mission"
        p_name = p.get("name") if p else "Unknown Project"
        
        if m_name not in stats:
            stats[m_name] = {}
        if p_name not in stats[m_name]:
            stats[m_name][p_name] = []
        stats[m_name][p_name].append(t["title"])
        
    username_map = get_username_map()
    return render_template("_operative_stats.html", request, stats=stats, operative_name=username_map.get(user_id, "Unknown"))

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
    missions_query = supabase.table("missions").select("*")
    missions = missions_query.execute().data
    
    mission_id_val = mission_id if mission_id else None
    projects = []
    if mission_id_val:
        projects = crud.get_projects_for_mission(mission_id_val)

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
        "search.html", request, user=user, results=results, query=q,
        missions=missions, selected_mission=mission_id, projects=projects,
        selected_project=project_id, selected_status=status,
        start_month=start_month, end_month=end_month, username_map=username_map
    )
