from fastapi import Request
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from datetime import date
from services.users import get_all_users_detailed

BASE_DIR = Path(__file__).resolve().parent
env = Environment(loader=FileSystemLoader(str(BASE_DIR / "templates")), autoescape=True)

TACTICAL_DICT = {
    "dashboard": "Overview",
    "tasks": "Actions",
    "todo": "Queued",
    "in_progress": "Active",
    "done": "Complete",
    "users": "Team",
    "audit_log": "Activity Log",
    "search": "Search",
    "analytics": "Insights",
    "mission": "Campaign",
    "project": "Stream",
    "task": "Item",
    "overdue": "Past Due",
    "due_today": "Due Today",
    "due_this_week": "This Week",
    "upcoming": "Scheduled",
    "no_due": "Flexible",
    "priority": "Priority",
    "status": "Status",
    "lead": "Lead",
    "member": "Member",
    "admin": "Admin",
}

STANDARD_DICT = {
    "dashboard": "Dashboard",
    "tasks": "Tasks",
    "todo": "To Do",
    "in_progress": "In Progress",
    "done": "Completed",
    "users": "User Management",
    "audit_log": "Audit Log",
    "search": "Search",
    "analytics": "Analytics",
    "mission": "Mission",
    "project": "Project",
    "task": "Task",
    "overdue": "Overdue",
    "due_today": "Due Today",
    "due_this_week": "Due This Week",
    "upcoming": "Upcoming",
    "no_due": "No Due Date",
    "priority": "Priority",
    "status": "Status",
    "lead": "Project Lead",
    "member": "Member",
    "admin": "Administrator",
}


def get_username_map(org_id: str | None = None) -> dict:
    try:
        users = get_all_users_detailed(org_id)
        return {u["id"]: u["display_name"] or u["username"] or "Member" for u in users}
    except Exception as e:
        print(f"get_username_map failed: {e}")
        return {}


def render_template(template_name: str, request: Request, **kwargs) -> HTMLResponse:
    template = env.get_template(template_name)

    theme = request.cookies.get("theme", "dark")
    ui_mode = request.cookies.get("ui_mode", "standard")

    t_dict = TACTICAL_DICT if ui_mode == "tactical" else STANDARD_DICT

    if "username_map" not in kwargs:
        user = kwargs.get("user")
        org_id = user.get("organization_id") if user else None
        kwargs["username_map"] = get_username_map(org_id)

    html_content = template.render(
        request=request,
        today=date.today(),
        theme=theme,
        ui_mode=ui_mode,
        t=t_dict,
        **kwargs,
    )
    return HTMLResponse(html_content)
