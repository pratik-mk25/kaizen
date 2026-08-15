"""
===============================================================================
KAIZEN / MISSION AVINYA - Missions, Projects & Tasks Database Services
===============================================================================
Module Purpose:
  Provides CRUD operations for Missions, Projects, Kanban Tasks, Task Assignees,
  Comments, and File Attachments with full line-by-line documentation.
===============================================================================
"""

# Import Python standard datetime utilities
from datetime import datetime, timezone

# Import base DB client and logging services
from .base import _get_client, log_action
from database import supabase


# =============================================================================
# MISSIONS MANAGEMENT
# =============================================================================

def get_all_missions():
    """
    Fetches all top-level missions ordered chronologically by creation date.
    """
    # Build query selecting all fields from missions table ordered by created_at ascending
    query = _get_client().table("missions").select("*").order("created_at", desc=False)
    # Execute query and return rows array or empty list fallback
    res = query.execute()
    return res.data if (res and res.data is not None) else []


def get_mission(mission_id: str):
    """
    Fetches a single mission by its unique UUID identifier.
    """
    # Build query filtering by mission_id
    query = _get_client().table("missions").select("*").eq("id", mission_id)
    # Execute single record query and return object dictionary
    return query.single().execute().data


def create_mission(name: str, description: str | None, user_id: str):
    """
    Creates a new mission and logs the action to audit history.
    """
    # Construct database insert dictionary payload
    data = {"name": name, "description": description}
    # Execute insert query into missions table
    res = _get_client().table("missions").insert(data).execute().data[0]
    # Log action to audit logs for user activity tracking
    log_action(user_id, "mission_created", "mission", res["id"], new_values=data)
    # Return newly created mission object
    return res


def update_mission(mission_id: str, name: str, description: str | None, user_id: str):
    """
    Updates an existing mission's title and description details.
    """
    # Retrieve current mission details before applying updates (for audit log revert)
    old = get_mission(mission_id)
    # Prepare update dictionary payload
    new_data = {"name": name, "description": description}
    # Execute database update query on matching mission_id
    _get_client().table("missions").update(new_data).eq("id", mission_id).execute()
    # Log update action with old and new values
    log_action(user_id, "mission_updated", "mission", mission_id, old_values=old, new_values=new_data)


def delete_mission(mission_id: str, user_id: str):
    """
    Deletes a mission by its UUID identifier.
    """
    # Fetch current mission details before deletion
    old = get_mission(mission_id)
    # Execute delete query on missions table
    _get_client().table("missions").delete().eq("id", mission_id).execute()
    # Log deletion action in audit log
    log_action(user_id, "mission_deleted", "mission", mission_id, old_values=old)


# =============================================================================
# PROJECTS MANAGEMENT
# =============================================================================

def get_projects_for_mission(mission_id: str):
    """
    Fetches all sub-projects associated with a specific mission ID.
    """
    # Build query filtering projects by mission_id
    query = _get_client().table("projects").select("*").eq("mission_id", mission_id).order("created_at")
    # Return rows array or empty fallback list
    res = query.execute()
    return res.data if (res and res.data is not None) else []


def get_project(project_id: str):
    """
    Fetches a single project by its project UUID identifier.
    """
    # Query single project record from database
    query = _get_client().table("projects").select("*").eq("id", project_id)
    return query.single().execute().data


def create_project(name: str, description: str | None, mission_id: str, lead_id: str | None, user_id: str):
    """
    Creates a new project linked to a mission and assigns a project lead.
    """
    # Construct payload dictionary
    data = {"name": name, "description": description, "mission_id": mission_id, "lead_id": lead_id}
    # Insert new project into database
    res = _get_client().table("projects").insert(data).execute().data[0]
    # Log action to audit logs
    log_action(user_id, "project_created", "project", res["id"], new_values=data)
    return res


def update_project(project_id: str, name: str, description: str | None, lead_id: str | None, user_id: str):
    """
    Updates an existing project's metadata or assigned project lead.
    """
    # Fetch previous state for audit log history
    old = get_project(project_id)
    # Construct new update dictionary payload
    new_data = {"name": name, "description": description, "lead_id": lead_id}
    # Execute update query on projects table
    _get_client().table("projects").update(new_data).eq("id", project_id).execute()
    # Log project update action
    log_action(user_id, "project_updated", "project", project_id, old_values=old, new_values=new_data)


