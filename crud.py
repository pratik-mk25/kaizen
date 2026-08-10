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
    try:
        query = _get_client().table("attendance").select("*").order("event_date", desc=True).limit(limit)
        res = query.execute()
        return res.data if (res and res.data is not None) else []
    except Exception as e:
        print(f"Error in get_attendance: {e}")
        return []

def get_attendance_for_member(user_id: str):
    try:
        query = _get_client().table("attendance").select("*").eq("user_id", user_id).order("event_date", desc=True)
        res = query.execute()
        return res.data if (res and res.data is not None) else []
    except Exception as e:
        print(f"Error in get_attendance_for_member: {e}")
        return []

def get_active_checkin(user_id: str, event_date: str):
    import json
    try:
        res = _get_client().table("attendance").select("*").eq("user_id", user_id).eq("event_date", event_date).eq("status", "present").execute()
        rows = res.data if (res and res.data is not None) else []
        for r in rows:
            notes = {}
            if r.get("notes"):
                try:
                    notes = json.loads(r["notes"])
                except (json.JSONDecodeError, TypeError):
                    notes = {}
            if isinstance(notes, dict) and "in" in notes and "out" not in notes:
                return r
    except Exception as e:
        print(f"Error in get_active_checkin: {e}")
    return None

def add_attendance(user_id: str, event_name: str, event_date: str, status: str, notes: str | None,
                   recorder_id: str):
    import json
    ist = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(ist).strftime("%H:%M:%S")

    formatted_notes = notes
    if not notes:
        formatted_notes = json.dumps({"in": now})
    elif isinstance(notes, str) and not (notes.startswith("{") and notes.endswith("}")):
        formatted_notes = json.dumps({"in": now, "info": notes})

    data = {"user_id": user_id, "event_name": event_name, "event_date": event_date, "status": status, "notes": formatted_notes}
    exec_res = _get_client().table("attendance").insert(data).execute()
    res = (exec_res.data[0] if (exec_res and exec_res.data) else data)
    rec_id = res.get("id", "N/A") if isinstance(res, dict) else "N/A"
    try:
        log_action(recorder_id, "attendance_added", "attendance", rec_id, new_values=data)
    except Exception:
        pass
    return res

def delete_attendance(attendance_id: str, user_id: str):
    _get_client().table("attendance").delete().eq("id", attendance_id).execute()
    log_action(user_id, "attendance_deleted", "attendance", attendance_id)

def update_attendance(attendance_id: str, event_name: str, event_date: str, status: str, notes: str | None, user_id: str):
    old_res = _get_client().table("attendance").select("*").eq("id", attendance_id).execute()
    old = old_res.data[0] if (old_res and old_res.data) else {}
    data = {"event_name": event_name, "event_date": event_date, "status": status, "notes": notes}
    _get_client().table("attendance").update(data).eq("id", attendance_id).execute()
    try:
        log_action(user_id, "attendance_updated", "attendance", attendance_id, old_values=old, new_values=data)
    except Exception:
        pass

def quick_toggle_attendance(user_id: str, event_date: str, recorder_id: str):
    try:
        active = get_active_checkin(user_id, event_date)
        ist = timezone(timedelta(hours=5, minutes=30))
        now = datetime.now(ist).strftime("%H:%M:%S")
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
            try:
                log_action(recorder_id, "attendance_checked_out", "attendance", active["id"],
                           new_values={"out_time": now})
            except Exception:
                pass
            return {"action": "checked_out", "record": active}
        else:
            import json
            notes = json.dumps({"in": now})
            data = {"user_id": user_id, "event_name": "Club Session", "event_date": event_date,
                    "status": "present", "notes": notes}
            exec_res = _get_client().table("attendance").insert(data).execute()
            res = (exec_res.data[0] if (exec_res and exec_res.data) else data)
            rec_id = res.get("id", "N/A") if isinstance(res, dict) else "N/A"
            try:
                log_action(recorder_id, "attendance_checked_in", "attendance", rec_id, new_values=data)
            except Exception:
                pass
            return {"action": "checked_in", "record": res}
    except Exception as e:
        print(f"Error in quick_toggle_attendance: {e}")
        return {"action": "error", "message": str(e)}

