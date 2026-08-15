"""
===============================================================================
KAIZEN / MISSION AVINYA - Equipment, Inventory & Checkout Database Services
===============================================================================
Module Purpose:
  Provides database services for hardware equipment, maintenance logs, consumable inventory,
  stock adjustments, and equipment borrower checkout/return workflows with line-by-line comments.
===============================================================================
"""

# Import Python standard datetime utilities
from datetime import datetime, timezone

# Import base client and audit logging
from .base import _get_client, log_action


# =============================================================================
# EQUIPMENT MANAGEMENT
# =============================================================================

def get_all_equipment():
    """
    Fetches all hardware equipment items ordered by creation timestamp descending.
    """
    query = _get_client().table("equipment").select("*").order("created_at", desc=True)
    res = query.execute()
    return res.data if (res and res.data is not None) else []


def get_equipment(equipment_id: str):
    """
    Fetches a single equipment record by its UUID identifier.
    """
    query = _get_client().table("equipment").select("*").eq("id", equipment_id)
    return query.single().execute().data


def create_equipment(name: str, equipment_type: str, serial_number: str | None, brand: str | None,
                     model: str | None, condition: str, location: str | None, notes: str | None,
                     user_id: str):
    """
    Registers new hardware equipment in the inventory system.
    """
    data = {
        "name": name,
        "equipment_type": equipment_type,
        "serial_number": serial_number,
        "brand": brand,
        "model": model,
        "condition": condition,
        "location": location,
        "notes": notes,
        "status": "available"  # Default initial status
    }
    res = _get_client().table("equipment").insert(data).execute().data[0]
    log_action(user_id, "equipment_created", "equipment", res["id"], new_values=data)
    return res


