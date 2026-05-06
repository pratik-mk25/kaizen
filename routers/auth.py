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
async def signup_post(request: Request, email: str = Form(...), password: str = Form(...)):
    try:
        supabase.auth.sign_up({"email": email, "password": password})
    except Exception as e:
        return render_template("signup.html", request, error=str(e))
    return RedirectResponse(url="/login?message=Account created. Please log in.", status_code=303)

@router.get("/login")
async def login_page(request: Request, message: Optional[str] = None):
    return render_template("login.html", request, message=message)

@router.post("/login")
async def login_post(request: Request, email: str = Form(...), password: str = Form(...)):
    try:
        auth_response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        access_token = auth_response.session.access_token
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