def fix_all_attendance_utc_to_ist(user_id: str):
    try:
        rows = _get_client().table("attendance").select("*").execute().data or []
        updated_count = 0
        for r in rows:
            notes_str = r.get("notes")
            if not notes_str:
                continue
            try:
                notes = json.loads(notes_str)
                modified = False
                for key in ["in", "out"]:
                    if key in notes and notes[key] and isinstance(notes[key], str):
                        val = notes[key]
                        if "AM" in val or "PM" in val or "IST" in val:
                            continue
                        parts = val.split(":")
                        if len(parts) >= 2:
                            hh = int(parts[0])
                            mm = int(parts[1])
                            ss = int(parts[2]) if len(parts) > 2 else 0
                            
                            mm_new = mm + 30
                            hh_add = 0
                            if mm_new >= 60:
                                mm_new -= 60
                                hh_add = 1
                            hh_new = (hh + 5 + hh_add) % 24
                            
                            notes[key] = f"{hh_new:02d}:{mm_new:02d}:{ss:02d}"
                            modified = True
                
                if modified:
                    _get_client().table("attendance").update({
                        "notes": json.dumps(notes)
                    }).eq("id", r["id"]).execute()
                    updated_count += 1
            except Exception as e:
                print(f"Error parsing attendance notes for {r.get('id')}: {e}")
                
        log_action(user_id, "fix_all_attendance_ist", "attendance", "all", new_values={"updated_count": updated_count})
        return updated_count
    except Exception as e:
        print(f"Error in fix_all_attendance_utc_to_ist: {e}")
        return 0

def delete_user_completely(user_id: str, admin_id: str):
    client = _get_client()
    
    # 1. Clean up child table references
    tables_to_delete_by_user = ["attendance", "task_assignees", "comments", "member_skills",
                                "member_certifications", "event_attendees", "audit_logs"]
    for t in tables_to_delete_by_user:
        try:
            client.table(t).delete().eq("user_id", user_id).execute()
        except Exception as e:
            print(f"Cleanup error in {t} for {user_id}: {e}")

    try:
        client.table("equipment_checkouts").delete().eq("borrower_id", user_id).execute()
    except Exception as e:
        print(f"Cleanup error in equipment_checkouts for {user_id}: {e}")

    try:
        client.table("flight_logs").delete().eq("pilot_id", user_id).execute()
    except Exception as e:
        print(f"Cleanup error in flight_logs for {user_id}: {e}")

    # Nullify references in parent tables
    try:
        client.table("projects").update({"lead_id": None}).eq("lead_id", user_id).execute()
    except Exception as e:
        print(f"Cleanup error in projects for {user_id}: {e}")

    try:
        client.table("equipment").update({"assigned_to": None}).eq("assigned_to", user_id).execute()
    except Exception as e:
        print(f"Cleanup error in equipment for {user_id}: {e}")

    try:
        client.table("events").update({"created_by": None}).eq("created_by", user_id).execute()
    except Exception as e:
        print(f"Cleanup error in events for {user_id}: {e}")

    # 2. Delete profile
    client.table("profiles").delete().eq("id", user_id).execute()

    # 3. Delete Supabase Auth user
    try:
        supabase_admin.auth.admin.delete_user(user_id)
    except Exception as e:
        print(f"Cleanup error in supabase_admin delete_user: {e}")

    log_action(admin_id, "user_deleted", "user", user_id)

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

def get_key_holder():
    org = get_organization()
    return org.get("key_holder", "HOD Cabin")

def set_key_holder(holder: str, user_id: str):
    org = get_organization()
    supabase.table("organizations").update({"key_holder": holder}).eq("id", org["id"]).execute()
    log_action(user_id, "key_holder_updated", "organization", org["id"], old_values={"key_holder": org.get("key_holder")}, new_values={"key_holder": holder})


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

# ==================== FLIGHT LOGBOOK & BATTERIES ====================
def get_all_flight_logs():
    try:
        query = _get_client().table("flight_logs").select("*").order("flight_date", desc=True)
        return query.execute().data or []
    except Exception as e:
        print(f"Error fetching flight logs: {e}")
        return []

def create_flight_log(pilot_id: str, equipment_id: str | None, battery_id: str | None,
                      flight_date: str, duration_minutes: int, location: str | None,
                      purpose: str | None, notes: str | None, user_id: str):
    data = {
        "pilot_id": pilot_id,
        "equipment_id": equipment_id,
        "battery_id": battery_id,
        "flight_date": flight_date,
        "duration_minutes": duration_minutes,
        "location": location,
        "purpose": purpose,
        "notes": notes
    }
    res = _get_client().table("flight_logs").insert(data).execute().data[0]
    log_action(user_id, "flight_logged", "flight_log", res["id"], new_values=data)
    
    # Auto-increment battery cycles if battery provided
    if battery_id:
        try:
            increment_battery_cycle(battery_id, user_id)
        except Exception as e:
            print(f"Failed to increment battery cycle: {e}")
            
    return res

