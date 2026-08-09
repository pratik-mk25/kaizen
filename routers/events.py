from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse
import crud
from auth import get_current_user, lead_or_admin_required
from templates_utils import render_template, get_username_map

router = APIRouter(prefix="/events", tags=["events"])

@router.get("")
async def events_list(request: Request, user: dict = Depends(get_current_user)):
    events = crud.get_all_events()
    probation_members = crud.get_probation_members()
    username_map = get_username_map()
    
    # Calculate probation stats
    attendance_records = crud.get_attendance(limit=200)
    probation_stats = []
    for m in probation_members:
        uid = m["id"]
        count = sum(1 for a in attendance_records if a.get("user_id") == uid and a.get("status") == "present")
        probation_stats.append({
            "member": m,
            "attended_count": count
        })
        
    return render_template("events_list.html", request, user=user, events=events,
                          probation_stats=probation_stats, username_map=username_map)

@router.get("/new")
async def create_event_form(request: Request, user: dict = Depends(get_current_user)):
    return render_template("event_form.html", request, user=user)

@router.post("/new")
async def create_event_action(request: Request,
                              title: str = Form(...),
                              description: str = Form(None),
                              event_type: str = Form("workshop"),
                              event_date: str = Form(...),
                              location: str = Form(None),
                              user: dict = Depends(get_current_user)):
    crud.create_event(title, description, event_type, event_date, location, user["id"])
    return RedirectResponse(url="/events", status_code=303)

@router.get("/{event_id}")
async def event_detail(request: Request, event_id: str, user: dict = Depends(get_current_user)):
    event = crud.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    attendees = crud.get_event_attendees(event_id)
    all_members = crud.get_all_users_detailed()
    username_map = get_username_map()
    
    return render_template("event_detail.html", request, user=user, event=event,
                          attendees=attendees, members=all_members, username_map=username_map)

@router.post("/{event_id}/rsvp")
async def rsvp_action(request: Request, event_id: str, status: str = Form("registered"),
                      notes: str = Form(None), user: dict = Depends(get_current_user)):
    crud.rsvp_event(event_id, user["id"], status, notes)
    return RedirectResponse(url=f"/events/{event_id}", status_code=303)

@router.post("/{event_id}/attendance")
async def mark_attendance_action(request: Request, event_id: str, user_id: str = Form(...),
                                status: str = Form("attended"), notes: str = Form(None),
                                user: dict = Depends(get_current_user)):
    crud.rsvp_event(event_id, user_id, status, notes)
    return RedirectResponse(url=f"/events/{event_id}", status_code=303)

@router.post("/{event_id}/delete")
async def delete_event_action(event_id: str, user: dict = Depends(get_current_user)):
    crud.delete_event(event_id, user["id"])
    return RedirectResponse(url="/events", status_code=303)
