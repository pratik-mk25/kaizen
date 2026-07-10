from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse
import crud
from auth import get_current_user, admin_required
from templates_utils import render_template, get_username_map

router = APIRouter(prefix="/docs", tags=["docs"])

@router.get("")
async def document_list(request: Request, category: str = None, user: dict = Depends(get_current_user)):
    docs = crud.get_all_documents(category=category)
    username_map = get_username_map()
    return render_template("document_list.html", request, user=user, docs=docs, selected_category=category, username_map=username_map)

@router.get("/new")
async def document_create_form(request: Request, user: dict = Depends(get_current_user)):
    return render_template("document_form.html", request, user=user, doc=None)

@router.post("/new")
async def create_document(request: Request, title: str = Form(...), content: str = Form(...),
                          category: str = Form("general"), tags: str = Form(""),
                          published: bool = Form(True), user: dict = Depends(get_current_user)):
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    crud.create_document(title, content, category, tag_list, published, user["id"])
    return RedirectResponse(url="/docs", status_code=303)

@router.get("/{doc_id}")
async def document_detail(request: Request, doc_id: str, user: dict = Depends(get_current_user)):
    doc = crud.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    username_map = get_username_map()
    return render_template("document_detail.html", request, user=user, doc=doc, username_map=username_map)

@router.get("/{doc_id}/edit")
async def document_edit_form(request: Request, doc_id: str, user: dict = Depends(get_current_user)):
    doc = crud.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404)
    return render_template("document_form.html", request, user=user, doc=doc)

@router.post("/{doc_id}/edit")
async def edit_document(doc_id: str, title: str = Form(...), content: str = Form(...),
                      category: str = Form("general"), tags: str = Form(""),
                      published: bool = Form(True), user: dict = Depends(get_current_user)):
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    crud.update_document(doc_id, title, content, category, tag_list, published, user["id"])
    return RedirectResponse(url=f"/docs/{doc_id}", status_code=303)

@router.post("/{doc_id}/delete")
async def delete_document(doc_id: str, user: dict = Depends(admin_required)):
    crud.delete_document(doc_id, user["id"])
    return RedirectResponse(url="/docs", status_code=303)