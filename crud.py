from datetime import datetime, timezone
from database import supabase
import uuid
import json

def log_action(user_id: str, action: str, entity_type: str, entity_id: str,
               old_values: dict | None = None, new_values: dict | None = None):
    """Insert an audit log entry."""
    supabase.table("audit_logs").insert({
        "user_id": user_id,
        "action": action,
        "entity_type": entity_type,
        "entity_id": str(entity_id),
        "old_values": json.dumps(old_values) if old_values else None,
        "new_values": json.dumps(new_values) if new_values else None,
    }).execute()

# ---------- Missions ----------
def get_all_missions():
    return supabase.table("missions").select("*").order("created_at", desc=False).execute().data

def get_mission(mission_id):
    return supabase.table("missions").select("*").eq("id", mission_id).single().execute().data

def create_mission(name: str, description: str | None, user_id: str):
    data = {"name": name, "description": description}
    res = supabase.table("missions").insert(data).execute().data[0]
    log_action(user_id, "mission_created", "mission", res["id"], new_values=data)
    return res

def update_mission(mission_id: str, name: str, description: str | None, user_id: str):
    old = get_mission(mission_id)
    new_data = {"name": name, "description": description}
    supabase.table("missions").update(new_data).eq("id", mission_id).execute()
    log_action(user_id, "mission_updated", "mission", mission_id, old_values=old, new_values=new_data)

def delete_mission(mission_id: str, user_id: str):
    old = get_mission(mission_id)
    supabase.table("missions").delete().eq("id", mission_id).execute()
    log_action(user_id, "mission_deleted", "mission", mission_id, old_values=old)

# ---------- Projects ----------
def get_projects_for_mission(mission_id: str):
    return supabase.table("projects").select("*").eq("mission_id", mission_id).order("created_at").execute().data

def get_project(project_id: str):
    return supabase.table("projects").select("*").eq("id", project_id).single().execute().data

def create_project(name: str, description: str | None, mission_id: str, lead_id: str | None, user_id: str):
    data = {
        "name": name,
        "description": description,
        "mission_id": mission_id,
        "lead_id": lead_id
    }
    res = supabase.table("projects").insert(data).execute().data[0]
    log_action(user_id, "project_created", "project", res["id"], new_values=data)
    return res

def update_project(project_id: str, name: str, description: str | None, lead_id: str | None, user_id: str):
    old = get_project(project_id)
    new_data = {"name": name, "description": description, "lead_id": lead_id}
    supabase.table("projects").update(new_data).eq("id", project_id).execute()
    log_action(user_id, "project_updated", "project", project_id, old_values=old, new_values=new_data)

def delete_project(project_id: str, user_id: str):
    old = get_project(project_id)
    supabase.table("projects").delete().eq("id", project_id).execute()
    log_action(user_id, "project_deleted", "project", project_id, old_values=old)

# ---------- Tasks ----------
def get_tasks_for_project(project_id: str):
    return supabase.table("tasks").select("*").eq("project_id", project_id).order("created_at").execute().data

def get_task(task_id: str):
    return supabase.table("tasks").select("*").eq("id", task_id).single().execute().data

def create_task(title: str, description: str | None, project_id: str, assignee_id: str | None, user_id: str):
    data = {
        "title": title,
        "description": description,
        "project_id": project_id,
        "assignee_id": assignee_id,
        "status": "todo"
    }
    res = supabase.table("tasks").insert(data).execute().data[0]
    log_action(user_id, "task_created", "task", res["id"], new_values=data)
    return res

def update_task_status(task_id: str, new_status: str, user_id: str):
    old = get_task(task_id)
    # Enforce valid transitions: todo -> in_progress -> done (no backward)
    if old["status"] == "done":
        raise Exception("Cannot change a completed task")
    if old["status"] == "todo" and new_status not in ("in_progress",):
        raise Exception("Can only move to In Progress")
    if old["status"] == "in_progress" and new_status not in ("done",):
        raise Exception("Can only move to Done")
    supabase.table("tasks").update({"status": new_status, "updated_at": datetime.now(timezone.utc).isoformat()}).eq("id", task_id).execute()
    log_action(user_id, "task_status_changed", "task", task_id, old_values={"status": old["status"]}, new_values={"status": new_status})

