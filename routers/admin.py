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
    reset_success = request.query_params.get("reset_success")
    reset_target = request.query_params.get("target")
    reset_pwd = request.query_params.get("pwd")
    reset_error = request.query_params.get("reset_error")
    suggested_pwd = crud.generate_temporary_password()
    return render_template("admin_users.html", request, user=user, profiles=profiles,
                           reset_success=reset_success, reset_target=reset_target,
                           reset_pwd=reset_pwd, reset_error=reset_error,
                           suggested_password=suggested_pwd)

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
    suggested_pwd = crud.generate_temporary_password()
    return render_template("admin_add_user.html", request, user=user, suggested_password=suggested_pwd)

@router.post("/users/add")
async def add_user_action(request: Request,
                          email: str = Form(...),
                          password: str = Form(None),
                          display_name: str = Form(None),
                          role: str = Form("member"), 
                          user: dict = Depends(admin_required)):
    if role not in ("member", "lead", "admin"):
        role = "member"
    
    clean_email = email.strip().lower()
    final_password = (password or "").strip() or crud.generate_temporary_password()
    final_display_name = (display_name or "").strip() or crud.derive_display_name_from_email(clean_email)

    try:
        result = crud.create_user_by_admin(clean_email, final_password, final_display_name, role, user["id"])
        is_adopted = result.get("adopted", False)
        status_msg = "Account adopted and updated successfully" if is_adopted else "User provisioned successfully"
        suggested_pwd = crud.generate_temporary_password()
        return render_template("admin_add_user.html", request, user=user,
                               success=True,
                               provisioned_user={
                                   "email": clean_email,
                                   "display_name": final_display_name,
                                   "role": role,
                                   "password": final_password,
                                   "adopted": is_adopted
                               },
                               message=status_msg,
                               suggested_password=suggested_pwd)
    except Exception as e:
        err_msg = str(e)
        if "profiles_pkey" in err_msg:
            err_msg = "Profile ID collision resolved. Please try submitting again."
        suggested_pwd = crud.generate_temporary_password()
        return render_template("admin_add_user.html", request, user=user,
                               error=err_msg,
                               email=email,
                               display_name=display_name,
                               role=role,
                               suggested_password=suggested_pwd)

@router.post("/users/bulk")
async def bulk_add_users_action(request: Request,
                                bulk_text: str = Form(...),
                                default_role: str = Form("member"),
                                user: dict = Depends(admin_required)):
    """
    Parses multi-line text input (CSV or list of emails) and bulk-provisions users.
    """
    lines = [line.strip() for line in bulk_text.strip().splitlines() if line.strip()]
    users_data = []

    for line in lines:
        parts = [p.strip() for p in line.replace("\t", ",").split(",") if p.strip()]
        if not parts:
            continue
        email = parts[0]
        name = parts[1] if len(parts) > 1 else crud.derive_display_name_from_email(email)
        role = parts[2].lower() if len(parts) > 2 and parts[2].lower() in ("member", "lead", "admin") else default_role
        pwd = parts[3] if len(parts) > 3 else crud.generate_temporary_password()
        users_data.append({
            "email": email,
            "display_name": name,
            "role": role,
            "password": pwd
        })

    bulk_results = crud.create_users_bulk(users_data, user["id"])
    suggested_pwd = crud.generate_temporary_password()
    return render_template("admin_add_user.html", request, user=user,
                           active_tab="bulk",
                           bulk_results=bulk_results,
                           suggested_password=suggested_pwd)

@router.post("/users/{user_id}/reset-password")
async def reset_password_action(user_id: str,
                                request: Request,
                                new_password: str = Form(None),
                                user: dict = Depends(admin_required)):
    pwd = (new_password or "").strip() or crud.generate_temporary_password()
    try:
        crud.reset_user_password_by_admin(user_id, pwd, user["id"])
        target_profile = next((p for p in crud.get_all_users_detailed() if p["id"] == user_id), None)
        target_name = target_profile.get("display_name") if target_profile else user_id[:8]
        return RedirectResponse(
            url=f"/admin/users?reset_success=1&target={target_name}&pwd={pwd}",
            status_code=303
        )
    except Exception as e:
        return RedirectResponse(
            url=f"/admin/users?reset_error={str(e)}",
            status_code=303
        )

@router.post("/users/{user_id}/delete")
async def delete_user(user_id: str, user: dict = Depends(admin_required)):
    try:
        crud.delete_user_completely(user_id, user["id"])
    except Exception as e:
        print(f"Error deleting user {user_id}: {e}")
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
                              kiosk_secret: str = Form(None),
                              user: dict = Depends(admin_required)):
    val = discord_webhook_url or None
    crud.update_organization_settings(name, val, user["id"])
    if kiosk_secret is not None:
        crud.set_kiosk_secret(kiosk_secret, user["id"])
    org = crud.get_organization()
    saved_url = org.get("discord_webhook_url")
    return RedirectResponse(url=f"/admin/settings?saved={'yes' if saved_url else 'fail'}&url={'set' if saved_url else 'empty'}", status_code=303)
