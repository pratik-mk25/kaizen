from datetime import datetime, timezone
from database import supabase, supabase_admin
import uuid
import json

def _get_client():
    return supabase

def log_action(user_id: str, action: str, entity_type: str, entity_id: str,
               old_values: dict | None = None, new_values: dict | None = None):
    client = _get_client()
    try:
        data = {
            "user_id": user_id,
            "action": action,
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "old_values": json.dumps(old_values) if old_values else None,
            "new_values": json.dumps(new_values) if new_values else None,
        }

        client.table("audit_logs").insert(data).execute()
    except Exception as e:
        print(f"DEBUG: Failed to log action {action}: {e}")

# ---------- Missions ----------
def get_all_missions():
    query = _get_client().table("missions").select("*").order("created_at", desc=False)
    return query.execute().data

def get_mission(mission_id: str):
    query = _get_client().table("missions").select("*").eq("id", mission_id)
    return query.single().execute().data

def create_mission(name: str, description: str | None, user_id: str):
    data = {"name": name, "description": description}
    res = _get_client().table("missions").insert(data).execute().data[0]
    log_action(user_id, "mission_created", "mission", res["id"], new_values=data)
    return res

def update_mission(mission_id: str, name: str, description: str | None, user_id: str):
    old = get_mission(mission_id)
    new_data = {"name": name, "description": description}
    _get_client().table("missions").update(new_data).eq("id", mission_id).execute()
    log_action(user_id, "mission_updated", "mission", mission_id, old_values=old, new_values=new_data)

def delete_mission(mission_id: str, user_id: str):
    old = get_mission(mission_id)
    _get_client().table("missions").delete().eq("id", mission_id).execute()
    log_action(user_id, "mission_deleted", "mission", mission_id, old_values=old)

# ---------- Projects ----------
def get_projects_for_mission(mission_id: str):
    query = _get_client().table("projects").select("*").eq("mission_id", mission_id).order("created_at")
    return query.execute().data

def get_project(project_id: str):
    query = _get_client().table("projects").select("*").eq("id", project_id)
    return query.single().execute().data

def create_project(name: str, description: str | None, mission_id: str, lead_id: str | None, user_id: str):
    data = {"name": name, "description": description, "mission_id": mission_id, "lead_id": lead_id}
    res = _get_client().table("projects").insert(data).execute().data[0]
    log_action(user_id, "project_created", "project", res["id"], new_values=data)
    return res

def update_project(project_id: str, name: str, description: str | None, lead_id: str | None, user_id: str):
    old = get_project(project_id)
    new_data = {"name": name, "description": description, "lead_id": lead_id}
    _get_client().table("projects").update(new_data).eq("id", project_id).execute()
    log_action(user_id, "project_updated", "project", project_id, old_values=old, new_values=new_data)

def delete_project(project_id: str, user_id: str):
    old = get_project(project_id)
    _get_client().table("projects").delete().eq("id", project_id).execute()
    log_action(user_id, "project_deleted", "project", project_id, old_values=old)

# ---------- Tasks ----------
def get_tasks_for_project(project_id: str):
    query = _get_client().table("tasks").select("*").eq("project_id", project_id).order("created_at")
    return query.execute().data

def get_task(task_id: str):
    query = _get_client().table("tasks").select("*").eq("id", task_id)
    return query.single().execute().data

def create_task(title: str, description: str | None, project_id: str, user_id: str,
                priority: str = "medium", due_date: str | None = None):
    data = {
        "title": title,
        "description": description,
        "project_id": project_id,
        "priority": priority,
        "due_date": due_date,
        "status": "todo"
    }
    client = supabase
    res = client.table("tasks").insert(data).execute().data[0]
    log_action(user_id, "task_created", "task", res["id"], new_values=data)
    return res

def update_task_status(task_id: str, new_status: str, user_id: str):
    old = get_task(task_id)
    client = supabase
    client.table("tasks").update({"status": new_status, "updated_at": datetime.now(timezone.utc).isoformat()}).eq("id", task_id).execute()
    log_action(user_id, "task_status_changed", "task", task_id, old_values={"status": old["status"]}, new_values={"status": new_status})