def delete_flight_log(log_id: str, user_id: str):
    old = _get_client().table("flight_logs").select("*").eq("id", log_id).single().execute().data
    _get_client().table("flight_logs").delete().eq("id", log_id).execute()
    log_action(user_id, "flight_deleted", "flight_log", log_id, old_values=old)

def get_all_battery_packs():
    try:
        query = _get_client().table("battery_packs").select("*").order("name")
        return query.execute().data or []
    except Exception as e:
        print(f"Error fetching battery packs: {e}")
        return []

def create_battery_pack(name: str, cell_count: str, capacity_mah: int, status: str, notes: str | None, user_id: str):
    data = {
        "name": name,
        "cell_count": cell_count,
        "capacity_mah": capacity_mah,
        "charge_cycles": 0,
        "status": status,
        "notes": notes
    }
    res = _get_client().table("battery_packs").insert(data).execute().data[0]
    log_action(user_id, "battery_created", "battery_pack", res["id"], new_values=data)
    return res

def increment_battery_cycle(battery_id: str, user_id: str):
    b = _get_client().table("battery_packs").select("*").eq("id", battery_id).single().execute().data
    if b:
        new_cycles = (b.get("charge_cycles") or 0) + 1
        _get_client().table("battery_packs").update({"charge_cycles": new_cycles}).eq("id", battery_id).execute()
        log_action(user_id, "battery_cycle_incremented", "battery_pack", battery_id, new_values={"charge_cycles": new_cycles})

def update_battery_status(battery_id: str, status: str, user_id: str):
    _get_client().table("battery_packs").update({"status": status}).eq("id", battery_id).execute()
    log_action(user_id, "battery_status_updated", "battery_pack", battery_id, new_values={"status": status})


# ==================== EQUIPMENT CHECKOUTS ====================
def get_active_checkouts():
    try:
        query = _get_client().table("equipment_checkouts").select("*").is_("returned_at", "null").order("checked_out_at", desc=True)
        return query.execute().data or []
    except Exception as e:
        print(f"Error fetching active checkouts: {e}")
        return []

def get_checkouts_for_equipment(equipment_id: str):
    try:
        query = _get_client().table("equipment_checkouts").select("*").eq("equipment_id", equipment_id).order("checked_out_at", desc=True)
        return query.execute().data or []
    except Exception as e:
        print(f"Error fetching checkouts for equipment: {e}")
        return []

def checkout_equipment(equipment_id: str, borrower_id: str, expected_return_at: str | None,
                       condition: str, notes: str | None, user_id: str):
    data = {
        "equipment_id": equipment_id,
        "borrower_id": borrower_id,
        "expected_return_at": expected_return_at,
        "condition_on_checkout": condition,
        "notes": notes
    }
    res = _get_client().table("equipment_checkouts").insert(data).execute().data[0]
    # Update equipment status to in_use and set assigned_to
    _get_client().table("equipment").update({"status": "in_use", "assigned_to": borrower_id}).eq("id", equipment_id).execute()
    log_action(user_id, "equipment_checked_out", "equipment_checkout", res["id"], new_values=data)
    return res

def return_equipment(checkout_id: str, condition_on_return: str, notes: str | None, user_id: str):
    checkout = _get_client().table("equipment_checkouts").select("*").eq("id", checkout_id).single().execute().data
    if checkout:
        now_iso = datetime.now(timezone.utc).isoformat()
        _get_client().table("equipment_checkouts").update({
            "returned_at": now_iso,
            "condition_on_return": condition_on_return,
            "notes": (checkout.get("notes") or "") + (f"\nReturn Note: {notes}" if notes else "")
        }).eq("id", checkout_id).execute()
        
        # Reset equipment status to available
        _get_client().table("equipment").update({
            "status": "available",
            "condition": condition_on_return,
            "assigned_to": None
        }).eq("id", checkout["equipment_id"]).execute()
        log_action(user_id, "equipment_returned", "equipment_checkout", checkout_id, new_values={"returned_at": now_iso, "condition": condition_on_return})


# ==================== EVENTS & PROBATION TRACKER ====================
def get_all_events():
    try:
        query = _get_client().table("events").select("*").order("event_date", desc=True)
        return query.execute().data or []
    except Exception as e:
        print(f"Error fetching events: {e}")
        return []

def get_event(event_id: str):
    try:
        query = _get_client().table("events").select("*").eq("id", event_id).single()
        return query.execute().data
    except Exception as e:
        print(f"Error fetching event {event_id}: {e}")
        return None

