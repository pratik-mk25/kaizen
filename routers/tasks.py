from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
import crud
from auth import get_current_user, lead_or_admin_required
from templates_utils import render_template, get_username_map, env as jinja_env
from database import supabase_admin
from notifications import notify_task_created, notify_task_status_changed

router = APIRouter(tags=["tasks"])

@router.post("/projects/{project_id}/tasks/create")
async def add_task(request: Request, project_id: str,
                   title: str = Form(...), description: str = Form(""),
                   priority: str = Form("medium"), due_date: str = Form(""),
                   assignee_id: str = Form(None),
                   user: dict = Depends(lead_or_admin_required)):
    org_id = user.get("organization_id")
    project = crud.get_project(project_id, org_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    new_task = crud.create_task(title, description, project_id, user["id"], priority, due_date or None, org_id)
    
    # Notify Discord
    try:
        notify_task_created(new_task, user.get("email", "Unknown"))
    except:
        pass

    if assignee_id:
        crud.assign_users_to_task(new_task["id"], [assignee_id], user["id"])
    if request.headers.get("HX-Request") == "true":
        tasks = crud.get_tasks_for_project(project_id, org_id)
        task_assignees = {t["id"]: crud.get_assignees(t["id"]) for t in tasks}
        username_map = get_username_map(org_id)
        assignable_users = crud.get_all_users_detailed(org_id)
        return HTMLResponse(jinja_env.get_template("_task_list.html").render(
            tasks=tasks, task_assignees=task_assignees, username_map=username_map,
            assignable_users=assignable_users, user=user
        ))
    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)

@router.post("/tasks/{task_id}/update-status")
async def update_task_status(request: Request, task_id: str, new_status: str = Form(...),
                             user: dict = Depends(get_current_user)):
    org_id = user.get("organization_id")
    task = crud.get_task(task_id, org_id)
    if not task:
         raise HTTPException(status_code=404, detail="Task not found")
    
    old_status = task["status"]
    try:
        crud.update_task_status(task_id, new_status, user["id"], org_id)
        # Notify Discord
        notify_task_status_changed(task, old_status, new_status, user.get("email", "Unknown"))
    except Exception:
        pass
    task = crud.get_task(task_id, org_id)
    if request.headers.get("HX-Request") == "true":
        task_assignees = {task["id"]: crud.get_assignees(task["id"])}
        username_map = get_username_map(org_id)
        return HTMLResponse(jinja_env.get_template("_task_card.html").render(
            task=task, task_assignees=task_assignees, username_map=username_map, user=user
        ))
    return RedirectResponse(url=f"/projects/{task['project_id']}", status_code=303)

@router.post("/tasks/{task_id}/assign")
async def assign_task_endpoint(task_id: str, request: Request, user: dict = Depends(lead_or_admin_required)):
    org_id = user.get("organization_id")
    task = crud.get_task(task_id, org_id)
    if not task:
         raise HTTPException(status_code=404, detail="Task not found")
    form_data = await request.form()
    assigned = form_data.getlist("assignee_ids")
    crud.assign_users_to_task(task_id, assigned, user["id"])
    return RedirectResponse(url=f"/tasks/{task_id}", status_code=303)

@router.get("/tasks/{task_id}")
async def task_detail(request: Request, task_id: str, user: dict = Depends(get_current_user)):
    org_id = user.get("organization_id")
    task = crud.get_task(task_id, org_id)
    if not task:
         raise HTTPException(status_code=404, detail="Task not found")
    assignable_users = crud.get_all_users_detailed(org_id)
    comments = crud.get_comments_for_task(task_id, org_id)
    username_map = get_username_map(org_id)
    assignees = crud.get_assignees(task_id)
    attachments = []
    try:
        attachments = crud.get_attachments(task_id, org_id)
        if attachments:
            for att in attachments:
                try:
                    signed = supabase_admin.storage.from_("task-attachments") \
                        .create_signed_url(att["storage_path"], 3600)
                    att["signed_url"] = signed["signedURL"] if signed else None
                except:
                    att["signed_url"] = None
    except:
        attachments = []
    return render_template("task_detail.html", request, user=user, task=task,
                           assignable_users=assignable_users, comments=comments,
                           username_map=username_map, assignees=assignees,
                           attachments=attachments)

@router.post("/tasks/{task_id}/comment")
async def add_comment_endpoint(request: Request, task_id: str, content: str = Form(...),
                               user: dict = Depends(get_current_user)):
    org_id = user.get("organization_id")
    task = crud.get_task(task_id, org_id)
    if not task:
         raise HTTPException(status_code=404, detail="Task not found")
    new_comment = crud.add_comment(task_id, content, user["id"], org_id)
    if request.headers.get("HX-Request") == "true":
        username_map = get_username_map(org_id)
        return HTMLResponse(jinja_env.get_template("_comment.html").render(
            comment=new_comment, username=username_map.get(user['id'], 'Unknown')
        ))
    return RedirectResponse(url=f"/tasks/{task_id}", status_code=303)

@router.post("/tasks/{task_id}/attachments")
async def upload_attachment(request: Request, task_id: str,
                            user: dict = Depends(get_current_user)):
    org_id = user.get("organization_id")
    task = crud.get_task(task_id, org_id)
    if not task:
         raise HTTPException(status_code=404, detail="Task not found")
    form_data = await request.form()
    file = form_data.get("file")
    if not file:
        return HTMLResponse("No file provided", status_code=400)
    filename = file.filename
    storage_path = f"{task_id}/{filename}"
    contents = await file.read()
    mime = file.content_type
    size = len(contents)
    supabase_admin.storage.from_("task-attachments").upload(
        storage_path, contents, {"content-type": mime}
    )
    crud.add_attachment(task_id, user["id"], filename, storage_path, mime, size, org_id)
    attachments = crud.get_attachments(task_id, org_id)
    for att in attachments:
        signed = supabase_admin.storage.from_("task-attachments") \
            .create_signed_url(att["storage_path"], 3600)
        att["signed_url"] = signed["signedURL"] if signed else None
    if request.headers.get("HX-Request") == "true":
        return HTMLResponse(jinja_env.get_template("_attachment_list.html").render(attachments=attachments, task=crud.get_task(task_id, org_id)))
    return RedirectResponse(url=f"/tasks/{task_id}", status_code=303)

@router.post("/tasks/{task_id}/attachments/{attachment_id}/delete")
async def delete_attachment_endpoint(task_id: str, attachment_id: str,
                                     user: dict = Depends(lead_or_admin_required)):
    org_id = user.get("organization_id")
    task = crud.get_task(task_id, org_id)
    if not task:
         raise HTTPException(status_code=404, detail="Task not found")
    crud.delete_attachment(attachment_id, user["id"], org_id)
    attachments = crud.get_attachments(task_id, org_id)
    for att in attachments:
        signed = supabase_admin.storage.from_("task-attachments") \
            .create_signed_url(att["storage_path"], 3600)
        att["signed_url"] = signed["signedURL"] if signed else None
    if request.headers.get("HX-Request") == "true":
        return HTMLResponse(jinja_env.get_template("_attachment_list.html").render(attachments=attachments, task=crud.get_task(task_id, org_id)))
    return RedirectResponse(url=f"/tasks/{task_id}", status_code=303)
