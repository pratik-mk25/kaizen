import random
import time
import json
from datetime import date, datetime, timezone, timedelta
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
import crud
from auth import get_current_user
from templates_utils import render_template, get_username_map
from notifications import send_discord_notification

router = APIRouter(prefix="/attendance", tags=["attendance"])

EDIT_CODES = {}
KIOSK_COOKIE = "kiosk_auth"
IST = timezone(timedelta(hours=5, minutes=30))

def get_ist_date():
    return datetime.now(IST).strftime("%Y-%m-%d")

def get_ist_time():
    return datetime.now(IST).strftime("%H:%M:%S")

def generate_code():
    return str(random.randint(100000, 999999))

def check_kiosk_auth(request: Request) -> bool:
    return bool(request.cookies.get(KIOSK_COOKIE))

@router.get("/")
async def attendance_view(request: Request, user: dict = Depends(get_current_user)):
    profiles = crud.get_all_users_detailed() or []
    today_str = get_ist_date()
    today_attendance = crud.get_attendance(limit=500) or []
    username_map = get_username_map() or {}
    active_ids = set()
    for a in today_attendance:
        if isinstance(a, dict) and a.get("status") == "present" and a.get("event_date") == today_str:
            notes = {}
            if a.get("notes"):
                try:
                    notes = json.loads(a["notes"])
                except (json.JSONDecodeError, TypeError):
                    notes = {}
            if isinstance(notes, dict) and "in" in notes and "out" not in notes:
                if a.get("user_id"):
                    active_ids.add(a["user_id"])
    return render_template("attendance_view.html", request, user=user, profiles=profiles,
                          today_attendance=today_attendance, today_records=today_attendance, username_map=username_map,
                          active_ids=active_ids, today_str=today_str)

@router.get("/kiosk/login")
async def kiosk_login_form(request: Request, user: dict = Depends(get_current_user)):
    if check_kiosk_auth(request):
        return RedirectResponse(url="/attendance/kiosk")
    return render_template("attendance_kiosk_login.html", request, user=user)

@router.post("/kiosk/login")
async def kiosk_login_action(request: Request, secret: str = Form(...), user: dict = Depends(get_current_user)):
    kiosk_secret = crud.get_kiosk_secret()
    if not kiosk_secret:
        return render_template("attendance_kiosk_login.html", request, user=user, error="No kiosk secret configured. Ask an admin to set it up.")
    if secret != kiosk_secret:
        return render_template("attendance_kiosk_login.html", request, user=user, error="Invalid kiosk secret")
    resp = RedirectResponse(url="/attendance/kiosk", status_code=303)
    resp.set_cookie(key=KIOSK_COOKIE, value="1", httponly=True, max_age=60*60*8, samesite="lax")
    return resp

@router.get("/kiosk/logout")
async def kiosk_logout(request: Request, user: dict = Depends(get_current_user)):
    resp = RedirectResponse(url="/attendance", status_code=303)
    resp.delete_cookie(KIOSK_COOKIE)
    return resp

@router.get("/kiosk")
async def attendance_kiosk(request: Request, user: dict = Depends(get_current_user)):
    if not check_kiosk_auth(request):
        return RedirectResponse(url="/attendance/kiosk/login", status_code=303)
    profiles = crud.get_all_users_detailed() or []
    today_str = get_ist_date()
    today_attendance = crud.get_attendance(limit=500) or []
    username_map = get_username_map() or {}
    active_ids = set()
    for a in today_attendance:
        if isinstance(a, dict) and a.get("status") == "present" and a.get("event_date") == today_str:
            notes = {}
            if a.get("notes"):
                try:
                    notes = json.loads(a["notes"])
                except (json.JSONDecodeError, TypeError):
                    notes = {}
            if isinstance(notes, dict) and "in" in notes and "out" not in notes:
                if a.get("user_id"):
                    active_ids.add(a["user_id"])
    return render_template("attendance_kiosk.html", request, user=user, profiles=profiles,
                          today_attendance=today_attendance, today_records=today_attendance, username_map=username_map,
                          active_ids=active_ids, today_str=today_str)