def delete_project(project_id: str, user_id: str):
    """
    Deletes a project record by its project ID.
    """
    # Fetch current record for undo audit entry
    old = get_project(project_id)
    # Execute delete on projects table
    _get_client().table("projects").delete().eq("id", project_id).execute()
    # Log action in audit log
    log_action(user_id, "project_deleted", "project", project_id, old_values=old)


# =============================================================================
# TASKS & KANBAN MANAGEMENT
# =============================================================================

def get_tasks_for_project(project_id: str):
    """
    Fetches all Kanban tasks for a specific project.
    """
    # Select all tasks matching project_id ordered by created_at
    query = _get_client().table("tasks").select("*").eq("project_id", project_id).order("created_at")
    res = query.execute()
    return res.data if (res and res.data is not None) else []


def get_task(task_id: str):
    """
    Fetches a single task by its task UUID identifier.
    """
    # Query single task record
    query = _get_client().table("tasks").select("*").eq("id", task_id)
    return query.single().execute().data


def create_task(title: str, description: str | None, project_id: str, user_id: str,
                priority: str = "medium", due_date: str | None = None):
    """
    Creates a new task in the default 'todo' status column.
    """
    # Construct task dictionary payload
    data = {
        "title": title,
        "description": description,
        "project_id": project_id,
        "priority": priority,
        "due_date": due_date,
        "status": "todo"  # Default initial column in Kanban board
    }
    # Insert new task into database
    res = _get_client().table("tasks").insert(data).execute().data[0]
    # Log action to audit log
    log_action(user_id, "task_created", "task", res["id"], new_values=data)
    return res


