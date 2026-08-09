from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse
import crud
from auth import get_current_user, lead_or_admin_required
from templates_utils import render_template, get_username_map

router = APIRouter(prefix="/flights", tags=["flights"])

@router.get("")
async def flight_logs_list(request: Request, user: dict = Depends(get_current_user)):
    logs = crud.get_all_flight_logs()
    equipment = crud.get_all_equipment()
    batteries = crud.get_all_battery_packs()
    members = crud.get_all_users_detailed()
    username_map = get_username_map()
    
    # Calculate stats
    total_minutes = sum(l.get("duration_minutes", 0) for l in logs)
    total_flights = len(logs)
    
    return render_template("flights_list.html", request, user=user, logs=logs,
                          equipment=equipment, batteries=batteries, members=members,
                          username_map=username_map, total_minutes=total_minutes,
                          total_flights=total_flights)

@router.get("/new")
async def flight_log_form(request: Request, user: dict = Depends(get_current_user)):
    equipment = crud.get_all_equipment()
    batteries = crud.get_all_battery_packs()
    members = crud.get_all_users_detailed()
    return render_template("flight_form.html", request, user=user, equipment=equipment,
                          batteries=batteries, members=members)

@router.post("/new")
async def create_flight_action(request: Request,
                               pilot_id: str = Form(...),
                               equipment_id: str = Form(None),
                               battery_id: str = Form(None),
                               flight_date: str = Form(...),
                               duration_minutes: int = Form(...),
                               location: str = Form(None),
                               purpose: str = Form(None),
                               notes: str = Form(None),
                               user: dict = Depends(get_current_user)):
    crud.create_flight_log(pilot_id, equipment_id, battery_id, flight_date,
                          duration_minutes, location, purpose, notes, user["id"])
    return RedirectResponse(url="/flights", status_code=303)

@router.post("/{log_id}/delete")
async def delete_flight_action(log_id: str, user: dict = Depends(get_current_user)):
    crud.delete_flight_log(log_id, user["id"])
    return RedirectResponse(url="/flights", status_code=303)

# ---------- Batteries ----------
@router.get("/batteries")
async def batteries_list(request: Request, user: dict = Depends(get_current_user)):
    batteries = crud.get_all_battery_packs()
    healthy_count = sum(1 for b in batteries if b.get("status") == "healthy")
    return render_template("batteries_list.html", request, user=user, batteries=batteries,
                          healthy_count=healthy_count)

@router.post("/batteries/new")
async def create_battery_action(request: Request,
                                name: str = Form(...),
                                cell_count: str = Form("4S"),
                                capacity_mah: int = Form(1500),
                                status: str = Form("healthy"),
                                notes: str = Form(None),
                                user: dict = Depends(get_current_user)):
    crud.create_battery_pack(name, cell_count, capacity_mah, status, notes, user["id"])
    return RedirectResponse(url="/flights/batteries", status_code=303)

@router.post("/batteries/{battery_id}/cycle")
async def cycle_battery_action(battery_id: str, user: dict = Depends(get_current_user)):
    crud.increment_battery_cycle(battery_id, user["id"])
    return RedirectResponse(url="/flights/batteries", status_code=303)

@router.post("/batteries/{battery_id}/status")
async def status_battery_action(battery_id: str, status: str = Form(...), user: dict = Depends(get_current_user)):
    crud.update_battery_status(battery_id, status, user["id"])
    return RedirectResponse(url="/flights/batteries", status_code=303)
