from datetime import datetime, timezone
from database import supabase, supabase_admin
import uuid
import json

def log_action(user_id: str, action: str, entity_type: str, entity_id: str,
               old_values: dict | None = None, new_values: dict | None = None, org_id: str | None = None):
    client = supabase_admin if supabase_admin else supabase
    try:
        data = {
            "user_id": user_id,
            "action": action,
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "old_values": json.dumps(old_values) if old_values else None,
            "new_values": json.dumps(new_values) if new_values else None,
        }
        if org_id:
            data["organization_id"] = org_id
            
        client.table("audit_logs").insert(data).execute()
    except Exception as e:
        print(f"DEBUG: Failed to log action {action}: {e}")

# ---------- Missions ----------
def get_all_missions(org_id: str = None):
    query = supabase.table("missions").select("*").order("created_at", desc=False)
    if org_id:
        query = query.eq("organization_id", org_id)
    return query.execute().data

def get_mission(mission_id: str, org_id: str = None):
    query = supabase.table("missions").select("*").eq("id", mission_id)
    if org_id:
        query = query.eq("organization_id", org_id)
    return query.single().execute().data

def create_mission(name: str, description: str | None, user_id: str, org_id: str = None):
    data = {"name": name, "description": description}
    if org_id:
        data["organization_id"] = org_id
    res = supabase.table("missions").insert(data).execute().data[0]
    log_action(user_id, "mission_created", "mission", res["id"], new_values=data, org_id=org_id)
    return res

def update_mission(mission_id: str, name: str, description: str | None, user_id: str, org_id: str = None):
    old = get_mission(mission_id, org_id)
    new_data = {"name": name, "description": description}
    supabase.table("missions").update(new_data).eq("id", mission_id).execute()
    log_action(user_id, "mission_updated", "mission", mission_id, old_values=old, new_values=new_data, org_id=org_id)

def delete_mission(mission_id: str, user_id: str, org_id: str = None):
    old = get_mission(mission_id, org_id)
    supabase.table("missions").delete().eq("id", mission_id).execute()
    log_action(user_id, "mission_deleted", "mission", mission_id, old_values=old, org_id=org_id)

# ---------- Projects ----------
def get_projects_for_mission(mission_id: str, org_id: str = None):
    query = supabase.table("projects").select("*").eq("mission_id", mission_id).order("created_at")
    if org_id:
        query = query.eq("organization_id", org_id)
    return query.execute().data

def get_project(project_id: str, org_id: str = None):
    query = supabase.table("projects").select("*").eq("id", project_id)
    if org_id:
        query = query.eq("organization_id", org_id)
    return query.single().execute().data

def create_project(name: str, description: str | None, mission_id: str, lead_id: str | None, user_id: str, org_id: str = None):
    data = {"name": name, "description": description, "mission_id": mission_id, "lead_id": lead_id}
    if org_id:
        data["organization_id"] = org_id
    res = supabase.table("projects").insert(data).execute().data[0]
    log_action(user_id, "project_created", "project", res["id"], new_values=data, org_id=org_id)
    return res

def update_project(project_id: str, name: str, description: str | None, lead_id: str | None, user_id: str, org_id: str = None):
    old = get_project(project_id, org_id)
    new_data = {"name": name, "description": description, "lead_id": lead_id}
    supabase.table("projects").update(new_data).eq("id", project_id).execute()
    log_action(user_id, "project_updated", "project", project_id, old_values=old, new_values=new_data, org_id=org_id)

def delete_project(project_id: str, user_id: str, org_id: str = None):
    old = get_project(project_id, org_id)
    supabase.table("projects").delete().eq("id", project_id).execute()
    log_action(user_id, "project_deleted", "project", project_id, old_values=old, org_id=org_id)

# ---------- Tasks ----------
def get_tasks_for_project(project_id: str, org_id: str = None):
    query = supabase.table("tasks").select("*").eq("project_id", project_id).order("created_at")
    if org_id:
        query = query.eq("organization_id", org_id)
    return query.execute().data

