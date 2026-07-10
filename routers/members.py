from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse
import crud
from auth import get_current_user, admin_required, club_pc_only
from templates_utils import render_template, get_username_map

router = APIRouter(prefix="/members", tags=["members"])

@router.get("")
async def member_list(request: Request, user: dict = Depends(get_current_user)):
    profiles = crud.get_all_users_detailed()
    skills = crud.get_all_skills()
    attendance = crud.get_attendance(limit=50)
    username_map = get_username_map()
    return render_template("member_list.html", request, user=user, profiles=profiles,
                          skills=skills, attendance=attendance, username_map=username_map)

@router.get("/{member_id}")
async def member_detail(request: Request, member_id: str, user: dict = Depends(get_current_user)):
    profiles = crud.get_all_users_detailed()
    member = next((p for p in profiles if p["id"] == member_id), None)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    member_skills = crud.get_member_skills(member_id)
    all_skills = crud.get_all_skills()
    member_certs = crud.get_member_certifications(member_id)
    all_certs = crud.get_all_certifications()
    member_attendance = crud.get_attendance_for_member(member_id)
    tasks = crud.get_tasks_for_user(member_id)
    username_map = get_username_map()
    return render_template("member_detail.html", request, user=user, member=member,
                          member_skills=member_skills, all_skills=all_skills,
                          member_certs=member_certs, all_certs=all_certs,
                          attendance=member_attendance, tasks=tasks, username_map=username_map)

@router.post("/{member_id}/skills/add")
async def add_member_skill(member_id: str, skill_id: str = Form(...), proficiency_level: str = Form("beginner"),
                          user: dict = Depends(admin_required)):
    crud.set_member_skill(member_id, skill_id, proficiency_level)
    return RedirectResponse(url=f"/members/{member_id}", status_code=303)

@router.post("/{member_id}/skills/{skill_id}/remove")
async def remove_member_skill(member_id: str, skill_id: str, user: dict = Depends(admin_required)):
    crud.remove_member_skill(member_id, skill_id)
    return RedirectResponse(url=f"/members/{member_id}", status_code=303)

@router.post("/{member_id}/certifications/add")
async def add_member_cert(request: Request, member_id: str, certification_id: str = Form(...),
                          date_obtained: str = Form(...), expiry_date: str = Form(None),
                          user: dict = Depends(admin_required)):
    crud.add_member_certification(member_id, certification_id, date_obtained, expiry_date, user["id"])
    return RedirectResponse(url=f"/members/{member_id}", status_code=303)

@router.post("/{member_id}/certifications/{cert_id}/verify")
async def verify_cert(member_id: str, cert_id: str, status: str = Form(...),
                      user: dict = Depends(admin_required)):
    crud.verify_member_certification(cert_id, status)
    return RedirectResponse(url=f"/members/{member_id}", status_code=303)

@router.post("/{member_id}/certifications/{cert_id}/delete")
async def delete_member_cert(member_id: str, cert_id: str, user: dict = Depends(admin_required)):
    crud.delete_member_certification(cert_id, user["id"])
    return RedirectResponse(url=f"/members/{member_id}", status_code=303)

@router.post("/attendance/add")
async def add_attendance(request: Request, user_id: str = Form(...), event_name: str = Form(...),
                         event_date: str = Form(...), status: str = Form("present"), notes: str = Form(None),
                         _=Depends(club_pc_only), user: dict = Depends(get_current_user)):
    crud.add_attendance(user_id, event_name, event_date, status, notes, user["id"])
    return RedirectResponse(url=f"/members/{user_id}", status_code=303)

@router.post("/attendance/{att_id}/delete")
async def delete_attendance(att_id: str, request: Request, _=Depends(club_pc_only),
                            user: dict = Depends(admin_required)):
    crud.delete_attendance(att_id, user["id"])
    return RedirectResponse(url=request.headers.get("referer", "/members"), status_code=303)

@router.get("/skills/manage")
async def manage_skills(request: Request, user: dict = Depends(admin_required)):
    skills = crud.get_all_skills()
    return render_template("manage_skills.html", request, user=user, skills=skills)

@router.post("/skills/create")
async def create_skill(name: str = Form(...), category: str = Form("general"),
                       user: dict = Depends(admin_required)):
    crud.create_skill(name, category, user["id"])
    return RedirectResponse(url="/members/skills/manage", status_code=303)

@router.post("/skills/{skill_id}/delete")
async def delete_skill(skill_id: str, user: dict = Depends(admin_required)):
    crud.delete_skill(skill_id, user["id"])
    return RedirectResponse(url="/members/skills/manage", status_code=303)

@router.get("/certifications/manage")
async def manage_certs(request: Request, user: dict = Depends(admin_required)):
    certs = crud.get_all_certifications()
    return render_template("manage_certifications.html", request, user=user, certs=certs)

@router.post("/certifications/create")
async def create_cert(name: str = Form(...), issuing_body: str = Form(None),
                      user: dict = Depends(admin_required)):
    crud.create_certification(name, issuing_body, user["id"])
    return RedirectResponse(url="/members/certifications/manage", status_code=303)

@router.post("/certifications/{cert_id}/delete")
async def delete_cert(cert_id: str, user: dict = Depends(admin_required)):
    crud.delete_certification(cert_id, user["id"])
    return RedirectResponse(url="/members/certifications/manage", status_code=303)