def create_event(title: str, description: str | None, event_type: str, event_date: str, location: str | None, user_id: str):
    data = {
        "title": title,
        "description": description,
        "event_type": event_type,
        "event_date": event_date,
        "location": location,
        "created_by": user_id
    }
    res = _get_client().table("events").insert(data).execute().data[0]
    log_action(user_id, "event_created", "event", res["id"], new_values=data)
    return res

def delete_event(event_id: str, user_id: str):
    old = get_event(event_id)
    _get_client().table("events").delete().eq("id", event_id).execute()
    log_action(user_id, "event_deleted", "event", event_id, old_values=old)

def get_event_attendees(event_id: str):
    try:
        query = _get_client().table("event_attendees").select("*").eq("event_id", event_id)
        return query.execute().data or []
    except Exception as e:
        print(f"Error fetching attendees for event {event_id}: {e}")
        return []

def rsvp_event(event_id: str, user_id: str, status: str = "registered", notes: str | None = None):
    # Check if existing record
    existing = _get_client().table("event_attendees").select("*").eq("event_id", event_id).eq("user_id", user_id).execute().data
    if existing:
        _get_client().table("event_attendees").update({"status": status, "notes": notes}).eq("id", existing[0]["id"]).execute()
    else:
        _get_client().table("event_attendees").insert({
            "event_id": event_id,
            "user_id": user_id,
            "status": status,
            "notes": notes
        }).execute()
    log_action(user_id, "event_rsvp", "event_attendee", event_id, new_values={"status": status})

def get_probation_members():
    try:
        profiles = get_all_users_detailed()
        return [p for p in profiles if p.get("role") in ["probation", "probationary_member", "member", "new_member"]]
    except Exception as e:
        print(f"Error fetching probation members: {e}")
        return []


# ==================== LEADERBOARD ====================
def get_leaderboard_data():
    try:
        profiles = get_all_users_detailed()
        tasks = _get_client().table("tasks").select("*").eq("status", "done").execute().data or []
        task_assignees = _get_client().table("task_assignees").select("*").execute().data or []
        attendance = _get_client().table("attendance").select("*").execute().data or []
        flights = get_all_flight_logs()

        # Map completed tasks per user
        completed_task_counts = {}
        for ta in task_assignees:
            tid = ta["task_id"]
            uid = ta["user_id"]
            if any(t["id"] == tid for t in tasks):
                completed_task_counts[uid] = completed_task_counts.get(uid, 0) + 1

        # Map attendance records & calculate time spent in club
        attendance_counts = {}
        club_minutes = {}
        for a in attendance:
            uid = a["user_id"]
            if a.get("status") == "present":
                attendance_counts[uid] = attendance_counts.get(uid, 0) + 1
                if a.get("notes"):
                    try:
                        notes = json.loads(a["notes"])
                        if "in" in notes and "out" in notes:
                            t_in = datetime.strptime(notes["in"], "%H:%M:%S")
                            t_out = datetime.strptime(notes["out"], "%H:%M:%S")
                            diff = (t_out - t_in).total_seconds() / 60
                            if diff > 0:
                                club_minutes[uid] = club_minutes.get(uid, 0) + int(diff)
                    except Exception:
                        pass

        # Map flight minutes per user
        flight_minutes = {}
        for f in flights:
            uid = f.get("pilot_id")
            if uid:
                flight_minutes[uid] = flight_minutes.get(uid, 0) + (f.get("duration_minutes") or 0)

        leaderboard = []
        for p in profiles:
            uid = p["id"]
            t_count = completed_task_counts.get(uid, 0)
            a_count = attendance_counts.get(uid, 0)
            c_mins = club_minutes.get(uid, 0)
            f_mins = flight_minutes.get(uid, 0)
            
            c_hours = round(c_mins / 60.0, 1)
            
            # Score formula: (Tasks * 50) + (Club Hours * 15) + (Flight Mins * 2) + (Attendance Count * 5)
            score = int((t_count * 50) + (c_hours * 15) + (f_mins * 2) + (a_count * 5))
            
            leaderboard.append({
                "profile": p,
                "tasks_completed": t_count,
                "attendance_events": a_count,
                "club_minutes": c_mins,
                "club_hours": c_hours,
                "flight_minutes": f_mins,
                "score": score
            })

        leaderboard.sort(key=lambda x: x["score"], reverse=True)
        return leaderboard
    except Exception as e:
        print(f"Error computing leaderboard: {e}")
        return []