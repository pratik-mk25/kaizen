from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from typing import Optional
from database import supabase
import auth
from auth import set_auth_cookie, remove_auth_cookie
from templates_utils import render_template

router = APIRouter(tags=["auth"])

@router.get("/signup")
async def signup_page(request: Request):
    return render_template("signup.html", request)

@router.post("/signup")
async def signup_post(request: Request, club_name: str = Form(...), email: str = Form(...), password: str = Form(...), discord_webhook_url: Optional[str] = Form(None), activation_key: Optional[str] = Form(None)):
    try:
        # 1. Check if organization exists, if not create it
        org_res = supabase.table("organizations").select("*").ilike("name", club_name).execute()
        if org_res.data:
            org_id = org_res.data[0]["id"]
        else:
            # Validate activation key for new organizations
            if not activation_key:
                raise Exception("An Activation Key is required to create a new organization. Please contact the KAIZEN administrator.")
            
            key_check = supabase.table("activation_keys").select("*").eq("key", activation_key).eq("is_used", False).execute()
            if not key_check.data:
                raise Exception("Invalid or already used Activation Key.")

            # Create new organization
            org_payload = {"name": club_name}
            if discord_webhook_url:
                org_payload["discord_webhook_url"] = discord_webhook_url
            
            new_org = supabase.table("organizations").insert(org_payload).execute()
            if not new_org.data:
                raise Exception("Failed to create organization")
            org_id = new_org.data[0]["id"]

            # Mark key as used
            from datetime import datetime, timezone
            supabase.table("activation_keys").update({"is_used": True, "used_at": datetime.now(timezone.utc).isoformat()}).eq("key", activation_key).execute()

        # 2. Sign up the user
        # We pass organization and role data in the metadata so the DB trigger can handle it automatically
        auth_res = supabase.auth.sign_up({
            "email": email, 
            "password": password,
            "options": {
                "data": {
                    "organization_id": str(org_id),
                    "role": "admin" if not org_res.data else "member"
                }
            }
        })
        if not auth_res.user:
            raise Exception("Signup failed. Check if the email is already registered.")
        
    except Exception as e:
        return render_template("signup.html", request, error=str(e))
    return RedirectResponse(url="/login?message=Account created for '" + club_name + "'. Please log in.", status_code=303)

@router.get("/login")
async def login_page(request: Request, message: Optional[str] = None):
    return render_template("login.html", request, message=message)

@router.post("/login")
async def login_post(request: Request, club_name: str = Form(...), email: str = Form(...), password: str = Form(...)):
    try:
        # 1. Authenticate
        auth_response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        access_token = auth_response.session.access_token
        user_id = auth_response.user.id

        # 2. Verify Club Identity
        # We fetch the profile and join with organization
        profile_res = supabase.table("profiles").select("*, organizations(name)").eq("id", user_id).single().execute()
        if not profile_res.data:
            raise Exception("Profile not found")
        
        user_org_name = profile_res.data.get("organizations", {}).get("name", "")
        if user_org_name.lower() != club_name.lower():
            supabase.auth.sign_out()
            raise Exception(f"You do not belong to the club '{club_name}'")

        # 3. Success
        response = RedirectResponse(url="/dashboard", status_code=303)
        set_auth_cookie(response, access_token)
        return response
    except Exception as e:
        return render_template("login.html", request, error=str(e))

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login")
    remove_auth_cookie(response)
    return response

@router.get("/change-password")
async def change_password_page(request: Request, user: dict = Depends(get_current_user)):
    return render_template("change_password.html", request, user=user)

@router.post("/change-password")
async def change_password_post(request: Request, password: str = Form(...), confirm_password: str = Form(...), user: dict = Depends(get_current_user)):
    if password != confirm_password:
        return render_template("change_password.html", request, user=user, error="Passwords do not match")
    
    if len(password) < 6:
        return render_template("change_password.html", request, user=user, error="Password must be at least 6 characters")
    
    try:
        # Get the access token from cookies
        token = request.cookies.get(auth.COOKIE_NAME)
        # We need to set the session for the client to update the user
        supabase.postgrest.headers["Authorization"] = f"Bearer {token}"
        supabase.auth.set_session(token, "") # Refresh token not needed for just updating password usually
        
        supabase.auth.update_user({"password": password})
        return render_template("change_password.html", request, user=user, message="Password updated successfully")
    except Exception as e:
        return render_template("change_password.html", request, user=user, error=str(e))

@router.get("/forgot-password")
async def forgot_password_page(request: Request):
    return render_template("login.html", request, message="Please contact your Club administrator to reset your password. Native password reset is coming in v2.1.")
