from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
import crud
from auth import admin_required
from templates_utils import render_template, get_username_map
from database import supabase, supabase_admin

router = APIRouter(prefix="/admin", tags=["admin"])

def _get_client():
    return supabase_admin if supabase_admin else supabase

@router.get("/users")
async def list_users(request: Request, user: dict = Depends(admin_required)):
    org_id = user.get("organization_id")
    profiles = crud.get_all_users_detailed(org_id)
    return render_template("admin_users.html", request, user=user, profiles=profiles)

@router.post("/users/{user_id}/role")
async def change_user_role(user_id: str, new_role: str = Form(...), user: dict = Depends(admin_required)):
    if new_role not in ("member", "lead", "admin"):
        return HTMLResponse("Invalid role", status_code=400)
    
    org_id = user.get("organization_id")
    target_profile = next((p for p in crud.get_all_users_detailed(org_id) if p["id"] == user_id), None)
    if not target_profile:
        raise HTTPException(status_code=403, detail="Forbidden or user not found")

    _get_client().table("profiles").update({"role": new_role}).eq("id", user_id).execute()
    crud.log_action(user["id"], "role_updated", "user", user_id,
                    old_values={"role": "..."}, new_values={"role": new_role}, org_id=org_id)
    return RedirectResponse(url="/admin/users", status_code=303)

@router.get("/users/add")
async def add_user_form(request: Request, user: dict = Depends(admin_required)):
    return render_template("admin_add_user.html", request, user=user)

@router.post("/users/add")
async def add_user_action(request: Request,
                          email: str = Form(...), password: str = Form(...),
                          display_name: str = Form(...),
                          role: str = Form(...), user: dict = Depends(admin_required)):
    if role not in ("member", "lead", "admin"):
        return HTMLResponse("Invalid role", status_code=400)
    try:
        crud.create_user_by_admin(email, password, display_name, role, user["id"], user.get("organization_id"))
    except Exception as e:
        return render_template("admin_add_user.html", request, user=user, error=str(e))
    return RedirectResponse(url="/admin/users", status_code=303)

@router.get("/audit-log")
async def audit_log_view(request: Request, user: dict = Depends(admin_required)):
    org_id = user.get("organization_id")
    logs = crud.get_audit_logs(limit=100, org_id=org_id)
    username_map = get_username_map(org_id)
    return render_template("audit_log.html", request, user=user, logs=logs, username_map=username_map)

@router.post("/undo/{log_id}")
async def undo_action(log_id: str, user: dict = Depends(admin_required)):
    try:
        crud.revert_action(log_id, user["id"])
    except Exception:
        pass
    return RedirectResponse(url="/admin/audit-log", status_code=303)

@router.get("/settings")
async def org_settings_form(request: Request, user: dict = Depends(admin_required)):
    org_id = user.get("organization_id")
    organization = crud.get_organization(org_id)
    return render_template("admin_settings.html", request, user=user, organization=organization)

@router.post("/settings")
async def org_settings_action(request: Request, name: str = Form(...), discord_webhook_url: str = Form(None),
                              user: dict = Depends(admin_required)):
    org_id = user.get("organization_id")
    crud.update_organization_settings(org_id, name, discord_webhook_url or None, user["id"])
    return RedirectResponse(url="/admin/settings", status_code=303)
