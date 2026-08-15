"""
===============================================================================
KAIZEN / MISSION AVINYA - Flight Telemetry & Battery Fleet Database Services
===============================================================================
Module Purpose:
  Provides database CRUD services for drone flight logs, flight durations, battery pack cycles,
  and battery health tracking with line-by-line comments.
===============================================================================
"""

# Import base DB client and audit logging
from .base import _get_client, log_action


# =============================================================================
# FLIGHT LOGBOOK SERVICES
# =============================================================================

def get_all_flight_logs():
    """
    Fetches all flight logs ordered by flight date descending.
    """
    try:
        query = _get_client().table("flight_logs").select("*").order("flight_date", desc=True)
        res = query.execute()
        return res.data if (res and res.data is not None) else []
    except Exception as e:
        print(f"Error fetching flight logs: {e}")
        return []


def create_flight_log(pilot_id: str, equipment_id: str | None, battery_id: str | None,
                      flight_date: str, duration_minutes: int, location: str | None,
                      purpose: str | None, notes: str | None, user_id: str):
    """
    Logs a new drone flight session and automatically increments charge cycles on the battery pack.
    """
    # Construct flight log data dictionary payload
    data = {
        "pilot_id": pilot_id,
        "equipment_id": equipment_id,
        "battery_id": battery_id,
        "flight_date": flight_date,
        "duration_minutes": duration_minutes,
        "location": location,
        "purpose": purpose,
        "notes": notes
    }
    # Insert flight log into database
    res = _get_client().table("flight_logs").insert(data).execute().data[0]
    # Log action to audit log
    log_action(user_id, "flight_logged", "flight_log", res["id"], new_values=data)
    
    # Auto-increment battery charge cycles if a battery pack was linked
    if battery_id:
        try:
            increment_battery_cycle(battery_id, user_id)
        except Exception as e:
            print(f"Failed to increment battery cycle: {e}")
            
    return res


def delete_flight_log(log_id: str, user_id: str):
    """
    Deletes a flight log entry by its UUID identifier.
    """
    old = _get_client().table("flight_logs").select("*").eq("id", log_id).single().execute().data
    _get_client().table("flight_logs").delete().eq("id", log_id).execute()
    log_action(user_id, "flight_deleted", "flight_log", log_id, old_values=old)


# =============================================================================
# BATTERY FLEET SERVICES
# =============================================================================

def get_all_battery_packs():
    """
    Fetches all registered LiPo battery packs ordered by battery pack name.
    """
    try:
        query = _get_client().table("battery_packs").select("*").order("name")
        res = query.execute()
        return res.data if (res and res.data is not None) else []
    except Exception as e:
        print(f"Error fetching battery packs: {e}")
        return []


def create_battery_pack(name: str, cell_count: str, capacity_mah: int, status: str, notes: str | None, user_id: str):
    """
    Registers a new LiPo battery pack into the fleet inventory.
    """
    data = {
        "name": name,
        "cell_count": cell_count,
        "capacity_mah": capacity_mah,
        "charge_cycles": 0,  # Initialize charge cycle count to 0
        "status": status,
        "notes": notes
    }
    res = _get_client().table("battery_packs").insert(data).execute().data[0]
    log_action(user_id, "battery_created", "battery_pack", res["id"], new_values=data)
    return res


def increment_battery_cycle(battery_id: str, user_id: str):
    """
    Increments the recorded charge cycles for a LiPo battery pack after a completed flight.
    """
    b = _get_client().table("battery_packs").select("*").eq("id", battery_id).single().execute().data
    if b:
        new_cycles = (b.get("charge_cycles") or 0) + 1
        _get_client().table("battery_packs").update({"charge_cycles": new_cycles}).eq("id", battery_id).execute()
        log_action(user_id, "battery_cycle_incremented", "battery_pack", battery_id, new_values={"charge_cycles": new_cycles})


def update_battery_status(battery_id: str, status: str, user_id: str):
    """
    Updates the operational health status of a battery pack (e.g. 'ready', 'charging', 'retired', 'damaged').
    """
    _get_client().table("battery_packs").update({"status": status}).eq("id", battery_id).execute()
    log_action(user_id, "battery_status_updated", "battery_pack", battery_id, new_values={"status": status})