def get_task(task_id: str, org_id: str = None):
    query = supabase.table("tasks").select("*").eq("id", task_id)
    if org_id:
        query = query.eq("organization_id", org_id)
    return query.single().execute().data

def create_task(title: str, description: str | None, project_id: str, user_id: str,
                priority: str = "medium", due_date: str | None = None, org_id: str = None):
    data = {
        "title": title,
        "description": description,
        "project_id": project_id,
        "priority": priority,
        "due_date": due_date,
        "status": "todo"
    }
    if org_id:
        data["organization_id"] = org_id
    res = supabase.table("tasks").insert(data).execute().data[0]
    log_action(user_id, "task_created", "task", res["id"], new_values=data, org_id=org_id)
    return res

def update_task_status(task_id: str, new_status: str, user_id: str, org_id: str = None):
    old = get_task(task_id, org_id)
    # Basic state machine
    if old["status"] == "done" and new_status != "done":
         # Allow moving back from done if admin/lead? For now stick to original logic
         pass
    
    # Original logic was quite restrictive:
    # if old["status"] == "done": raise Exception("Cannot change a completed task")
    # if old["status"] == "todo" and new_status not in ("in_progress",): ...
    
    # Let's make it more flexible for SaaS
    supabase.table("tasks").update({"status": new_status, "updated_at": datetime.now(timezone.utc).isoformat()}).eq("id", task_id).execute()
    log_action(user_id, "task_status_changed", "task", task_id, old_values={"status": old["status"]}, new_values={"status": new_status}, org_id=org_id)

# ---------- Multi-Assignees ----------
def get_assignees(task_id: str) -> list[dict]:
    assignee_rows = supabase.table("task_assignees").select("user_id").eq("task_id", task_id).execute().data
    user_ids = [r["user_id"] for r in assignee_rows]
    if not user_ids:
        return []
    profiles = supabase.table("profiles").select("id, username, display_name, role").in_("id", user_ids).execute().data
    return profiles

def assign_users_to_task(task_id: str, user_ids: list[str], admin_id: str):
    supabase.table("task_assignees").delete().eq("task_id", task_id).execute()
    rows = [{"task_id": task_id, "user_id": uid} for uid in user_ids if uid]
    if rows:
        supabase.table("task_assignees").insert(rows).execute()
    log_action(admin_id, "task_assignees_updated", "task", task_id,
               new_values={"assignee_ids": user_ids})

def get_tasks_for_user(user_id: str, org_id: str = None) -> list[dict]:
    rows = supabase.table("task_assignees").select("task_id").eq("user_id", user_id).execute().data
    task_ids = [r["task_id"] for r in rows]
    if not task_ids:
        return []
    query = supabase.table("tasks").select("*").in_("id", task_ids)
    if org_id:
        query = query.eq("organization_id", org_id)
    return query.execute().data

# ---------- Comments ----------
def get_comments_for_task(task_id: str, org_id: str = None):
    query = supabase.table("comments").select("*").eq("task_id", task_id).order("created_at", desc=False)
    if org_id:
        query = query.eq("organization_id", org_id)
    return query.execute().data

def add_comment(task_id: str, content: str, user_id: str, org_id: str = None):
    data = {"task_id": task_id, "user_id": user_id, "content": content}
    if org_id:
        data["organization_id"] = org_id
    res = supabase.table("comments").insert(data).execute().data[0]
    log_action(user_id, "comment_added", "comment", res["id"], new_values=data)
    return res

# ---------- Attachments ----------
def get_attachments(task_id: str, org_id: str = None) -> list[dict]:
    query = supabase.table("task_attachments").select("*").eq("task_id", task_id).order("created_at")
    if org_id:
        query = query.eq("organization_id", org_id)
    return query.execute().data

