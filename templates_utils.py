from fastapi import Request
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from datetime import date
import crud

BASE_DIR = Path(__file__).resolve().parent
env = Environment(loader=FileSystemLoader(str(BASE_DIR / "templates")), autoescape=True)

def get_username_map(org_id: str = None):
    users = crud.get_all_users_detailed(org_id)
    return {u["id"]: u["display_name"] or u["username"] or "Member" for u in users}

def render_template(template_name: str, request: Request, **kwargs) -> HTMLResponse:
    template = env.get_template(template_name)
    if "username_map" not in kwargs:
        user = kwargs.get("user")
        org_id = user.get("organization_id") if user else None
        kwargs["username_map"] = get_username_map(org_id)
    html_content = template.render(request=request, today=date.today(), **kwargs)
    return HTMLResponse(html_content)
