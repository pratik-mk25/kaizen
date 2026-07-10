from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
import crud
from auth import get_current_user, admin_required, lead_or_admin_required
from templates_utils import render_template, get_username_map

router = APIRouter(prefix="/equipment", tags=["equipment"])

@router.get("")
async def equipment_list(request: Request, user: dict = Depends(get_current_user)):
    items = crud.get_all_equipment()
    return render_template("equipment_list.html", request, user=user, items=items)

@router.get("/new")
async def equipment_create_form(request: Request, user: dict = Depends(get_current_user)):
    members = crud.get_all_users_detailed()
    return render_template("equipment_form.html", request, user=user, item=None, members=members)

@router.post("/new")
async def equipment_create_action(request: Request, name: str = Form(...), equipment_type: str = Form(...),
                                   serial_number: str = Form(None), brand: str = Form(None), model: str = Form(None),
                                   status: str = Form("available"), condition: str = Form("good"),
                                   purchase_date: str = Form(None), purchase_price: float = Form(None),
                                   assigned_to: str = Form(None), notes: str = Form(None),
                                   user: dict = Depends(get_current_user)):
    crud.create_equipment(name, equipment_type, serial_number, brand, model, status, condition,
                          purchase_date, purchase_price, assigned_to, notes, user["id"])
    return RedirectResponse(url="/equipment", status_code=303)

@router.get("/inventory")
async def inventory_list(request: Request, user: dict = Depends(get_current_user)):
    items = crud.get_all_inventory()
    low_stock = [i for i in items if i["quantity"] <= i["min_threshold"]]
    return render_template("inventory_list.html", request, user=user, items=items, low_stock=low_stock)

@router.get("/inventory/new")
async def inventory_form(request: Request, user: dict = Depends(get_current_user)):
    return render_template("inventory_form.html", request, user=user, item=None)

@router.post("/inventory/new")
async def create_inventory(request: Request, name: str = Form(...), category: str = Form(...),
                            quantity: int = Form(0), min_threshold: int = Form(5), unit: str = Form("piece"),
                            location: str = Form(None), notes: str = Form(None),
                            user: dict = Depends(get_current_user)):
    crud.create_inventory_item(name, category, quantity, min_threshold, unit, location, notes, user["id"])
    return RedirectResponse(url="/equipment/inventory", status_code=303)

@router.get("/inventory/{item_id}/edit")
async def inventory_edit_form(request: Request, item_id: str, user: dict = Depends(get_current_user)):
    item = crud.get_inventory_item(item_id)
    if not item:
        raise HTTPException(status_code=404)
    return render_template("inventory_form.html", request, user=user, item=item)

@router.post("/inventory/{item_id}/edit")
async def inventory_edit_action(request: Request, item_id: str, name: str = Form(...), category: str = Form(...),
                              quantity: int = Form(0), min_threshold: int = Form(5), unit: str = Form("piece"),
                              location: str = Form(None), notes: str = Form(None),
                              user: dict = Depends(get_current_user)):
    crud.update_inventory_item(item_id, name, category, quantity, min_threshold, unit, location, notes, user["id"])
    return RedirectResponse(url="/equipment/inventory", status_code=303)

@router.post("/inventory/{item_id}/delete")
async def inventory_delete(item_id: str, user: dict = Depends(get_current_user)):
    crud.delete_inventory_item(item_id, user["id"])
    return RedirectResponse(url="/equipment/inventory", status_code=303)

@router.post("/inventory/{item_id}/adjust")
async def inventory_adjust(request: Request, item_id: str, change_amount: int = Form(...),
                           transaction_type: str = Form(...), notes: str = Form(None),
                           user: dict = Depends(get_current_user)):
    item = crud.get_inventory_item(item_id)
    if not item:
        raise HTTPException(status_code=404)
    new_qty = item["quantity"] + change_amount
    if new_qty < 0:
        new_qty = 0
    crud.update_inventory_item(item_id, item["name"], item["category"], new_qty, item["min_threshold"],
                               item["unit"], item.get("location"), item.get("notes"), user["id"])
    crud.log_inventory_transaction(item_id, change_amount, transaction_type, None, notes, user["id"])
    return RedirectResponse(url="/equipment/inventory", status_code=303)

@router.get("/{item_id}")
async def equipment_detail(request: Request, item_id: str, user: dict = Depends(get_current_user)):
    item = crud.get_equipment(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Equipment not found")
    maintenance = crud.get_maintenance_logs(item_id)
    username_map = get_username_map()
    return render_template("equipment_detail.html", request, user=user, item=item, maintenance=maintenance, username_map=username_map)

@router.get("/{item_id}/edit")
async def equipment_edit_form(request: Request, item_id: str, user: dict = Depends(get_current_user)):
    item = crud.get_equipment(item_id)
    if not item:
        raise HTTPException(status_code=404)
    members = crud.get_all_users_detailed()
    return render_template("equipment_form.html", request, user=user, item=item, members=members)

@router.post("/{item_id}/edit")
async def equipment_edit_action(request: Request, item_id: str, name: str = Form(...),
                                equipment_type: str = Form(...), serial_number: str = Form(None),
                                brand: str = Form(None), model: str = Form(None),
                                status: str = Form("available"), condition: str = Form("good"),
                                purchase_date: str = Form(None), purchase_price: float = Form(None),
                                assigned_to: str = Form(None), notes: str = Form(None),
                                user: dict = Depends(get_current_user)):
    crud.update_equipment(item_id, name, equipment_type, brand, model, serial_number, status, condition,
                          purchase_date, purchase_price, assigned_to, notes, user["id"])
    return RedirectResponse(url=f"/equipment/{item_id}", status_code=303)

@router.post("/{item_id}/delete")
async def equipment_delete(item_id: str, user: dict = Depends(get_current_user)):
    crud.delete_equipment(item_id, user["id"])
    return RedirectResponse(url="/equipment", status_code=303)

@router.post("/{item_id}/maintenance")
async def add_maintenance(request: Request, item_id: str, description: str = Form(...),
                          maintenance_date: str = Form(...), cost: float = Form(0), notes: str = Form(None),
                          user: dict = Depends(get_current_user)):
    crud.add_maintenance_log(item_id, description, maintenance_date, user["id"], cost, notes, user["id"])
    return RedirectResponse(url=f"/equipment/{item_id}", status_code=303)

@router.post("/maintenance/{log_id}/delete")
async def delete_maintenance(log_id: str, request: Request, user: dict = Depends(get_current_user)):
    crud.delete_maintenance_log(log_id, user["id"])
    return RedirectResponse(url=request.headers.get("referer", "/equipment"), status_code=303)