def assign_task(task_id: str, assignee_id: str | None, user_id: str):
    old = get_task(task_id)
    supabase.table("tasks").update({"assignee_id": assignee_id}).eq("id", task_id).execute()
    log_action(user_id, "task_assigned", "task", task_id, old_values={"assignee_id": old["assignee_id"]}, new_values={"assignee_id": assignee_id})

# ---------- Users ----------
def get_all_users():
    """Returns all profiles (id, role)."""
    return supabase.table("profiles").select("id, role").execute().data

def get_users_by_role(role: str):
    """Return profiles with a specific role, including username and display_name."""
    return supabase.table("profiles").select("id, role, username, display_name").eq("role", role).execute().data

# ---------- Comments ----------
def get_comments_for_task(task_id: str):
    res = supabase.table("comments").select("*").eq("task_id", task_id).order("created_at", desc=False).execute()
    return res.data

def add_comment(task_id: str, content: str, user_id: str):
    data = {"task_id": task_id, "user_id": user_id, "content": content}
    res = supabase.table("comments").insert(data).execute().data[0]
    log_action(user_id, "comment_added", "comment", res["id"], new_values=data)
    return res

# ---------- Progress Reporting ----------
def get_monthly_progress(month: str):
    """
    month: 'YYYY-MM' format.
    Returns task completions for that month per mission, project, and assignee.
    """
    start_date = f"{month}-01T00:00:00Z"
    # Calculate end month
    year, mon = month.split("-")
    y, m = int(year), int(mon)
    if m == 12:
        end_month = f"{y+1}-01"
    else:
        end_month = f"{y}-{m+1:02d}"
    end_date = f"{end_month}-01T00:00:00Z"

    # Completed in month
    completed = supabase.table("tasks").select("*")\
                .gte("updated_at", start_date)\
                .lt("updated_at", end_date)\
                .eq("status", "done").execute().data

    all_tasks = supabase.table("tasks").select("*").execute().data
    missions = supabase.table("missions").select("id, name").execute().data
    projects = supabase.table("projects").select("id, name, mission_id").execute().data

    # Build dicts
    mission_stats = {}
    for m in missions:
        mission_stats[m["id"]] = {"name": m["name"], "projects": {}}
    for p in projects:
        mission_stats[p["mission_id"]]["projects"][p["id"]] = {"name": p["name"], "total": 0, "completed": 0}
    for t in all_tasks:
        pid = t["project_id"]
        # find mission_id via project list
        for p in projects:
            if p["id"] == pid:
                mid = p["mission_id"]
                mission_stats[mid]["projects"][pid]["total"] += 1
                break
    for c in completed:
        pid = c["project_id"]
        for p in projects:
            if p["id"] == pid:
                mid = p["mission_id"]
                mission_stats[mid]["projects"][pid]["completed"] += 1
                break

    # Per assignee completions
    assignee_stats = {}
    for c in completed:
        aid = c["assignee_id"]
        if aid:
            assignee_stats[aid] = assignee_stats.get(aid, 0) + 1

    return mission_stats, assignee_stats

# ---------- Audit Logs ----------
def get_audit_logs(limit=50, user_id=None, entity_type=None):
    query = supabase.table("audit_logs").select("*").order("created_at", desc=True).limit(limit)
    if user_id:
        query = query.eq("user_id", user_id)
    if entity_type:
        query = query.eq("entity_type", entity_type)
    return query.execute().data

# ---------- User creation (admin) ----------
def create_user_by_admin(email: str, password: str, username: str, display_name: str, role: str, admin_id: str):
    # 1. Create auth user in Supabase
    try:
        auth_res = supabase.auth.sign_up({"email": email, "password": password})
        user_id = auth_res.user.id
    except Exception as e:
        raise Exception(f"Auth signup failed: {e}")

    # 2. Update profile with username, display_name, and desired role
    supabase.table("profiles").update({
        "username": username,
        "display_name": display_name,
        "role": role
    }).eq("id", user_id).execute()

    # 3. Log it
    log_action(admin_id, "user_created", "user", user_id,
               new_values={"email": email, "username": username, "display_name": display_name, "role": role})
    return user_id