@router.post("/kiosk/toggle")
async def kiosk_toggle(request: Request, user_id: str = Form(...), user: dict = Depends(get_current_user)):
    if not check_kiosk_auth(request):
        return RedirectResponse(url="/attendance/kiosk/login", status_code=303)
    today_str = get_ist_date()
    result = crud.quick_toggle_attendance(user_id, today_str, user["id"])
    uname = user.get("display_name") or user.get("email", "Unknown")
    umap = get_username_map() or {}
    member_name = umap.get(user_id, user_id[:8])
    try:
        act = (result.get("action") or "toggled").upper() if isinstance(result, dict) else "TOGGLED"
        send_discord_notification(
            f"**{act}**\n**Member:** {member_name}\n**Time:** {get_ist_time()} (IST)\n**By:** {uname}",
            title="ATTENDANCE TOGGLE", color=0x00f0ff if act == "CHECKED_IN" else 0xff6b35
        )
    except Exception as e:
        print(f"Error sending discord notification: {e}")
    return RedirectResponse(url="/attendance/kiosk", status_code=303)

@router.post("/fix-all-ist")
async def fix_all_attendance_ist(request: Request, user: dict = Depends(get_current_user)):
    count = crud.fix_all_attendance_utc_to_ist(user["id"])
    return RedirectResponse(url=request.headers.get("referer", "/attendance"), status_code=303)

@router.post("/kiosk/edit-request")
async def request_edit_code(request: Request, attendance_id: str = Form(...), action: str = Form(...),
                            user: dict = Depends(get_current_user)):
    if not check_kiosk_auth(request):
        return HTMLResponse('{"error": "Kiosk auth required"}', status_code=401)
    code = generate_code()
    EDIT_CODES[code] = {
        "attendance_id": attendance_id,
        "action": action,
        "requested_by": user["id"],
        "expires_at": time.time() + 300,
        "used": False
    }
    attendance_records = crud.get_attendance(limit=500) or []
    record = next((a for a in attendance_records if isinstance(a, dict) and a.get("id") == attendance_id), None)
    member_name = "Unknown"
    if record:
        username_map = get_username_map() or {}
        member_name = username_map.get(record.get("user_id"), record.get("user_id", "Unknown"))
    try:
        send_discord_notification(
            f"**Attendance Edit Requested**\n**Member:** {member_name}\n"
            f"**Action:** {action.upper()}\n**Code:** {code}\n**Requested By:** {user.get('display_name') or user.get('email')}",
            title="ATTENDANCE EDIT", color=0xff6b35
        )
    except Exception:
        pass
    return HTMLResponse(f'{{"code": "{code}", "expires_in": 300}}', media_type="application/json")

@router.post("/kiosk/edit-confirm")
async def confirm_edit(request: Request, attendance_id: str = Form(...), code: str = Form(...),
                       event_name: str = Form(None), event_date: str = Form(None),
                       status: str = Form(None), notes: str = Form(None),
                       action: str = Form(...), user: dict = Depends(get_current_user)):
    if not check_kiosk_auth(request):
        return RedirectResponse(url="/attendance/kiosk/login", status_code=303)
    stored = EDIT_CODES.get(code)
    if not stored or stored["used"] or stored["attendance_id"] != attendance_id or time.time() > stored["expires_at"]:
        raise HTTPException(status_code=400, detail="Invalid or expired code")
    EDIT_CODES[code]["used"] = True
    if action == "delete":
        crud.delete_attendance(attendance_id, user["id"])
        try:
            send_discord_notification(
                f"**Attendance Deleted**\n**Record ID:** {attendance_id}\n**By:** {user.get('display_name') or user.get('email')}",
                title="ATTENDANCE DELETED", color=0xef4444
            )
        except Exception:
            pass
    elif action == "edit":
        if event_name and event_date and status:
            crud.update_attendance(attendance_id, event_name, event_date, status, notes, user["id"])
    return RedirectResponse(url="/attendance/kiosk", status_code=303)
