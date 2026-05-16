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

# ---------- System Administration (Super Admin) ----------

async def super_admin_required(user: dict = Depends(admin_required)):
    # Feature disabled for now pending Editor role implementation
    raise HTTPException(status_code=403, detail="System administration feature is currently disabled")

@router.get("/system/requests")
async def list_system_requests(request: Request, user: dict = Depends(super_admin_required)):
    res = supabase.table("access_requests").select("*").eq("status", "pending").order("created_at", desc=True).execute()
    return render_template("system_requests.html", request, user=user, requests=res.data)

@router.post("/system/approve/{request_id}")
async def approve_system_request(request_id: str, user: dict = Depends(super_admin_required)):
    from urllib.parse import quote
    req = supabase.table("access_requests").select("*").eq("id", request_id).single().execute().data
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    
    try:
        # Use supabase_admin for all administrative operations to bypass RLS
        admin_client = supabase_admin if supabase_admin else supabase
        
        # 1. Check if organization already exists
        existing_org = admin_client.table("organizations").select("*").ilike("name", req["club_name"]).execute()
        if existing_org.data:
            org_id = existing_org.data[0]["id"]
        else:
            # Create Organization
            org_res = admin_client.table("organizations").insert({"name": req["club_name"]}).execute()
            if not org_res.data:
                raise Exception("Failed to create organization")
            org_id = org_res.data[0]["id"]
        
        # 2. Check if user already exists (using admin client to see all profiles)
        existing_user = admin_client.table("profiles").select("*").eq("email", req["email"]).execute()
        
        if existing_user.data:
            user_id = existing_user.data[0]["id"]
            # Update existing user to be admin of the NEW organization
            admin_client.table("profiles").update({
                "organization_id": org_id,
                "role": "admin",
                "display_name": req["full_name"]
            }).eq("id", user_id).execute()
            
            # Mark request as approved
            admin_client.table("access_requests").update({"status": "approved"}).eq("id", request_id).execute()
            msg = quote(f"Existing user {req['email']} linked as Admin to {req['club_name']}.")
            return RedirectResponse(url=f"/admin/system/requests?message={msg}", status_code=303)
        
        else:
            # 3. Generate Random Password for NEW user
            import secrets
            import string
            temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
            
            # 4. Create Admin User for this organization
            crud.create_user_by_admin(req["email"], temp_password, req["full_name"], "admin", user["id"], org_id)
            
            # 5. Mark request as approved
            admin_client.table("access_requests").update({"status": "approved"}).eq("id", request_id).execute()
            msg = quote(f"Successfully approved {req['club_name']}. Initial Password: {temp_password}")
            return RedirectResponse(url=f"/admin/system/requests?message={msg}", status_code=303)
            
    except Exception as e:
        err_msg = quote(str(e))
        return RedirectResponse(url=f"/admin/system/requests?error={err_msg}", status_code=303)

@router.post("/system/reject/{request_id}")
async def reject_system_request(request_id: str, user: dict = Depends(super_admin_required)):
    supabase.table("access_requests").update({"status": "rejected"}).eq("id", request_id).execute()
    return RedirectResponse(url="/admin/system/requests?message=Request rejected.", status_code=303)
