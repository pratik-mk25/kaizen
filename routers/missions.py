from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse
import crud
from auth import get_current_user, admin_required
from templates_utils import render_template

router = APIRouter(tags=["missions"])

@router.get("/missions/{mission_id}")
async def mission_detail(request: Request, mission_id: str, user: dict = Depends(get_current_user)):
    mission = crud.get_mission(mission_id)
    if not mission:
        raise HTTPException(status_code=403, detail="Forbidden")
    projects = crud.get_projects_for_mission(mission_id)
    return render_template("mission_detail.html", request, user=user, mission=mission, projects=projects)

@router.get("/admin/missions/create")
async def create_mission_form(request: Request, user: dict = Depends(admin_required)):
    return render_template("mission_form.html", request, user=user, mission=None)

@router.post("/admin/missions/create")
async def create_mission_action(request: Request, name: str = Form(...), description: str = Form(""), user: dict = Depends(admin_required)):
    crud.create_mission(name, description, user["id"])
    return RedirectResponse(url="/dashboard", status_code=303)

@router.get("/admin/missions/{mission_id}/edit")
async def edit_mission_form(request: Request, mission_id: str, user: dict = Depends(admin_required)):
    mission = crud.get_mission(mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    return render_template("mission_form.html", request, user=user, mission=mission)

@router.post("/admin/missions/{mission_id}/edit")
async def edit_mission_action(request: Request, mission_id: str, name: str = Form(...), description: str = Form(""), user: dict = Depends(admin_required)):
    mission = crud.get_mission(mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    crud.update_mission(mission_id, name, description, user["id"])
    return RedirectResponse(url=f"/missions/{mission_id}", status_code=303)

@router.post("/admin/missions/{mission_id}/delete")
async def delete_mission(mission_id: str, user: dict = Depends(admin_required)):
    mission = crud.get_mission(mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    crud.delete_mission(mission_id, user["id"])
    return RedirectResponse(url="/dashboard", status_code=303)
