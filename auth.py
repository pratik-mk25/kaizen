import os
from fastapi import Request, HTTPException, Depends
from fastapi.responses import RedirectResponse
from database import supabase
from typing import Optional

COOKIE_NAME = "access_token"

_IS_HTTPS = os.environ.get("VERCEL_ENV") is not None or os.environ.get("VERCEL") == "1"

def set_auth_cookie(response: RedirectResponse, access_token: str):
    response.set_cookie(
        key=COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=_IS_HTTPS,
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

    supabase.postgrest.headers["Authorization"] = f"Bearer {token}"

    try:
        profile_response = supabase.table("profiles").select("*").eq("id", user.id).execute()
        if not profile_response.data:
            raise HTTPException(status_code=401, detail="Profile not found")
        profile = profile_response.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    return {
        "id": user.id,
        "email": user.email,
        "username": profile.get("username"),
        "display_name": profile.get("display_name"),
        "role": profile["role"],
    }

async def admin_required(user: dict = Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admins only")
    return user

async def lead_or_admin_required(user: dict = Depends(get_current_user)):
    if user["role"] not in ("lead", "admin"):
        raise HTTPException(status_code=403, detail="Leads or admins only")
    return user