def update_task_status(task_id: str, new_status: str, user_id: str):
    """
    Updates a task's status column (e.g. 'todo', 'in_progress', 'done') for Kanban board drags.
    """
    # Update status and updated_at timestamp in database
    _get_client().table("tasks").update({
        "status": new_status, 
        "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", task_id).execute()
    # Log status update action
    log_action(user_id, "task_status_updated", "task", task_id, new_values={"status": new_status})


def update_task(task_id: str, title: str, description: str | None, priority: str, due_date: str | None, user_id: str):
    """
    Updates a task's title, description, priority, or deadline due date.
    """
    # Fetch previous state for audit log tracking
    old = get_task(task_id)
    # Construct update data payload
    new_data = {
        "title": title,
        "description": description,
        "priority": priority,
        "due_date": due_date,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    # Update tasks table
    _get_client().table("tasks").update(new_data).eq("id", task_id).execute()
    # Log task update action
    log_action(user_id, "task_updated", "task", task_id, old_values=old, new_values=new_data)


def delete_task(task_id: str, user_id: str):
    """
    Deletes a task by its task UUID identifier.
    """
    # Fetch old task record for audit history
    old = get_task(task_id)
    # Execute delete query on tasks table
    _get_client().table("tasks").delete().eq("id", task_id).execute()
    # Log deletion in audit log
    log_action(user_id, "task_deleted", "task", task_id, old_values=old)


def get_assignees(task_id: str) -> list[dict]:
    """
    Fetches member profiles assigned to a specific task.
    """
    # Fetch user_ids assigned to task_id
    assignee_rows = _get_client().table("task_assignees").select("user_id").eq("task_id", task_id).execute().data or []
    if not assignee_rows:
        return []
    # Extract list of assigned user IDs
    user_ids = [r["user_id"] for r in assignee_rows]
    # Fetch profile details for assigned users
    profiles = _get_client().table("profiles").select("id, username, display_name, role").in_("id", user_ids).execute().data
    return profiles or []


def assign_users_to_task(task_id: str, user_ids: list[str], admin_id: str):
    """
    Updates assignees for a task by replacing current task_assignee entries.
    """
    # Delete existing assignees for this task
    _get_client().table("task_assignees").delete().eq("task_id", task_id).execute()
    # Build list of new assignee rows if user_ids provided
    if user_ids:
        rows = [{"task_id": task_id, "user_id": uid} for uid in user_ids]
        _get_client().table("task_assignees").insert(rows).execute()
    # Log task assignment action
    log_action(admin_id, "task_assigned", "task", task_id, new_values={"user_ids": user_ids})


def get_tasks_for_user(user_id: str) -> list[dict]:
    """
    Fetches all tasks assigned to a specific user.
    """
    # Query task_assignees for matching user_id
    rows = _get_client().table("task_assignees").select("task_id").eq("user_id", user_id).execute().data or []
    if not rows:
        return []
    # Extract task IDs assigned to user
    task_ids = [r["task_id"] for r in rows]
    # Query full task records matching task_ids
    query = _get_client().table("tasks").select("*").in_("id", task_ids)
    res = query.execute()
    return res.data if (res and res.data is not None) else []


# =============================================================================
# COMMENTS & ATTACHMENTS
# =============================================================================

def get_comments_for_task(task_id: str):
    """
    Fetches all discussion comments on a task.
    """
    # Query comments table for task_id ordered chronologically
    query = _get_client().table("comments").select("*").eq("task_id", task_id).order("created_at", desc=False)
    res = query.execute()
    return res.data if (res and res.data is not None) else []


def add_comment(task_id: str, content: str, user_id: str):
    """
    Adds a new comment to a task discussion thread.
    """
    # Construct comment payload dictionary
    data = {"task_id": task_id, "content": content, "user_id": user_id}
    # Insert comment into database
    res = _get_client().table("comments").insert(data).execute().data[0]
    # Log action to audit log
    log_action(user_id, "comment_added", "comment", res["id"], new_values=data)
    return res


def get_attachments(task_id: str) -> list[dict]:
    """
    Fetches all file attachment records linked to a task.
    """
    # Query task_attachments table for matching task_id
    query = _get_client().table("task_attachments").select("*").eq("task_id", task_id).order("created_at")
    res = query.execute()
    return res.data if (res and res.data is not None) else []


def add_attachment(task_id: str, uploader_id: str, file_name: str, storage_path: str,
                   file_type: str | None = None, file_size: int | None = None):
    """
    Records a uploaded file attachment linked to a task.
    """
    # Construct attachment metadata payload
    data = {
        "task_id": task_id,
        "uploader_id": uploader_id,
        "file_name": file_name,
        "storage_path": storage_path,
        "file_type": file_type,
        "file_size": file_size
    }
    # Insert record into database
    res = _get_client().table("task_attachments").insert(data).execute().data[0]
    # Log action to audit log
    log_action(uploader_id, "attachment_added", "task_attachment", res["id"], new_values=data)
    return res


def delete_attachment(attachment_id: str, user_id: str):
    """
    Deletes a file attachment record by its UUID identifier.
    """
    # Query attachment details
    query = _get_client().table("task_attachments").select("*").eq("id", attachment_id)
    records = query.execute().data
    if records:
        # Delete attachment row from database
        _get_client().table("task_attachments").delete().eq("id", attachment_id).execute()
        # Log deletion in audit log
        log_action(user_id, "attachment_deleted", "task_attachment", attachment_id, old_values=records[0])


def get_monthly_progress(month: str):
    """
    Calculates completed task metrics and mission breakdown for a target YYYY-MM month.
    """
    try:
        # Fetch all tasks from database
        tasks_query = _get_client().table("tasks").select("*")
        tasks = tasks_query.execute().data or []

        # Fetch missions and projects
        missions_query = _get_client().table("missions").select("id, name")
        missions = missions_query.execute().data or []
        projects_query = _get_client().table("projects").select("id, name, mission_id")
        projects = projects_query.execute().data or []

        # Filter completed tasks for target month
        completed_in_month = []
        for t in tasks:
            if t.get("status") == "done":
                updated_at = t.get("updated_at")
                if updated_at and updated_at.startswith(month):
                    completed_in_month.append(t)

        # Build project to mission mapping dictionary
        project_to_mission = {p["id"]: p["mission_id"] for p in projects}
        mission_names = {m["id"]: m["name"] for m in missions}

        # Count completed tasks per mission
        mission_counts = {}
        for t in completed_in_month:
            pid = t.get("project_id")
            mid = project_to_mission.get(pid)
            if mid:
                mname = mission_names.get(mid, "Unknown Mission")
                mission_counts[mname] = mission_counts.get(mname, 0) + 1

        # Calculate assignee task counts
        task_ids = [t["id"] for t in completed_in_month]
        assignee_counts = {}
        if task_ids:
            all_rows = _get_client().table("task_assignees").select("task_id, user_id").in_("task_id", task_ids).execute().data or []
            for r in all_rows:
                uid = r["user_id"]
                assignee_counts[uid] = assignee_counts.get(uid, 0) + 1

        return {
            "month": month,
            "total_completed": len(completed_in_month),
            "mission_breakdown": mission_counts,
            "assignee_counts": assignee_counts
        }
    except Exception as e:
        print(f"Error computing monthly progress: {e}")
        return {"month": month, "total_completed": 0, "mission_breakdown": {}, "assignee_counts": {}}
