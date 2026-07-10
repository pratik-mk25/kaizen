import random
import time
import json
from datetime import date, datetime
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
import crud
from auth import get_current_user
from templates_utils import render_template, get_username_map
from notifications import send_discord_notification

router = APIRouter(prefix="/attendance", tags=["attendance"])

EDIT_CODES = {}
KIOSK_COOKIE = "kiosk_auth"

def generate_code():
    return str(random.randint(100000, 999999))

def kiosk_required(request: Request):
    if not request.cookies.get(KIOSK_COOKIE):
        raise HTTPException(status_code=303, detail="Kiosk auth required")

@router.get("/")
async def attendance_view(request: Request, user: dict = Depends(get_current_user)):
    profiles = crud.get_all_users_detailed()
    today_str = date.today().isoformat()
    today_attendance = crud.get_attendance(limit=500)
    username_map = get_username_map()
    active_ids = set()
    for a in today_attendance:
        if a["status"] == "present" and a["event_date"] == today_str:
            notes = {}
            if a.get("notes"):
                try:
                    notes = json.loads(a["notes"])
                except (json.JSONDecodeError, TypeError):
                    notes = {}
            if "in" in notes and "out" not in notes:
                active_ids.add(a["user_id"])
    return render_template("attendance_view.html", request, user=user, profiles=profiles,
                          today_attendance=today_attendance, username_map=username_map,
                          active_ids=active_ids, today_str=today_str)

@router.get("/kiosk/login")
async def kiosk_login_form(request: Request, user: dict = Depends(get_current_user)):
    if request.cookies.get(KIOSK_COOKIE):
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
async def attendance_kiosk(request: Request, _=Depends(kiosk_required), user: dict = Depends(get_current_user)):
    profiles = crud.get_all_users_detailed()
    today_str = date.today().isoformat()
    today_attendance = crud.get_attendance(limit=500)
    username_map = get_username_map()
    import json
    active_ids = set()
    for a in today_attendance:
        if a["status"] == "present" and a["event_date"] == today_str:
            notes = {}
            if a.get("notes"):
                try:
                    notes = json.loads(a["notes"])
                except (json.JSONDecodeError, TypeError):
                    notes = {}
            if "in" in notes and "out" not in notes:
                active_ids.add(a["user_id"])
    return render_template("attendance_kiosk.html", request, user=user, profiles=profiles,
                          today_attendance=today_attendance, username_map=username_map,
                          active_ids=active_ids, today_str=today_str)

@router.post("/kiosk/toggle")
async def kiosk_toggle(request: Request, user_id: str = Form(...), _=Depends(kiosk_required),
                       user: dict = Depends(get_current_user)):
    today_str = date.today().isoformat()
    result = crud.quick_toggle_attendance(user_id, today_str, user["id"])
    uname = user.get("display_name") or user.get("email", "Unknown")
    umap = get_username_map()
    member_name = umap.get(user_id, user_id[:8])
    send_discord_notification(
        f"**{result['action'].upper()}**\n**Member:** {member_name}\n**Time:** {datetime.now().strftime('%H:%M:%S')}\n**By:** {uname}",
        title="ATTENDANCE TOGGLE", color=0x00f0ff if result["action"] == "checked_in" else 0xff6b35
    )
    return RedirectResponse(url="/attendance/kiosk", status_code=303)

@router.post("/kiosk/edit-request")
async def request_edit_code(attendance_id: str = Form(...), action: str = Form(...),
                            _=Depends(kiosk_required), user: dict = Depends(get_current_user)):
    code = generate_code()
    EDIT_CODES[code] = {
        "attendance_id": attendance_id,
        "action": action,
        "requested_by": user["id"],
        "expires_at": time.time() + 300,
        "used": False
    }
    attendance_records = crud.get_attendance(limit=500)
    record = next((a for a in attendance_records if a["id"] == attendance_id), None)
    member_name = "Unknown"
    if record:
        username_map = get_username_map()
        member_name = username_map.get(record.get("user_id"), record.get("user_id", "Unknown"))
    send_discord_notification(
        f"**Attendance Edit Requested**\n**Member:** {member_name}\n"
        f"**Action:** {action.upper()}\n**Code:** {code}\n**Requested By:** {user.get('display_name') or user.get('email')}",
        title="ATTENDANCE EDIT", color=0xff6b35
    )
    return HTMLResponse(f'{{"code": "{code}", "expires_in": 300}}', media_type="application/json")

@router.post("/kiosk/edit-confirm")
async def confirm_edit(request: Request, attendance_id: str = Form(...), code: str = Form(...),
                       event_name: str = Form(None), event_date: str = Form(None),
                       status: str = Form(None), notes: str = Form(None),
                       action: str = Form(...), _=Depends(kiosk_required),
                       user: dict = Depends(get_current_user)):
    stored = EDIT_CODES.get(code)
    if not stored or stored["used"] or stored["attendance_id"] != attendance_id or time.time() > stored["expires_at"]:
        raise HTTPException(status_code=400, detail="Invalid or expired code")
    EDIT_CODES[code]["used"] = True
    if action == "delete":
        crud.delete_attendance(attendance_id, user["id"])
        send_discord_notification(
            f"**Attendance Deleted**\n**Record ID:** {attendance_id}\n**By:** {user.get('display_name') or user.get('email')}",
            title="ATTENDANCE DELETED", color=0xef4444
        )
    elif action == "edit":
        if event_name and event_date and status:
            crud.update_attendance(attendance_id, event_name, event_date, status, notes, user["id"])
    return RedirectResponse(url="/attendance/kiosk", status_code=303)
