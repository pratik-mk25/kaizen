from fastapi import Request, HTTPException, Depends
from fastapi.responses import RedirectResponse
from database import supabase, supabase_admin
from typing import Optional

COOKIE_NAME = "access_token"

def set_auth_cookie(response: RedirectResponse, access_token: str):
    response.set_cookie(
        key=COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=False,     # True in production
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
    )

def remove_auth_cookie(response: RedirectResponse):
    response.delete_cookie(COOKIE_NAME)

async def get_current_user(request: Request) -> dict:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        user_response = supabase.auth.get_user(token)
        user = user_response.user
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Use supabase_admin to bypass RLS for the initial profile fetch
    # This ensures we can always get the user's role and org_id
    if supabase_admin is not None:
        client = supabase_admin
        print("DEBUG: Using supabase_admin for profile fetch")
    else:
        # Fallback to regular supabase client if service role key is missing
        # Note: We attempt to set the auth header for this request
        client = supabase
        print("DEBUG: supabase_admin is None, falling back to supabase client")
        if client is not None and hasattr(client, "postgrest"):
            # Set the Authorization header for this client instance
            client.postgrest.headers["Authorization"] = f"Bearer {token}"
            print("DEBUG: Set Bearer token in postgrest headers")

    if client is None:
        print("DEBUG: CRITICAL - Client is None before table access")
        raise HTTPException(status_code=500, detail="Supabase client not initialized")

    try:
        print(f"DEBUG: Attempting to fetch profile for user {user.id}")
        if not hasattr(client, "table"):
            print(f"DEBUG: CRITICAL - Client of type {type(client)} has no 'table' attribute")
            raise AttributeError(f"Client {type(client)} has no 'table' attribute")
            
        profile_response = client.table("profiles").select("*").eq("id", user.id).execute()
        if not profile_response.data:
            print(f"DEBUG: Profile not found for user {user.id}")
            raise HTTPException(status_code=401, detail="Profile not found")
        profile = profile_response.data[0]
        print(f"DEBUG: Profile found, role: {profile.get('role')}")
    except AttributeError as ae:
        print(f"DEBUG: AttributeError during profile fetch: {ae}")
        raise HTTPException(status_code=500, detail=f"Client configuration error: {str(ae)}")
    except Exception as e:
        print(f"DEBUG: Exception during profile fetch: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    return {
        "id": user.id, 
        "email": user.email, 
        "role": profile["role"],
        "organization_id": profile.get("organization_id")
    }

async def admin_required(user: dict = Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admins only")
    return user

async def lead_or_admin_required(user: dict = Depends(get_current_user)):
    if user["role"] not in ("lead", "admin"):
        raise HTTPException(status_code=403, detail="Leads or admins only")
    return user