def update_task(task_id: str, title: str, description: str | None, priority: str, due_date: str | None, user_id: str):
    old = get_task(task_id)
    new_data = {
        "title": title,
        "description": description,
        "priority": priority,
        "due_date": due_date,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    _get_client().table("tasks").update(new_data).eq("id", task_id).execute()
    log_action(user_id, "task_updated", "task", task_id, old_values=old, new_values=new_data)

def delete_task(task_id: str, user_id: str):
    old = get_task(task_id)
    _get_client().table("tasks").delete().eq("id", task_id).execute()
    log_action(user_id, "task_deleted", "task", task_id, old_values=old)

# ---------- Multi-Assignees ----------
def get_assignees(task_id: str) -> list[dict]:
    assignee_rows = _get_client().table("task_assignees").select("user_id").eq("task_id", task_id).execute().data
    user_ids = [r["user_id"] for r in assignee_rows]
    if not user_ids:
        return []
    profiles = _get_client().table("profiles").select("id, username, display_name, role").in_("id", user_ids).execute().data
    return profiles

def assign_users_to_task(task_id: str, user_ids: list[str], admin_id: str):
    _get_client().table("task_assignees").delete().eq("task_id", task_id).execute()
    rows = [{"task_id": task_id, "user_id": uid} for uid in user_ids if uid]
    if rows:
        _get_client().table("task_assignees").insert(rows).execute()
    log_action(admin_id, "task_assignees_updated", "task", task_id,
               new_values={"assignee_ids": user_ids})

def get_tasks_for_user(user_id: str) -> list[dict]:
    rows = _get_client().table("task_assignees").select("task_id").eq("user_id", user_id).execute().data
    task_ids = [r["task_id"] for r in rows]
    if not task_ids:
        return []
    query = _get_client().table("tasks").select("*").in_("id", task_ids)
    return query.execute().data

# ---------- Comments ----------
def get_comments_for_task(task_id: str):
    query = _get_client().table("comments").select("*").eq("task_id", task_id).order("created_at", desc=False)
    return query.execute().data

def add_comment(task_id: str, content: str, user_id: str):
    data = {"task_id": task_id, "user_id": user_id, "content": content}
    res = _get_client().table("comments").insert(data).execute().data[0]
    log_action(user_id, "comment_added", "comment", res["id"], new_values=data)
    return res

# ---------- Attachments ----------
def get_attachments(task_id: str) -> list[dict]:
    query = _get_client().table("task_attachments").select("*").eq("task_id", task_id).order("created_at")
    return query.execute().data

def add_attachment(task_id: str, uploader_id: str, file_name: str, storage_path: str,
                   mime_type: str | None, file_size: int) -> dict:
    data = {
        "task_id": task_id,
        "uploader_id": uploader_id,
        "file_name": file_name,
        "storage_path": storage_path,
        "mime_type": mime_type,
        "file_size": file_size,
    }
    res = _get_client().table("task_attachments").insert(data).execute().data[0]
    log_action(uploader_id, "attachment_uploaded", "task_attachment", res["id"], new_values=data)
    return res

def delete_attachment(attachment_id: str, user_id: str):
    query = _get_client().table("task_attachments").select("*").eq("id", attachment_id)
    old = query.single().execute().data
    if old:
        _get_client().table("task_attachments").delete().eq("id", attachment_id).execute()
        log_action(user_id, "attachment_deleted", "task_attachment", attachment_id, old_values=old)

# ---------- Users ----------
def get_all_users():
    query = _get_client().table("profiles").select("id, role")
    return query.execute().data

def get_users_by_role(role: str):
    query = _get_client().table("profiles").select("id, role, username, display_name").eq("role", role)
    return query.execute().data

def get_all_users_detailed():
    client = supabase
    query = client.table("profiles").select("id, username, display_name, role, email, created_at").order("created_at")
    return query.execute().data

# ---------- Progress Reporting ----------
def get_monthly_progress(month: str):
    start_date = f"{month}-01T00:00:00Z"
    year, mon = month.split("-")
    y, m = int(year), int(mon)
    if m == 12:
        end_month = f"{y+1}-01"
    else:
        end_month = f"{y}-{m+1:02d}"
    end_date = f"{end_month}-01T00:00:00Z"

    tasks_query = _get_client().table("tasks").select("*")
    all_tasks = tasks_query.execute().data
    
    completed_tasks = [t for t in all_tasks if t["status"] == "done" and t["updated_at"] >= start_date and t["updated_at"] < end_date]

    missions_query = _get_client().table("missions").select("id, name")
    missions = missions_query.execute().data
    
    projects_query = _get_client().table("projects").select("id, name, mission_id")
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
        all_rows = _get_client().table("task_assignees").select("task_id, user_id").in_("task_id", task_ids).execute().data
        for row in all_rows:
            uid = row["user_id"]
            if uid:
                assignee_stats[uid] = assignee_stats.get(uid, 0) + 1

    return mission_stats, assignee_stats

# ---------- Audit Logs ----------
def get_audit_logs(limit=50, user_id=None, entity_type=None):
    query = _get_client().table("audit_logs").select("*").order("created_at", desc=True).limit(limit)
    if user_id:
        query = query.eq("user_id", user_id)
    if entity_type:
        query = query.eq("entity_type", entity_type)
    return query.execute().data

def get_audit_log(log_id: str):
    return _get_client().table("audit_logs").select("*").eq("id", log_id).single().execute().data

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
            _get_client().table(f"{entity_type}s" if not entity_type.endswith('s') else entity_type).delete().eq("id", entity_id).execute()
            log_action(admin_id, f"reverted_{action}", entity_type, entity_id, old_values=json.loads(log["new_values"]) if log["new_values"] else None)
            return True
        raise Exception("Nothing to revert to (no old values)")

    # Status Reversal
    if action == "task_status_changed":
        _get_client().table("tasks").update({"status": old_values["status"]}).eq("id", entity_id).execute()
    
    # Metadata/Edit Reversal
    elif action in ("mission_updated", "project_updated", "task_updated"):
        if action == "mission_updated": table = "missions"
        elif action == "project_updated": table = "projects"
        else: table = "tasks"
        
        # We only restore fields that were in the edit form
        allowed_fields = ("name", "description", "lead_id", "title", "priority", "due_date")
        data = {k: v for k, v in old_values.items() if k in allowed_fields}
        _get_client().table(table).update(data).eq("id", entity_id).execute()
    
    # Role Reversal
    elif action == "role_updated":
        _get_client().table("profiles").update({"role": old_values["role"]}).eq("id", entity_id).execute()
    
    # Assignees Reversal
    elif action == "task_assignees_updated":
        _get_client().table("task_assignees").delete().eq("task_id", entity_id).execute()
        rows = [{"task_id": entity_id, "user_id": uid} for uid in old_values.get("assignee_ids", []) if uid]
        if rows:
            _get_client().table("task_assignees").insert(rows).execute()

    # Deletion Reversal (Restore)
    elif "deleted" in action:
        table = f"{entity_type}s" if not entity_type.endswith('s') else entity_type
        if entity_type == "user":
            table = "profiles"
        elif entity_type == "task_attachment":
             table = "task_attachments"
        _get_client().table(table).insert(old_values).execute()
    
    else:
        raise Exception(f"Action '{action}' cannot be automatically reverted yet.")

    log_action(admin_id, f"reverted_{action}", entity_type, entity_id, 
               old_values=json.loads(log["new_values"]) if log["new_values"] else None,
               new_values=old_values)
    return True

# ==================== EQUIPMENT ====================

def get_all_equipment():
    query = _get_client().table("equipment").select("*").order("created_at", desc=True)
    return query.execute().data

def get_equipment(equipment_id: str):
    query = _get_client().table("equipment").select("*").eq("id", equipment_id)
    return query.single().execute().data

def create_equipment(name: str, equipment_type: str, serial_number: str | None, brand: str | None,
                     model: str | None, status: str, condition: str, purchase_date: str | None,
                     purchase_price: float | None, assigned_to: str | None, notes: str | None,
                     user_id: str):
    data = {k: v for k, v in {
        "name": name, "equipment_type": equipment_type, "serial_number": serial_number,
        "brand": brand, "model": model, "status": status, "condition": condition,
        "purchase_date": purchase_date, "purchase_price": purchase_price,
        "assigned_to": assigned_to, "notes": notes,
    }.items() if v is not None}
    res = _get_client().table("equipment").insert(data).execute().data[0]
    log_action(user_id, "equipment_created", "equipment", res["id"], new_values=data)
    return res

def update_equipment(equipment_id: str, name: str, equipment_type: str, brand: str | None,
                     model: str | None, serial_number: str | None, status: str, condition: str,
                     purchase_date: str | None, purchase_price: float | None, assigned_to: str | None,
                     notes: str | None, user_id: str):
    old = get_equipment(equipment_id)
    new_data = {k: v for k, v in {
        "name": name, "equipment_type": equipment_type, "brand": brand, "model": model,
        "serial_number": serial_number, "status": status, "condition": condition,
        "purchase_date": purchase_date, "purchase_price": purchase_price,
        "assigned_to": assigned_to, "notes": notes, "updated_at": datetime.now(timezone.utc).isoformat()
    }.items() if v is not None}
    _get_client().table("equipment").update(new_data).eq("id", equipment_id).execute()
    log_action(user_id, "equipment_updated", "equipment", equipment_id, old_values=old, new_values=new_data)

def delete_equipment(equipment_id: str, user_id: str):
    old = get_equipment(equipment_id)
    _get_client().table("equipment").delete().eq("id", equipment_id).execute()
    log_action(user_id, "equipment_deleted", "equipment", equipment_id, old_values=old)

# ==================== EQUIPMENT MAINTENANCE ====================

def get_maintenance_logs(equipment_id: str):
    query = _get_client().table("equipment_maintenance_logs").select("*").eq("equipment_id", equipment_id).order("maintenance_date", desc=True)
    return query.execute().data

def add_maintenance_log(equipment_id: str, description: str, maintenance_date: str, performed_by: str | None,
                        cost: float, notes: str | None, user_id: str):
    data = {"equipment_id": equipment_id, "description": description, "maintenance_date": maintenance_date,
            "performed_by": performed_by, "cost": cost, "notes": notes}
    res = _get_client().table("equipment_maintenance_logs").insert(data).execute().data[0]
    log_action(user_id, "maintenance_added", "equipment_maintenance", res["id"], new_values=data)
    return res

def delete_maintenance_log(log_id: str, user_id: str):
    query = _get_client().table("equipment_maintenance_logs").select("*").eq("id", log_id)
    old = query.single().execute().data
    if old:
        _get_client().table("equipment_maintenance_logs").delete().eq("id", log_id).execute()
        log_action(user_id, "maintenance_deleted", "equipment_maintenance", log_id, old_values=old)

# ==================== INVENTORY ====================

def get_all_inventory():
    query = _get_client().table("inventory_items").select("*").order("name")
    return query.execute().data

def get_inventory_item(item_id: str):
    query = _get_client().table("inventory_items").select("*").eq("id", item_id)
    return query.single().execute().data

def create_inventory_item(name: str, category: str, quantity: int, min_threshold: int, unit: str,
                          location: str | None, notes: str | None, user_id: str):
    data = {k: v for k, v in {"name": name, "category": category, "quantity": quantity,
            "min_threshold": min_threshold, "unit": unit, "location": location, "notes": notes}.items() if v is not None}
    res = _get_client().table("inventory_items").insert(data).execute().data[0]
    log_action(user_id, "inventory_created", "inventory_item", res["id"], new_values=data)
    return res

def update_inventory_item(item_id: str, name: str, category: str, quantity: int, min_threshold: int,
                           unit: str, location: str | None, notes: str | None, user_id: str):
    old = get_inventory_item(item_id)
    new_data = {k: v for k, v in {"name": name, "category": category, "quantity": quantity,
                "min_threshold": min_threshold, "unit": unit, "location": location,
                "notes": notes, "updated_at": datetime.now(timezone.utc).isoformat()}.items() if v is not None}
    _get_client().table("inventory_items").update(new_data).eq("id", item_id).execute()
    log_action(user_id, "inventory_updated", "inventory_item", item_id, old_values=old, new_values=new_data)

def delete_inventory_item(item_id: str, user_id: str):
    old = get_inventory_item(item_id)
    _get_client().table("inventory_items").delete().eq("id", item_id).execute()
    log_action(user_id, "inventory_deleted", "inventory_item", item_id, old_values=old)

def log_inventory_transaction(item_id: str, change_amount: int, transaction_type: str, reference: str | None,
                              notes: str | None, user_id: str):
    data = {"item_id": item_id, "change_amount": change_amount, "transaction_type": transaction_type,
            "reference": reference, "performed_by": user_id, "notes": notes}
    res = _get_client().table("inventory_transactions").insert(data).execute().data[0]
    log_action(user_id, "inventory_transaction", "inventory_item", item_id, new_values=data)
    return res

def get_inventory_transactions(item_id: str):
    query = _get_client().table("inventory_transactions").select("*").eq("item_id", item_id).order("created_at", desc=True)
    return query.execute().data

# ==================== SKILLS ====================

def get_all_skills():
    query = _get_client().table("skills").select("*").order("name")
    return query.execute().data

def create_skill(name: str, category: str, user_id: str):
    data = {"name": name, "category": category}
    res = _get_client().table("skills").insert(data).execute().data[0]
    log_action(user_id, "skill_created", "skill", res["id"], new_values=data)
    return res

def delete_skill(skill_id: str, user_id: str):
    _get_client().table("skills").delete().eq("id", skill_id).execute()
    log_action(user_id, "skill_deleted", "skill", skill_id)

def get_member_skills(user_id: str):
    rows = _get_client().table("member_skills").select("*, skills(name, category)").eq("user_id", user_id).execute().data
    return rows

def set_member_skill(user_id: str, skill_id: str, proficiency_level: str):
    data = {"user_id": user_id, "skill_id": skill_id, "proficiency_level": proficiency_level, "updated_at": datetime.now(timezone.utc).isoformat()}
    _get_client().table("member_skills").upsert(data, on_conflict="user_id,skill_id").execute()

def remove_member_skill(user_id: str, skill_id: str):
    _get_client().table("member_skills").delete().eq("user_id", user_id).eq("skill_id", skill_id).execute()

# ==================== CERTIFICATIONS ====================

def get_all_certifications():
    query = _get_client().table("certifications").select("*").order("name")
    return query.execute().data

def create_certification(name: str, issuing_body: str | None, user_id: str):
    data = {"name": name, "issuing_body": issuing_body}
    res = _get_client().table("certifications").insert(data).execute().data[0]
    log_action(user_id, "certification_created", "certification", res["id"], new_values=data)
    return res

def delete_certification(cert_id: str, user_id: str):
    _get_client().table("certifications").delete().eq("id", cert_id).execute()
    log_action(user_id, "certification_deleted", "certification", cert_id)

def get_member_certifications(user_id: str):
    rows = _get_client().table("member_certifications").select("*, certifications(name, issuing_body)").eq("user_id", user_id).order("date_obtained", desc=True).execute().data
    return rows

def add_member_certification(member_id: str, certification_id: str, date_obtained: str, expiry_date: str | None,
                             admin_id: str):
    data = {"user_id": member_id, "certification_id": certification_id, "date_obtained": date_obtained,
            "expiry_date": expiry_date, "verification_status": "pending"}
    res = _get_client().table("member_certifications").insert(data).execute().data[0]
    log_action(admin_id, "member_cert_added", "member_certification", res["id"], new_values=data)
    return res

def verify_member_certification(cert_id: str, status: str):
    query = _get_client().table("member_certifications").update({"verification_status": status}).eq("id", cert_id)
    query.execute()

def delete_member_certification(cert_id: str, user_id: str):
    _get_client().table("member_certifications").delete().eq("id", cert_id).execute()
    log_action(user_id, "member_cert_deleted", "member_certification", cert_id)

# ==================== ATTENDANCE ====================

def get_attendance(limit: int = 100):
    query = _get_client().table("attendance").select("*").order("event_date", desc=True).limit(limit)
    return query.execute().data

def get_attendance_for_member(user_id: str):
    query = _get_client().table("attendance").select("*").eq("user_id", user_id).order("event_date", desc=True)
    return query.execute().data

def get_active_checkin(user_id: str, event_date: str):
    import json
    rows = _get_client().table("attendance").select("*").eq("user_id", user_id).eq("event_date", event_date).eq("status", "present").execute().data
    for r in rows:
        notes = {}
        if r.get("notes"):
            try:
                notes = json.loads(r["notes"])
            except (json.JSONDecodeError, TypeError):
                notes = {}
        if "in" in notes and "out" not in notes:
            return r
    return None

def add_attendance(user_id: str, event_name: str, event_date: str, status: str, notes: str | None,
                   recorder_id: str):
    data = {"user_id": user_id, "event_name": event_name, "event_date": event_date, "status": status, "notes": notes}
    res = _get_client().table("attendance").insert(data).execute().data[0]
    log_action(recorder_id, "attendance_added", "attendance", res["id"], new_values=data)
    return res

def delete_attendance(attendance_id: str, user_id: str):
    _get_client().table("attendance").delete().eq("id", attendance_id).execute()
    log_action(user_id, "attendance_deleted", "attendance", attendance_id)

def update_attendance(attendance_id: str, event_name: str, event_date: str, status: str, notes: str | None, user_id: str):
    old = _get_client().table("attendance").select("*").eq("id", attendance_id).execute().data[0]
    data = {"event_name": event_name, "event_date": event_date, "status": status, "notes": notes}
    _get_client().table("attendance").update(data).eq("id", attendance_id).execute()
    log_action(user_id, "attendance_updated", "attendance", attendance_id, old_values=old, new_values=data)
    log_action(user_id, "attendance_updated", "attendance", attendance_id, old_values=old, new_values=data)

def quick_toggle_attendance(user_id: str, event_date: str, recorder_id: str):
    active = get_active_checkin(user_id, event_date)
    now = datetime.now().strftime("%H:%M:%S")
    if active:
        import json
        existing_notes = {}
        if active.get("notes"):
            try:
                existing_notes = json.loads(active["notes"])
            except (json.JSONDecodeError, TypeError):
                existing_notes = {}
        existing_notes["out"] = now
        _get_client().table("attendance").update({
            "notes": json.dumps(existing_notes)
        }).eq("id", active["id"]).execute()
        log_action(recorder_id, "attendance_checked_out", "attendance", active["id"],
                   new_values={"out_time": now})
        return {"action": "checked_out", "record": active}
    else:
        import json
        notes = json.dumps({"in": now})
        data = {"user_id": user_id, "event_name": "Club Session", "event_date": event_date,
                "status": "present", "notes": notes}
        res = _get_client().table("attendance").insert(data).execute().data[0]
        log_action(recorder_id, "attendance_checked_in", "attendance", res["id"], new_values=data)
        return {"action": "checked_in", "record": res}

# ==================== BUDGET ====================

def get_budget_categories():
    query = _get_client().table("budget_categories").select("*").order("name")
    return query.execute().data

def create_budget_category(name: str, allocated_amount: float, user_id: str):
    data = {"name": name, "allocated_amount": allocated_amount}
    res = _get_client().table("budget_categories").insert(data).execute().data[0]
    log_action(user_id, "budget_category_created", "budget_category", res["id"], new_values=data)
    return res

def update_budget_category(cat_id: str, name: str, allocated_amount: float, user_id: str):
    old_data = _get_client().table("budget_categories").select("*").eq("id", cat_id)
    old = old_data.single().execute().data
    new_data = {"name": name, "allocated_amount": allocated_amount}
    _get_client().table("budget_categories").update(new_data).eq("id", cat_id).execute()
    log_action(user_id, "budget_category_updated", "budget_category", cat_id, old_values=old, new_values=new_data)

def delete_budget_category(cat_id: str, user_id: str):
    _get_client().table("budget_categories").delete().eq("id", cat_id).execute()
    log_action(user_id, "budget_category_deleted", "budget_category", cat_id)

def get_transactions(limit: int = 200):
    query = _get_client().table("transactions").select("*, budget_categories(name)").order("transaction_date", desc=True).limit(limit)
    return query.execute().data

def create_transaction(description: str, amount: float, type_: str, category_id: str | None,
                       transaction_date: str, notes: str | None, user_id: str):
    data = {"description": description, "amount": amount, "type": type_, "category_id": category_id,
           "transaction_date": transaction_date, "recorded_by": user_id, "notes": notes}
    res = _get_client().table("transactions").insert(data).execute().data[0]
    log_action(user_id, "transaction_created", "transaction", res["id"], new_values=data)
    return res

def update_transaction(txn_id: str, description: str, amount: float, type_: str, category_id: str | None,
                      transaction_date: str, notes: str | None, user_id: str):
    old = _get_client().table("transactions").select("*").eq("id", txn_id)
    old = old.single().execute().data
    new_data = {"description": description, "amount": amount, "type": type_, "category_id": category_id,
                "transaction_date": transaction_date, "notes": notes}
    _get_client().table("transactions").update(new_data).eq("id", txn_id).execute()
    log_action(user_id, "transaction_updated", "transaction", txn_id, old_values=old, new_values=new_data)

def delete_transaction(txn_id: str, user_id: str):
    _get_client().table("transactions").delete().eq("id", txn_id).execute()
    log_action(user_id, "transaction_deleted", "transaction", txn_id)

# ==================== DUES ====================

def get_dues():
    query = _get_client().table("dues").select("*, profiles(display_name, username)").order("due_date", desc=True)
    return query.execute().data

def create_dues_entry(member_id: str, amount: float, period: str, due_date: str, notes: str | None,
                     user_id: str):
    data = {"member_id": member_id, "amount": amount, "period": period, "due_date": due_date,
            "status": "unpaid", "notes": notes}
    res = _get_client().table("dues").insert(data).execute().data[0]
    log_action(user_id, "dues_created", "dues", res["id"], new_values=data)
    return res

def mark_dues_paid(dues_id: str, paid_date: str, user_id: str):
    old = _get_client().table("dues").select("*").eq("id", dues_id)
    old = old.single().execute().data
    new_data = {"status": "paid", "paid_date": paid_date, "updated_at": datetime.now(timezone.utc).isoformat()}
    _get_client().table("dues").update(new_data).eq("id", dues_id).execute()
    log_action(user_id, "dues_paid", "dues", dues_id, old_values=old, new_values=new_data)

def delete_dues(dues_id: str, user_id: str):
    _get_client().table("dues").delete().eq("id", dues_id).execute()
    log_action(user_id, "dues_deleted", "dues", dues_id)

# ==================== DOCUMENTS ====================

def get_all_documents(category: str = None):
    query = _get_client().table("documents").select("*").order("updated_at", desc=True)
    if category: query = query.eq("category", category)
    return query.execute().data

def get_document(doc_id: str):
    query = _get_client().table("documents").select("*").eq("id", doc_id)
    return query.single().execute().data

def create_document(title: str, content: str, category: str, tags: list[str] | None, published: bool,
                  user_id: str):
    data = {k: v for k, v in {"title": title, "content": content, "category": category,
            "tags": tags or [], "published": published, "created_by": user_id}.items() if v is not None}
    res = _get_client().table("documents").insert(data).execute().data[0]
    log_action(user_id, "document_created", "document", res["id"], new_values=data)
    return res

def update_document(doc_id: str, title: str, content: str, category: str, tags: list[str] | None,
                    published: bool, user_id: str):
    old = get_document(doc_id)
    new_data = {k: v for k, v in {"title": title, "content": content, "category": category,
                "tags": tags or [], "published": published,
                "updated_at": datetime.now(timezone.utc).isoformat()}.items() if v is not None}
    _get_client().table("documents").update(new_data).eq("id", doc_id).execute()
    log_action(user_id, "document_updated", "document", doc_id, old_values=old, new_values=new_data)

def delete_document(doc_id: str, user_id: str):
    old = get_document(doc_id)
    _get_client().table("documents").delete().eq("id", doc_id).execute()
    log_action(user_id, "document_deleted", "document", doc_id, old_values=old)

def get_organization():
    rows = supabase.table("organizations").select("*").order("created_at", desc=True).limit(1).execute().data
    if rows:
        return rows[0]
    supabase.table("organizations").insert({"name": "Drone Club OS", "discord_webhook_url": None}).execute()
    rows = supabase.table("organizations").select("*").order("created_at", desc=True).limit(1).execute().data
    return rows[0] if rows else {"id": "N/A", "name": "Drone Club OS", "discord_webhook_url": None}

def update_organization_settings(name: str, discord_webhook_url: str, user_id: str):
    org = get_organization()
    supabase.table("organizations").update({"name": name, "discord_webhook_url": discord_webhook_url}).eq("id", org["id"]).execute()
    log_action(user_id, "organization_updated", "organization", org["id"], old_values=org, new_values={"name": name, "discord_webhook_url": discord_webhook_url})

def get_kiosk_secret():
    org = get_organization()
    return org.get("kiosk_secret", "")

def set_kiosk_secret(secret: str, user_id: str):
    org = get_organization()
    supabase.table("organizations").update({"kiosk_secret": secret}).eq("id", org["id"]).execute()
    log_action(user_id, "kiosk_secret_updated", "organization", org["id"], new_values={"kiosk_secret": "***"})

def create_user_by_admin(email: str, password: str, display_name: str, role: str, admin_id: str):
    try:
        user_resp = supabase_admin.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True
        })
        new_user = user_resp.user
    except Exception as e:
        raise Exception(f"Failed to create auth user: {e}")
    profile_data = {
        "id": new_user.id,
        "email": email,
        "display_name": display_name,
        "username": email.split("@")[0],
        "role": role,
    }
    supabase.table("profiles").insert(profile_data).execute()
    log_action(admin_id, "user_created", "user", new_user.id, new_values=profile_data)
    return new_user