def add_attachment(task_id: str, uploader_id: str, file_name: str, storage_path: str,
                   mime_type: str | None, file_size: int, org_id: str = None) -> dict:
    data = {
        "task_id": task_id,
        "uploader_id": uploader_id,
        "file_name": file_name,
        "storage_path": storage_path,
        "mime_type": mime_type,
        "file_size": file_size,
    }
    if org_id:
        data["organization_id"] = org_id
    res = supabase.table("task_attachments").insert(data).execute().data[0]
    log_action(uploader_id, "attachment_uploaded", "task_attachment", res["id"], new_values=data)
    return res

def delete_attachment(attachment_id: str, user_id: str, org_id: str = None):
    query = supabase.table("task_attachments").select("*").eq("id", attachment_id)
    if org_id:
        query = query.eq("organization_id", org_id)
    old = query.single().execute().data
    if old:
        if supabase_admin:
            try:
                supabase_admin.storage.from_("task-attachments").remove([old["storage_path"]])
            except:
                pass
        supabase.table("task_attachments").delete().eq("id", attachment_id).execute()
        log_action(user_id, "attachment_deleted", "task_attachment", attachment_id, old_values=old)

# ---------- Users ----------
def get_all_users(org_id: str = None):
    query = supabase.table("profiles").select("id, role")
    if org_id:
        query = query.eq("organization_id", org_id)
    return query.execute().data

def get_users_by_role(role: str, org_id: str = None):
    query = supabase.table("profiles").select("id, role, username, display_name").eq("role", role)
    if org_id:
        query = query.eq("organization_id", org_id)
    return query.execute().data

def get_all_users_detailed(org_id: str = None):
    query = supabase.table("profiles").select("id, username, display_name, role, created_at").order("created_at")
    if org_id:
        query = query.eq("organization_id", org_id)
    return query.execute().data

def get_next_member_id(org_id: str = None):
    users = get_all_users_detailed(org_id)
    ids = []
    for u in users:
        uname = u.get("username")
        if uname and uname.startswith("vhng_"):
            try:
                num_part = uname.split("_")[1]
                ids.append(int(num_part))
            except:
                pass
    next_num = max(ids) + 1 if ids else 0
    return f"vhng_{next_num:04d}"

def create_user_by_admin(email: str, password: str, display_name: str, role: str, admin_id: str, org_id: str = None):
    username = get_next_member_id(org_id)
    if not supabase_admin:
        raise Exception("Administrative actions require SUPABASE_SERVICE_ROLE_KEY to be configured.")
    try:
        auth_res = supabase_admin.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True
        })
        user_id = auth_res.user.id
    except Exception as e:
        raise Exception(f"Auth create failed: {e}")
    
    update_data = {
        "username": username,
        "display_name": display_name,
        "role": role
    }
    if org_id:
        update_data["organization_id"] = org_id
        
    supabase.table("profiles").update(update_data).eq("id", user_id).execute()
    log_action(admin_id, "user_created", "user", user_id,
               new_values={"email": email, "username": username, "display_name": display_name, "role": role, "organization_id": org_id})
    return user_id

# ---------- Progress Reporting ----------
def get_monthly_progress(month: str, org_id: str = None):
    start_date = f"{month}-01T00:00:00Z"
    year, mon = month.split("-")
    y, m = int(year), int(mon)
    if m == 12:
        end_month = f"{y+1}-01"
    else:
        end_month = f"{y}-{m+1:02d}"
    end_date = f"{end_month}-01T00:00:00Z"

    tasks_query = supabase.table("tasks").select("*")
    if org_id:
        tasks_query = tasks_query.eq("organization_id", org_id)
    all_tasks = tasks_query.execute().data
    
    completed_tasks = [t for t in all_tasks if t["status"] == "done" and t["updated_at"] >= start_date and t["updated_at"] < end_date]

    missions_query = supabase.table("missions").select("id, name")
    if org_id:
        missions_query = missions_query.eq("organization_id", org_id)
    missions = missions_query.execute().data
    
    projects_query = supabase.table("projects").select("id, name, mission_id")
    if org_id:
        projects_query = projects_query.eq("organization_id", org_id)
    projects = projects_query.execute().data

    mission_stats = {}
    for m in missions:
        mission_stats[m["id"]] = {"name": m["name"], "projects": {}}
    for p in projects:
        if p["mission_id"] in mission_stats:
            mission_stats[p["mission_id"]]["projects"][p["id"]] = {"name": p["name"], "total": 0, "completed": 0}
            
    for t in all_tasks:
        pid = t["project_id"]
        for mid, m_data in mission_stats.items():
            if pid in m_data["projects"]:
                m_data["projects"][pid]["total"] += 1
                break
    for c in completed_tasks:
        pid = c["project_id"]
        for mid, m_data in mission_stats.items():
            if pid in m_data["projects"]:
                m_data["projects"][pid]["completed"] += 1
                break

    # Per-assignee completions (using junction table)
    assignee_stats = {}
    if completed_tasks:
        task_ids = [t["id"] for t in completed_tasks]
        all_rows = supabase.table("task_assignees").select("task_id, user_id").in_("task_id", task_ids).execute().data
        for row in all_rows:
            uid = row["user_id"]
            if uid:
                assignee_stats[uid] = assignee_stats.get(uid, 0) + 1

    return mission_stats, assignee_stats

