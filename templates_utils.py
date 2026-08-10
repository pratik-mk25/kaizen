from fastapi import Request
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from datetime import date, datetime, timezone, timedelta
import json
from crud import get_all_users_detailed

BASE_DIR = Path(__file__).resolve().parent
env = Environment(loader=FileSystemLoader(str(BASE_DIR / "templates")), autoescape=True)

IST = timezone(timedelta(hours=5, minutes=30))

def from_json(value):
    if not value:
        return {}
    if isinstance(value, dict):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        try:
            import ast
            res = ast.literal_eval(value)
            if isinstance(res, dict):
                return res
        except Exception:
            pass
        return {}

def format_time_12h(time_str):
    if not time_str or time_str == "-":
        return "-"
    try:
        if "AM" in time_str or "PM" in time_str:
            return time_str
        parts = time_str.split(":")
        hh = int(parts[0])
        mm = int(parts[1])
        am_pm = "AM" if hh < 12 else "PM"
        hh_12 = hh % 12
        if hh_12 == 0:
            hh_12 = 12
        return f"{hh_12:02d}:{mm:02d} {am_pm}"
    except Exception:
        return time_str

env.filters["from_json"] = from_json
env.filters["format_time_12h"] = format_time_12h

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


def get_username_map() -> dict:
    try:
        users = get_all_users_detailed()
        return {u["id"]: u["display_name"] or u["username"] or "Member" for u in users}
    except Exception as e:
        print(f"get_username_map failed: {e}")
        return {}


def render_template(template_name: str, request: Request, **kwargs) -> HTMLResponse:
    template = env.get_template(template_name)

    theme = request.cookies.get("theme", "system")
    ui_mode = request.cookies.get("ui_mode", "standard")

    t_dict = TACTICAL_DICT if ui_mode == "tactical" else STANDARD_DICT

    if "username_map" not in kwargs:
        kwargs["username_map"] = get_username_map()

    today_ist = datetime.now(IST).date()

    html_content = template.render(
        request=request,
        today=today_ist,
        theme=theme,
        ui_mode=ui_mode,
        t=t_dict,
        **kwargs,
    )
    return HTMLResponse(html_content)
