from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse
import crud
from auth import get_current_user, admin_required, lead_or_admin_required
from templates_utils import render_template, get_username_map
from notifications import notify_project_created, notify_project_lead_assigned

router = APIRouter(tags=["projects"])

@router.get("/projects/{project_id}")
async def project_detail(request: Request, project_id: str, user: dict = Depends(get_current_user)):
    project = crud.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    tasks = crud.get_tasks_for_project(project_id)
    assignable_users = crud.get_all_users_detailed() or []
    username_map = get_username_map() or {}
    task_assignees = {}
    for t in tasks:
        task_assignees[t["id"]] = crud.get_assignees(t["id"])
    return render_template("project_detail.html", request, user=user, project=project, tasks=tasks,
                           assignable_users=assignable_users, username_map=username_map, task_assignees=task_assignees)

@router.post("/projects/{project_id}/assign-lead")
async def assign_project_lead_action(request: Request, project_id: str, lead_id: str = Form(None), user: dict = Depends(get_current_user)):
    project = crud.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check permissions: Admin or Lead role or current Project Lead
    if user["role"] not in ["admin", "lead"] and project.get("lead_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")
        
    crud.update_project(project_id, project["name"], project.get("description"), lead_id if lead_id else None, user["id"])
    
    if lead_id:
        umap = get_username_map() or {}
        lead_name = umap.get(lead_id, "Member")
        uname = user.get("display_name") or user.get("email", "Admin")
        try:
            notify_project_lead_assigned(project["name"], lead_name, uname)
        except Exception:
            pass

    referer = request.headers.get("referer")
    if referer and "projects" in referer:
        return RedirectResponse(url=referer, status_code=303)
    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)

@router.get("/admin/projects/create")
async def create_project_form(request: Request, mission_id: str, user: dict = Depends(admin_required)):
    leads = crud.get_all_users_detailed() or []
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
    leads = crud.get_all_users_detailed() or []
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