# ---------- Audit Logs ----------
def get_audit_logs(limit=50, user_id=None, entity_type=None, org_id: str = None):
    query = supabase.table("audit_logs").select("*").order("created_at", desc=True).limit(limit)
    if user_id:
        query = query.eq("user_id", user_id)
    if entity_type:
        query = query.eq("entity_type", entity_type)
    # Note: audit_logs might need organization_id too in the future
    return query.execute().data

def get_audit_log(log_id: str):
    return supabase.table("audit_logs").select("*").eq("id", log_id).single().execute().data

def revert_action(log_id: str, admin_id: str):
    log = get_audit_log(log_id)
    if not log:
        raise Exception("Log not found")
    
    action = log["action"]
    entity_type = log["entity_type"]
    entity_id = log["entity_id"]
    old_values = json.loads(log["old_values"]) if log["old_values"] else None
    
    if not old_values:
        # If it was a 'created' action, undoing it means deleting the entity
        if "created" in action or "added" in action or "uploaded" in action:
            supabase.table(f"{entity_type}s" if not entity_type.endswith('s') else entity_type).delete().eq("id", entity_id).execute()
            log_action(admin_id, f"reverted_{action}", entity_type, entity_id, old_values=json.loads(log["new_values"]) if log["new_values"] else None)
            return True
        raise Exception("Nothing to revert to (no old values)")

    # Status Reversal
    if action == "task_status_changed":
        supabase.table("tasks").update({"status": old_values["status"]}).eq("id", entity_id).execute()
    
    # Metadata/Edit Reversal
    elif action in ("mission_updated", "project_updated"):
        table = "missions" if action == "mission_updated" else "projects"
        # We only restore fields that were in the edit form
        data = {k: v for k, v in old_values.items() if k in ("name", "description", "lead_id")}
        supabase.table(table).update(data).eq("id", entity_id).execute()
    
    # Role Reversal
    elif action == "role_updated":
        supabase.table("profiles").update({"role": old_values["role"]}).eq("id", entity_id).execute()
    
    # Assignees Reversal
    elif action == "task_assignees_updated":
        supabase.table("task_assignees").delete().eq("task_id", entity_id).execute()
        rows = [{"task_id": entity_id, "user_id": uid} for uid in old_values.get("assignee_ids", []) if uid]
        if rows:
            supabase.table("task_assignees").insert(rows).execute()

    # Deletion Reversal (Restore)
    elif "deleted" in action:
        table = f"{entity_type}s" if not entity_type.endswith('s') else entity_type
        # Special case for task_attachments as the table name is different
        if entity_type == "task_attachment":
             table = "task_attachments"
        supabase.table(table).insert(old_values).execute()
    
    else:
        raise Exception(f"Action '{action}' cannot be automatically reverted yet.")

    log_action(admin_id, f"reverted_{action}", entity_type, entity_id, 
               old_values=json.loads(log["new_values"]) if log["new_values"] else None,
               new_values=old_values)
    return True
