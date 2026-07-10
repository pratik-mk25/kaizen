from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse
from datetime import date
import crud
from auth import get_current_user, admin_required
from templates_utils import render_template, get_username_map

router = APIRouter(prefix="/budget", tags=["budget"])

@router.get("")
async def budget_dashboard(request: Request, user: dict = Depends(get_current_user)):
    categories = crud.get_budget_categories()
    transactions = crud.get_transactions()
    dues = crud.get_dues()
    username_map = get_username_map()
    members = crud.get_all_users_detailed()

    total_income = sum(t["amount"] for t in transactions if t["type"] == "income")
    total_expenses = sum(t["amount"] for t in transactions if t["type"] == "expense")
    balance = total_income - total_expenses
    unpaid_dues = sum(d["amount"] for d in dues if d["status"] == "unpaid")

    return render_template("budget_dashboard.html", request, user=user,
                          categories=categories, transactions=transactions, dues=dues,
                          total_income=total_income, total_expenses=total_expenses,
                          balance=balance, unpaid_dues=unpaid_dues, username_map=username_map, members=members)

@router.post("/categories/create")
async def create_category(name: str = Form(...), allocated_amount: float = Form(0),
                          user: dict = Depends(admin_required)):
    crud.create_budget_category(name, allocated_amount, user["id"])
    return RedirectResponse(url="/budget", status_code=303)

@router.post("/categories/{cat_id}/edit")
async def edit_category(cat_id: str, name: str = Form(...), allocated_amount: float = Form(0),
                        user: dict = Depends(admin_required)):
    crud.update_budget_category(cat_id, name, allocated_amount, user["id"])
    return RedirectResponse(url="/budget", status_code=303)

@router.post("/categories/{cat_id}/delete")
async def delete_category(cat_id: str, user: dict = Depends(admin_required)):
    crud.delete_budget_category(cat_id, user["id"])
    return RedirectResponse(url="/budget", status_code=303)

@router.post("/transactions/create")
async def create_transaction(request: Request, description: str = Form(...), amount: float = Form(...),
                              type_: str = Form(...), category_id: str = Form(None),
                              transaction_date: str = Form(...), notes: str = Form(None),
                              user: dict = Depends(admin_required)):
    crud.create_transaction(description, amount, type_, category_id, transaction_date, notes, user["id"])
    return RedirectResponse(url="/budget", status_code=303)

@router.get("/transactions/{txn_id}/edit")
async def edit_transaction_form(request: Request, txn_id: str, user: dict = Depends(admin_required)):
    categories = crud.get_budget_categories()
    txn = next((t for t in crud.get_transactions() if t["id"] == txn_id), None)
    if not txn:
        raise HTTPException(status_code=404)
    return render_template("transaction_form.html", request, user=user, txn=txn, categories=categories, category_id=txn["category_id"])

@router.post("/transactions/{txn_id}/edit")
async def edit_transaction(txn_id: str, description: str = Form(...), amount: float = Form(...),
                           type_: str = Form(...), category_id: str = Form(None),
                           transaction_date: str = Form(...), notes: str = Form(None),
                           user: dict = Depends(admin_required)):
    crud.update_transaction(txn_id, description, amount, type_, category_id, transaction_date, notes, user["id"])
    return RedirectResponse(url="/budget", status_code=303)

@router.post("/transactions/{txn_id}/delete")
async def delete_transaction(txn_id: str, user: dict = Depends(admin_required)):
    crud.delete_transaction(txn_id, user["id"])
    return RedirectResponse(url="/budget", status_code=303)

@router.post("/dues/create")
async def create_dues(request: Request, member_id: str = Form(...), amount: float = Form(...),
                      period: str = Form(...), due_date: str = Form(...), notes: str = Form(None),
                      user: dict = Depends(admin_required)):
    crud.create_dues_entry(member_id, amount, period, due_date, notes, user["id"])
    return RedirectResponse(url="/budget", status_code=303)

@router.post("/dues/{dues_id}/mark-paid")
async def mark_dues_paid(dues_id: str, paid_date: str = Form(...), user: dict = Depends(admin_required)):
    crud.mark_dues_paid(dues_id, paid_date, user["id"])
    return RedirectResponse(url="/budget", status_code=303)

@router.post("/dues/{dues_id}/delete")
async def delete_dues(dues_id: str, user: dict = Depends(admin_required)):
    crud.delete_dues(dues_id, user["id"])
    return RedirectResponse(url="/budget", status_code=303)
