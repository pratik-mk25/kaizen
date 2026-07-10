from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from database import supabase
import auth
from auth import set_auth_cookie, remove_auth_cookie, get_current_user
from templates_utils import render_template

router = APIRouter(tags=["auth"])

@router.get("/login")
async def login_page(request: Request, message: str = None):
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
        token = request.cookies.get(auth.COOKIE_NAME)
        supabase.postgrest.headers["Authorization"] = f"Bearer {token}"
        supabase.auth.set_session(token, "")
        supabase.auth.update_user({"password": password})
        return render_template("change_password.html", request, user=user, message="Password updated successfully")
    except Exception as e:
        return render_template("change_password.html", request, user=user, error=str(e))
