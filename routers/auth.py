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
async def signup_post(request: Request, club_name: str = Form(...), email: str = Form(...), password: str = Form(...), discord_webhook_url: Optional[str] = Form(None)):
    try:
        # 1. Check if organization exists, if not create it
        org_res = supabase.table("organizations").select("*").ilike("name", club_name).execute()
        if org_res.data:
            org_id = org_res.data[0]["id"]
        else:
            # Create new organization
            org_payload = {"name": club_name}
            if discord_webhook_url:
                org_payload["discord_webhook_url"] = discord_webhook_url
            new_org = supabase.table("organizations").insert(org_payload).execute()
            if not new_org.data:
                raise Exception("Failed to create organization")
            org_id = new_org.data[0]["id"]

        # 2. Sign up the user
        auth_res = supabase.auth.sign_up({"email": email, "password": password})
        if not auth_res.user:
            raise Exception("Signup failed. Check if the email is already registered.")
        
        # 3. Update profile with organization_id
        # We use supabase_admin to bypass RLS if it exists
        client = auth.supabase_admin if auth.supabase_admin else supabase
        
        # We use upsert to ensure the profile exists with the correct org and role
        # First check if profile already exists (to preserve existing data if any)
        profile_data = {
            "id": auth_res.user.id,
            "organization_id": org_id,
            "role": "admin" if not org_res.data else "member", # First user in club is admin
            "email": email
        }
        client.table("profiles").upsert(profile_data).execute()

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

@router.get("/forgot-password")
async def forgot_password_page(request: Request):
    return render_template("login.html", request, message="Please contact your Drone Club administrator to reset your password. Native password reset is coming in v2.1.")
