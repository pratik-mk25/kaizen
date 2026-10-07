from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from database import supabase
import auth
from auth import set_auth_cookie, remove_auth_cookie, get_current_user
from templates_utils import render_template

router = APIRouter(tags=["auth"])

@router.get("/demo-login")
async def demo_login(request: Request, role: str = "admin", next: str = None):
    token = "demo-admin-token" if role == "admin" else "demo-member-token"
    dest = next or request.query_params.get("next") or "/dashboard"
    response = RedirectResponse(url=dest, status_code=303)
    set_auth_cookie(response, token)
    return response

@router.get("/login")
async def login_page(request: Request, message: str = None, next: str = None):
    return render_template("login.html", request, message=message, next=next)

@router.post("/login")
async def login_post(request: Request, email: str = Form(...), password: str = Form(...), next: str = Form(None)):
    email_clean = email.strip().lower()
    dest = next or request.query_params.get("next") or "/dashboard"
    
    # 1-Click / Demo login bypass
    if email_clean in ("admin@kaizen.club", "admin"):
        response = RedirectResponse(url=dest, status_code=303)
        set_auth_cookie(response, "demo-admin-token")
        return response
    if email_clean in ("pilot@kaizen.club", "member", "pilot"):
        response = RedirectResponse(url=dest, status_code=303)
        set_auth_cookie(response, "demo-member-token")
        return response

    try:
        auth_response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        access_token = auth_response.session.access_token
        response = RedirectResponse(url=dest, status_code=303)
        set_auth_cookie(response, access_token)
        return response
    except Exception as e:
        err_msg = str(e).lower()
        # Graceful fallback if Supabase is unreachable/offline locally
        if any(term in err_msg for term in ("temporary failure", "supabase_url is required", "invalid api key", "could not resolve")):
            response = RedirectResponse(url=dest, status_code=303)
            set_auth_cookie(response, "demo-admin-token")
            return response
        return render_template("login.html", request, error=str(e), next=next)

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
