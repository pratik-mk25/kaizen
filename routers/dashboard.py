from fastapi import APIRouter, Request, Depends, HTTPException
from datetime import date, datetime
import crud
from auth import get_current_user
from templates_utils import render_template, get_username_map
from database import supabase, supabase_admin

router = APIRouter(tags=["dashboard"])

def _get_client():
    return supabase_admin if supabase_admin else supabase

@router.get("/dashboard")
async def dashboard(
    request: Request, 
    mission_id: str = None,
    project_id: str = None,
    user: dict = Depends(get_current_user)
):
    if user.get("role") == "editor":
        return await editor_hub(request, user)
        
    org_id = user.get("organization_id")
    is_editor = user.get("role") == "editor"
    today = date.today()
    
    try:
        # Optimized fetch with optional filters
        missions_query = _get_client().table("missions").select("*")
        if org_id and not is_editor:
            missions_query = missions_query.eq("organization_id", org_id)
        if mission_id:
            missions_query = missions_query.eq("id", mission_id)
        missions_data = missions_query.execute().data or []
        
        projects_query = _get_client().table("projects").select("*")
        if org_id and not is_editor:
            projects_query = projects_query.eq("organization_id", org_id)
        if mission_id:
            projects_query = projects_query.eq("mission_id", mission_id)
        if project_id:
            projects_query = projects_query.eq("id", project_id)
        projects_data = projects_query.execute().data or []
        
        tasks_query = _get_client().table("tasks").select("*")
        if org_id and not is_editor:
            tasks_query = tasks_query.eq("organization_id", org_id)
        if project_id:
            tasks_query = tasks_query.eq("project_id", project_id)
        elif mission_id:
            # If mission filtered but not project, we need to filter tasks by project_ids in that mission
            p_ids = [p["id"] for p in projects_data]
            if p_ids:
                tasks_query = tasks_query.in_("project_id", p_ids)
            else:
                tasks_query = tasks_query.eq("project_id", "00000000-0000-0000-0000-000000000000") # Empty result
        tasks_data = tasks_query.execute().data or []

        # For the filter dropdowns, we need all missions/projects in the system (for editor) or org
        all_missions_query = _get_client().table("missions").select("id, name")
        if org_id and not is_editor:
            all_missions_query = all_missions_query.eq("organization_id", org_id)
        all_missions = all_missions_query.execute().data or []

        all_projects = []
        if mission_id:
            all_projects_query = _get_client().table("projects").select("id, name").eq("mission_id", mission_id)
            if org_id and not is_editor:
                all_projects_query = all_projects_query.eq("organization_id", org_id)
            all_projects = all_projects_query.execute().data or []
        
        profiles_query = _get_client().table("profiles").select("id", count="exact")
        if org_id and not is_editor:
            profiles_query = profiles_query.eq("organization_id", org_id)
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

        # Fetch recent activities for the sidebar (Editor sees everything)
        recent_logs = crud.get_audit_logs(limit=10, org_id=None if is_editor else org_id)
            
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
        # Fallback for migration/initial setup issues
        return render_template("dashboard.html", request, user=user, missions=[], stats={}, alerts=[], error=str(e))

