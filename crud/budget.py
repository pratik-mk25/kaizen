"""
===============================================================================
KAIZEN / MISSION AVINYA - Budget, Transactions & Dues Database Services
===============================================================================
Module Purpose:
  Provides database services for club budget categories, financial expense transactions,
  and member dues tracking with line-by-line comments.
===============================================================================
"""

# Import Python standard datetime utilities
from datetime import datetime, timezone

# Import base DB client and audit logging
from .base import _get_client, log_action


# =============================================================================
# BUDGET CATEGORIES
# =============================================================================

def get_budget_categories():
    """
    Fetches all budget category definitions (e.g. Avionics, Frame Parts, Events).
    """
    query = _get_client().table("budget_categories").select("*").order("name")
    res = query.execute()
    return res.data if (res and res.data is not None) else []


def create_budget_category(name: str, allocated_amount: float, user_id: str):
    """
    Creates a new budget allocation category.
    """
    data = {"name": name, "allocated_amount": allocated_amount}
    res = _get_client().table("budget_categories").insert(data).execute().data[0]
    log_action(user_id, "budget_category_created", "budget_category", res["id"], new_values=data)
    return res


def update_budget_category(cat_id: str, name: str, allocated_amount: float, user_id: str):
    """
    Updates budget allocation category name or allocated amount limit.
    """
    old_data = _get_client().table("budget_categories").select("*").eq("id", cat_id)
    old = old_data.single().execute().data
    new_data = {"name": name, "allocated_amount": allocated_amount}
    _get_client().table("budget_categories").update(new_data).eq("id", cat_id).execute()
    log_action(user_id, "budget_category_updated", "budget_category", cat_id, old_values=old, new_values=new_data)


def delete_budget_category(cat_id: str, user_id: str):
    """
    Deletes a budget allocation category.
    """
    _get_client().table("budget_categories").delete().eq("id", cat_id).execute()
    log_action(user_id, "budget_category_deleted", "budget_category", cat_id)


# =============================================================================
# TRANSACTIONS
# =============================================================================

def get_transactions(limit: int = 200):
    """
    Fetches recent financial transaction entries with joined category names.
    """
    query = _get_client().table("transactions").select("*, budget_categories(name)").order("transaction_date", desc=True).limit(limit)
    res = query.execute()
    return res.data if (res and res.data is not None) else []


def create_transaction(description: str, amount: float, type_: str, category_id: str | None,
                       transaction_date: str, notes: str | None, user_id: str):
    """
    Logs an expense or income transaction entry.
    """
    data = {
        "description": description,
        "amount": amount,
        "type": type_,
        "category_id": category_id,
        "transaction_date": transaction_date,
        "recorded_by": user_id,
        "notes": notes
    }
    res = _get_client().table("transactions").insert(data).execute().data[0]
    log_action(user_id, "transaction_created", "transaction", res["id"], new_values=data)
    return res


def update_transaction(txn_id: str, description: str, amount: float, type_: str, category_id: str | None,
                      transaction_date: str, notes: str | None, user_id: str):
    """
    Updates details of a financial transaction.
    """
    old = _get_client().table("transactions").select("*").eq("id", txn_id).single().execute().data
    new_data = {
        "description": description,
        "amount": amount,
        "type": type_,
        "category_id": category_id,
        "transaction_date": transaction_date,
        "notes": notes
    }
    _get_client().table("transactions").update(new_data).eq("id", txn_id).execute()
    log_action(user_id, "transaction_updated", "transaction", txn_id, old_values=old, new_values=new_data)


def delete_transaction(txn_id: str, user_id: str):
    """
    Deletes a transaction entry.
    """
    _get_client().table("transactions").delete().eq("id", txn_id).execute()
    log_action(user_id, "transaction_deleted", "transaction", txn_id)


# =============================================================================
# MEMBER DUES
# =============================================================================

def get_dues():
    """
    Fetches member dues records joined with profile usernames.
    """
    query = _get_client().table("dues").select("*, profiles(display_name, username)").order("due_date", desc=True)
    res = query.execute()
    return res.data if (res and res.data is not None) else []


def create_dues_entry(member_id: str, amount: float, period: str, due_date: str, notes: str | None,
                     user_id: str):
    """
    Creates a new membership due invoice for a member.
    """
    data = {
        "member_id": member_id,
        "amount": amount,
        "period": period,
        "due_date": due_date,
        "status": "unpaid",
        "notes": notes
    }
    res = _get_client().table("dues").insert(data).execute().data[0]
    log_action(user_id, "dues_created", "dues", res["id"], new_values=data)
    return res


def mark_dues_paid(dues_id: str, paid_date: str, user_id: str):
    """
    Marks a member due as paid with payment date timestamp.
    """
    old = _get_client().table("dues").select("*").eq("id", dues_id).single().execute().data
    new_data = {"status": "paid", "paid_date": paid_date, "updated_at": datetime.now(timezone.utc).isoformat()}
    _get_client().table("dues").update(new_data).eq("id", dues_id).execute()
    log_action(user_id, "dues_paid", "dues", dues_id, old_values=old, new_values=new_data)


def delete_dues(dues_id: str, user_id: str):
    """
    Deletes a dues entry.
    """
    _get_client().table("dues").delete().eq("id", dues_id).execute()
    log_action(user_id, "dues_deleted", "dues", dues_id)