def get_all_users_detailed():
    """Return all profiles with id, username, display_name, role, created_at."""
    return supabase.table("profiles").select("id, username, display_name, role, created_at").order("created_at").execute().data

# ---------- Multi-Assignee ----------
def get_assignees(task_id: str) -> list[dict]:
    """Return list of user profiles assigned to a task."""
    res = supabase.table("task_assignees").select("user_id, profiles!inner(id, username, display_name, role)").eq("task_id", task_id).execute()
    # The nested select might need adjustment. Simpler: get user_ids then fetch profiles.
    # We'll do a two-step for clarity.
    assignee_rows = supabase.table("task_assignees").select("user_id").eq("task_id", task_id).execute().data
    user_ids = [r["user_id"] for r in assignee_rows]
    if not user_ids:
        return []
    # Fetch profiles with those ids
    profiles = supabase.table("profiles").select("id, username, display_name, role").in_("id", user_ids).execute().data
    return profiles

def assign_users_to_task(task_id: str, user_ids: list[str], admin_id: str):
    """Replace all assignees for a task with the given list."""
    # Remove existing
    supabase.table("task_assignees").delete().eq("task_id", task_id).execute()
    # Add new
    for uid in user_ids:
        supabase.table("task_assignees").insert({"task_id": task_id, "user_id": uid}).execute()
    # Log (simplified)
    log_action(admin_id, "task_assignees_updated", "task", task_id,
               new_values={"assignee_ids": user_ids})

def get_tasks_for_user(user_id: str) -> list[dict]:
    """Return tasks where the user is an assignee."""
    rows = supabase.table("task_assignees").select("task_id").eq("user_id", user_id).execute().data
    task_ids = [r["task_id"] for r in rows]
    if not task_ids:
        return []
    return supabase.table("tasks").select("*").in_("id", task_ids).execute().data

# Modify monthly progress to use junction table
def get_monthly_progress(month: str):
    start_date = f"{month}-01T00:00:00Z"
    year, mon = month.split("-")
    y, m = int(year), int(mon)
    if m == 12:
        end_month = f"{y+1}-01"
    else:
        end_month = f"{y}-{m+1:02d}"
    end_date = f"{end_month}-01T00:00:00Z"

    # Completed tasks in the month
    completed_tasks = supabase.table("tasks").select("*")\
                .gte("updated_at", start_date)\
                .lt("updated_at", end_date)\
                .eq("status", "done").execute().data

    all_tasks = supabase.table("tasks").select("*").execute().data
    missions = supabase.table("missions").select("id, name").execute().data
    projects = supabase.table("projects").select("id, name, mission_id").execute().data

    # Mission/project totals
    mission_stats = {}
    for m in missions:
        mission_stats[m["id"]] = {"name": m["name"], "projects": {}}
    for p in projects:
        mission_stats[p["mission_id"]]["projects"][p["id"]] = {"name": p["name"], "total": 0, "completed": 0}
    for t in all_tasks:
        pid = t["project_id"]
        for p in projects:
            if p["id"] == pid:
                mid = p["mission_id"]
                mission_stats[mid]["projects"][pid]["total"] += 1
                break
    for c in completed_tasks:
        pid = c["project_id"]
        for p in projects:
            if p["id"] == pid:
                mid = p["mission_id"]
                mission_stats[mid]["projects"][pid]["completed"] += 1
                break

    # Per-assignee completions (using junction table)
    assignee_stats = {}
    for c in completed_tasks:
        # get all assignees for this completed task
        assignees = supabase.table("task_assignees").select("user_id").eq("task_id", c["id"]).execute().data
        for a in assignees:
            uid = a["user_id"]
            assignee_stats[uid] = assignee_stats.get(uid, 0) + 1

    return mission_stats, assignee_stats
