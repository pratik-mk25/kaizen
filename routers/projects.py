from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse
import crud
from auth import get_current_user, admin_required
from templates_utils import render_template, get_username_map
from notifications import notify_project_created

router = APIRouter(tags=["projects"])

@router.get("/projects/{project_id}")
async def project_detail(request: Request, project_id: str, user: dict = Depends(get_current_user)):
    project = crud.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    tasks = crud.get_tasks_for_project(project_id)
    assignable_users = crud.get_all_users_detailed()
    username_map = get_username_map()
    task_assignees = {}
    for t in tasks:
        task_assignees[t["id"]] = crud.get_assignees(t["id"])
    return render_template("project_detail.html", request, user=user, project=project, tasks=tasks,
                           assignable_users=assignable_users, username_map=username_map, task_assignees=task_assignees)

@router.get("/admin/projects/create")
async def create_project_form(request: Request, mission_id: str, user: dict = Depends(admin_required)):
    leads = crud.get_users_by_role("lead")
    return render_template("project_form.html", request, user=user, mission_id=mission_id, project=None, leads=leads)

@router.post("/admin/projects/create")
async def create_project_action(request: Request, mission_id: str = Form(...), name: str = Form(...), description: str = Form(""), lead_id: str = Form(None), user: dict = Depends(admin_required)):
    new_project = crud.create_project(name, description, mission_id, lead_id if lead_id else None, user["id"])
    try:
        notify_project_created(new_project, user.get("email", "Unknown"))
    except:
        pass
    return RedirectResponse(url=f"/missions/{mission_id}", status_code=303)

@router.get("/admin/projects/{project_id}/edit")
async def edit_project_form(request: Request, project_id: str, user: dict = Depends(admin_required)):
    project = crud.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    leads = crud.get_users_by_role("lead")
    return render_template("project_form.html", request, user=user, project=project, mission_id=project["mission_id"], leads=leads)

@router.post("/admin/projects/{project_id}/edit")
async def edit_project_action(request: Request, project_id: str, name: str = Form(...), description: str = Form(""), lead_id: str = Form(None), user: dict = Depends(admin_required)):
    project = crud.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    crud.update_project(project_id, name, description, lead_id if lead_id else None, user["id"])
    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)

@router.post("/admin/projects/{project_id}/delete")
async def delete_project(project_id: str, user: dict = Depends(admin_required)):
    project = crud.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    mission_id = project["mission_id"]
    crud.delete_project(project_id, user["id"])
    return RedirectResponse(url=f"/missions/{mission_id}", status_code=303)