def update_equipment(equipment_id: str, name: str, equipment_type: str, brand: str | None,
                     model: str | None, serial_number: str | None, condition: str,
                     status: str, location: str | None, notes: str | None, user_id: str):
    """
    Updates specs, condition, or status of existing equipment.
    """
    old = get_equipment(equipment_id)
    new_data = {
        "name": name,
        "equipment_type": equipment_type,
        "brand": brand,
        "model": model,
        "serial_number": serial_number,
        "condition": condition,
        "status": status,
        "location": location,
        "notes": notes,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    _get_client().table("equipment").update(new_data).eq("id", equipment_id).execute()
    log_action(user_id, "equipment_updated", "equipment", equipment_id, old_values=old, new_values=new_data)


def delete_equipment(equipment_id: str, user_id: str):
    """
    Deletes an equipment record from the database.
    """
    old = get_equipment(equipment_id)
    _get_client().table("equipment").delete().eq("id", equipment_id).execute()
    log_action(user_id, "equipment_deleted", "equipment", equipment_id, old_values=old)


# =============================================================================
# MAINTENANCE LOGS
# =============================================================================

def get_maintenance_logs(equipment_id: str):
    """
    Fetches maintenance history entries for a specific piece of equipment.
    """
    query = _get_client().table("equipment_maintenance_logs").select("*").eq("equipment_id", equipment_id).order("maintenance_date", desc=True)
    res = query.execute()
    return res.data if (res and res.data is not None) else []


def add_maintenance_log(equipment_id: str, description: str, maintenance_date: str, performed_by: str | None,
                        cost: float | None, notes: str | None, user_id: str):
    """
    Logs a maintenance repair or service record for equipment.
    """
    data = {
        "equipment_id": equipment_id,
        "description": description,
        "maintenance_date": maintenance_date,
        "performed_by": performed_by,
        "cost": cost,
        "notes": notes
    }
    res = _get_client().table("equipment_maintenance_logs").insert(data).execute().data[0]
    log_action(user_id, "maintenance_log_added", "equipment_maintenance_log", res["id"], new_values=data)
    return res


def delete_maintenance_log(log_id: str, user_id: str):
    """
    Deletes a maintenance log entry.
    """
    _get_client().table("equipment_maintenance_logs").delete().eq("id", log_id).execute()
    log_action(user_id, "maintenance_log_deleted", "equipment_maintenance_log", log_id)


# =============================================================================
# CONSUMABLE INVENTORY
# =============================================================================

def get_all_inventory():
    """
    Fetches all consumable inventory items (e.g., propellers, screws, wiring).
    """
    query = _get_client().table("inventory_items").select("*").order("name")
    res = query.execute()
    return res.data if (res and res.data is not None) else []


def get_inventory_item(item_id: str):
    """
    Fetches a single consumable inventory item.
    """
    query = _get_client().table("inventory_items").select("*").eq("id", item_id)
    return query.single().execute().data


def create_inventory_item(name: str, category: str, quantity: int, min_threshold: int, unit: str,
                          location: str | None, notes: str | None, user_id: str):
    """
    Creates a new consumable inventory item record.
    """
    data = {
        "name": name,
        "category": category,
        "quantity": quantity,
        "min_threshold": min_threshold,
        "unit": unit,
        "location": location,
        "notes": notes
    }
    res = _get_client().table("inventory_items").insert(data).execute().data[0]
    log_action(user_id, "inventory_created", "inventory_item", res["id"], new_values=data)
    return res


def update_inventory_item(item_id: str, name: str, category: str, quantity: int, min_threshold: int,
                          unit: str, location: str | None, notes: str | None, user_id: str):
    """
    Updates details or stock counts for a consumable item.
    """
    old = get_inventory_item(item_id)
    new_data = {
        "name": name,
        "category": category,
        "quantity": quantity,
        "min_threshold": min_threshold,
        "unit": unit,
        "location": location,
        "notes": notes,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    _get_client().table("inventory_items").update(new_data).eq("id", item_id).execute()
    log_action(user_id, "inventory_updated", "inventory_item", item_id, old_values=old, new_values=new_data)


def delete_inventory_item(item_id: str, user_id: str):
    """
    Deletes an inventory item record.
    """
    old = get_inventory_item(item_id)
    _get_client().table("inventory_items").delete().eq("id", item_id).execute()
    log_action(user_id, "inventory_deleted", "inventory_item", item_id, old_values=old)


def log_inventory_transaction(item_id: str, change_amount: int, transaction_type: str, reference: str | None,
                              notes: str | None, user_id: str):
    """
    Logs an inventory stock adjustment (+ in stock, - restock/use).
    """
    data = {
        "inventory_item_id": item_id,
        "change_amount": change_amount,
        "transaction_type": transaction_type,
        "reference": reference,
        "recorded_by": user_id,
        "notes": notes
    }
    res = _get_client().table("inventory_transactions").insert(data).execute().data[0]
    
    # Adjust total quantity in inventory_items table
    item = get_inventory_item(item_id)
    new_qty = (item.get("quantity") or 0) + change_amount
    _get_client().table("inventory_items").update({"quantity": new_qty}).eq("id", item_id).execute()
    log_action(user_id, "inventory_transaction_logged", "inventory_transaction", res["id"], new_values=data)
    return res


def get_inventory_transactions(item_id: str):
    """
    Fetches stock transaction logs for an inventory item.
    """
    query = _get_client().table("inventory_transactions").select("*").eq("inventory_item_id", item_id).order("created_at", desc=True)
    res = query.execute()
    return res.data if (res and res.data is not None) else []


# =============================================================================
# EQUIPMENT CHECKOUTS & RETURNS
# =============================================================================

def get_active_checkouts():
    """
    Fetches all currently unreturned equipment checkout records.
    """
    try:
        query = _get_client().table("equipment_checkouts").select("*").is_("returned_at", "null").order("checked_out_at", desc=True)
        res = query.execute()
        return res.data if (res and res.data is not None) else []
    except Exception as e:
        print(f"Error fetching active checkouts: {e}")
        return []


def get_checkouts_for_equipment(equipment_id: str):
    """
    Fetches checkout history for a specific piece of equipment.
    """
    try:
        query = _get_client().table("equipment_checkouts").select("*").eq("equipment_id", equipment_id).order("checked_out_at", desc=True)
        res = query.execute()
        return res.data if (res and res.data is not None) else []
    except Exception as e:
        print(f"Error fetching checkouts for equipment: {e}")
        return []


def checkout_equipment(equipment_id: str, borrower_id: str, expected_return_at: str | None,
                       condition: str, notes: str | None, user_id: str):
    """
    Checks out equipment to a member and updates equipment status to 'in_use'.
    """
    data = {
        "equipment_id": equipment_id,
        "borrower_id": borrower_id,
        "expected_return_at": expected_return_at,
        "condition_on_checkout": condition,
        "notes": notes
    }
    res = _get_client().table("equipment_checkouts").insert(data).execute().data[0]
    
    # Update equipment status to in_use and set assigned borrower
    _get_client().table("equipment").update({"status": "in_use", "assigned_to": borrower_id}).eq("id", equipment_id).execute()
    log_action(user_id, "equipment_checked_out", "equipment_checkout", res["id"], new_values=data)
    return res


def return_equipment(checkout_id: str, condition_on_return: str, notes: str | None, user_id: str):
    """
    Processes equipment return, updates condition rating, and resets status to 'available'.
    """
    checkout = _get_client().table("equipment_checkouts").select("*").eq("id", checkout_id).single().execute().data
    if checkout:
        now_iso = datetime.now(timezone.utc).isoformat()
        # Mark checkout record as returned
        _get_client().table("equipment_checkouts").update({
            "returned_at": now_iso,
            "condition_on_return": condition_on_return,
            "notes": (checkout.get("notes") or "") + (f"\nReturn Note: {notes}" if notes else "")
        }).eq("id", checkout_id).execute()
        
        # Reset equipment status to available and remove borrower assignment
        _get_client().table("equipment").update({
            "status": "available",
            "condition": condition_on_return,
            "assigned_to": None
        }).eq("id", checkout["equipment_id"]).execute()
        
        log_action(user_id, "equipment_returned", "equipment_checkout", checkout_id, new_values={"returned_at": now_iso, "condition": condition_on_return})
