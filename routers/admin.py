from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
import crud
from auth import admin_required
from templates_utils import render_template, get_username_map
from database import supabase

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/users")
async def list_users(request: Request, user: dict = Depends(admin_required)):
    profiles = crud.get_all_users_detailed()
    return render_template("admin_users.html", request, user=user, profiles=profiles)

@router.post("/users/{user_id}/role")
async def change_user_role(user_id: str, new_role: str = Form(...), user: dict = Depends(admin_required)):
    if new_role not in ("member", "lead", "admin"):
        return HTMLResponse("Invalid role", status_code=400)
    
    target_profile = next((p for p in crud.get_all_users_detailed() if p["id"] == user_id), None)
    if not target_profile:
        raise HTTPException(status_code=403, detail="Forbidden or user not found")

    supabase.table("profiles").update({"role": new_role}).eq("id", user_id).execute()
    crud.log_action(user["id"], "role_updated", "user", user_id,
                    old_values={"role": "..."}, new_values={"role": new_role})
    return RedirectResponse(url="/admin/users", status_code=303)

@router.get("/users/add")
async def add_user_form(request: Request, user: dict = Depends(admin_required)):
    return render_template("admin_add_user.html", request, user=user)

@router.post("/users/add")
async def add_user_action(request: Request,
                          email: str = Form(...), password: str = Form(...),
                          display_name: str = Form(...),
                          role: str = Form(...), 
                          user: dict = Depends(admin_required)):
    if role not in ("member", "lead", "admin"):
        return HTMLResponse("Invalid role", status_code=400)
    
    try:
        crud.create_user_by_admin(email, password, display_name, role, user["id"])
    except Exception as e:
        return render_template("admin_add_user.html", request, user=user, error=str(e))
    return RedirectResponse(url="/admin/users", status_code=303)

@router.post("/users/{user_id}/delete")
async def delete_user(user_id: str, user: dict = Depends(admin_required)):
    from database import supabase_admin
    try:
        supabase_admin.auth.admin.delete_user(user_id)
    except Exception:
        pass
    supabase.table("profiles").delete().eq("id", user_id).execute()
    crud.log_action(user["id"], "user_deleted", "user", user_id)
    return RedirectResponse(url="/admin/users", status_code=303)

@router.get("/audit-log")
async def audit_log_view(request: Request, user: dict = Depends(admin_required)):
    logs = crud.get_audit_logs(limit=100)
    username_map = get_username_map()
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
    organization = crud.get_organization()
    return render_template("admin_settings.html", request, user=user, organization=organization)

@router.post("/settings")
async def org_settings_action(request: Request, name: str = Form(...), discord_webhook_url: str = Form(None),
                              user: dict = Depends(admin_required)):
    val = discord_webhook_url or None
    crud.update_organization_settings(name, val, user["id"])
    org = crud.get_organization()
    saved_url = org.get("discord_webhook_url")
    return RedirectResponse(url=f"/admin/settings?saved={'yes' if saved_url else 'fail'}&url={'set' if saved_url else 'empty'}", status_code=303)