async def editor_hub(request: Request, user: dict):
    try:
        # Use admin client to bypass all RLS
        admin_client = supabase_admin if supabase_admin else supabase
        
        # 1. Fetch Global Stats
        orgs_res = admin_client.table("organizations").select("id, name").execute()
        orgs = orgs_res.data or []
        
        users_res = admin_client.table("profiles").select("id", count="exact").execute()
        user_count = users_res.count if hasattr(users_res, 'count') else len(users_res.data)
        
        tasks_res = admin_client.table("tasks").select("id", count="exact").execute()
        task_count = tasks_res.count if hasattr(tasks_res, 'count') else len(tasks_res.data)
        
        # 2. Fetch Recent Activities (Global)
        recent_logs = crud.get_audit_logs(limit=30)
        
        # 3. Organization Health (Member counts)
        profiles_all = admin_client.table("profiles").select("organization_id").execute().data or []
        org_counts = {}
        for p in profiles_all:
            oid = p.get("organization_id")
            if oid:
                org_counts[oid] = org_counts.get(oid, 0) + 1
            
        for o in orgs:
            o["member_count"] = org_counts.get(o["id"], 0)
            
        # 4. Maps for templates
        username_map = get_username_map() # Global map
        org_map = {o["id"]: o["name"] for o in orgs}
        
        return render_template("editor_hub.html", request, user=user,
                               stats={
                                   "org_count": len(orgs),
                                   "user_count": user_count,
                                   "task_count": task_count
                               },
                               recent_activities=recent_logs,
                               organizations=orgs,
                               username_map=username_map,
                               org_map=org_map)
    except Exception as e:
        return render_template("dashboard.html", request, user=user, missions=[], stats={}, alerts=[], error=f"Hub Error: {str(e)}")

@router.get("/my-tasks")
async def my_tasks(request: Request, user: dict = Depends(get_current_user)):
    org_id = user.get("organization_id")
    is_editor = user.get("role") == "editor"
    tasks = crud.get_tasks_for_user(user["id"], None if is_editor else org_id)
    username_map = get_username_map(None if is_editor else org_id)
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
    org_id = user.get("organization_id")
    is_editor = user.get("role") == "editor"
    mission_stats, assignee_stats = crud.get_monthly_progress(month, None if is_editor else org_id)
    username_map = get_username_map(None if is_editor else org_id)
    return render_template("progress.html", request, user=user, month=month,
                           mission_stats=mission_stats, assignee_stats=assignee_stats,
                           username_map=username_map)

@router.get("/demo-analytics")
async def demo_analytics(request: Request, user: dict = Depends(get_current_user)):
    """A purely static page for video recording purposes to ensure charts always show data."""
    return render_template("fake_progress.html", request, user=user)

@router.get("/progress/operative/{user_id}")
async def operative_drilldown(request: Request, user_id: str, month: str = None, user: dict = Depends(get_current_user)):
    if not month:
        now = datetime.utcnow()
        month = now.strftime("%Y-%m")
    
    org_id = user.get("organization_id")
    
    # 1. Get task_ids for this user from junction table
    assignee_rows = _get_client().table("task_assignees").select("task_id").eq("user_id", user_id).execute().data
    task_ids = [r["task_id"] for r in assignee_rows]
    
    if not task_ids:
        return render_template("_operative_stats.html", request, stats={})

    # 2. Get completed tasks for this user in this month
    start_date = f"{month}-01T00:00:00Z"
    y, m = map(int, month.split("-"))
    next_month = f"{y+1}-01" if m == 12 else f"{y}-{m+1:02d}"
    end_date = f"{next_month}-01T00:00:00Z"

    query = _get_client().table("tasks").select("*, projects(name, mission_id, missions(name))").in_("id", task_ids).eq("status", "done").gte("updated_at", start_date).lt("updated_at", end_date)
    if org_id:
        query = query.eq("organization_id", org_id)
    
    tasks = query.execute().data or []
    
    # 3. Group by Mission/Project
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
        
    username_map = get_username_map(org_id)
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
    org_id = user.get("organization_id")
    is_editor = user.get("role") == "editor"
    missions_query = _get_client().table("missions").select("*")
    if org_id and not is_editor:
        missions_query = missions_query.eq("organization_id", org_id)
    missions = missions_query.execute().data
    
    mission_id_val = mission_id if mission_id else None
    projects = []
    if mission_id_val:
        projects = crud.get_projects_for_mission(mission_id_val, None if is_editor else org_id)

    query = _get_client().table("tasks").select("*")
    if org_id and not is_editor:
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
    username_map = get_username_map(None if is_editor else org_id)
    return render_template(
        "search.html", request, user=user, results=results, query=q,
        missions=missions, selected_mission=mission_id, projects=projects,
        selected_project=project_id, selected_status=status,
        start_month=start_month, end_month=end_month, username_map=username_map
    )
