"""
===============================================================================
KAIZEN / MISSION AVINYA - Attendance & Kiosk Terminal Database Services
===============================================================================
Module Purpose:
  Provides check-in / check-out attendance services, active check-in state tracking across
  midnight boundaries, 12h IST time formatting, and automated UTC-to-IST migration logic.
===============================================================================
"""

# Import Python standard datetime & timezone utilities
from datetime import datetime, timezone, timedelta
import json
import ast

# Import base DB client and logging services
from .base import _get_client, log_action

# Define Indian Standard Time (IST = UTC + 5 hours 30 minutes)
IST = timezone(timedelta(hours=5, minutes=30))


def get_attendance(limit: int = 100):
    """
    Fetches recent attendance records ordered by event date descending.
    """
    try:
        # Query attendance table ordering newest event dates first
        query = _get_client().table("attendance").select("*").order("event_date", desc=True).limit(limit)
        res = query.execute()
        # Return data list or safe empty list fallback
        return res.data if (res and res.data is not None) else []
    except Exception as e:
        print(f"Error in get_attendance: {e}")
        return []


def get_attendance_for_member(user_id: str):
    """
    Fetches all attendance records logged for a specific member ID.
    """
    try:
        # Query attendance table filtering by user_id
        query = _get_client().table("attendance").select("*").eq("user_id", user_id).order("event_date", desc=True)
        res = query.execute()
        return res.data if (res and res.data is not None) else []
    except Exception as e:
        print(f"Error in get_attendance_for_member: {e}")
        return []


def get_active_checkin(user_id: str, event_date: str = None):
    """
    Searches for an open check-in record for a user (status='present' with an 'in' time but NO 'out' time).
    Searches across dates to handle overnight/cross-date sessions seamlessly.
    """
    try:
        # Query present attendance entries for user_id ordered descending
        query = _get_client().table("attendance").select("*").eq("user_id", user_id).eq("status", "present").order("event_date", desc=True)
        res = query.execute()
        rows = res.data if (res and res.data is not None) else []
        
        # Iterate over records to inspect notes JSON payload
        for r in rows:
            notes = {}
            if r.get("notes"):
                if isinstance(r["notes"], dict):
                    notes = r["notes"]
                else:
                    try:
                        # Attempt standard JSON decoding
                        notes = json.loads(r["notes"])
                    except (json.JSONDecodeError, TypeError):
                        try:
                            # Fallback AST literal eval for single-quoted Python dict strings
                            notes = ast.literal_eval(r["notes"])
                        except Exception:
                            notes = {}
                            
            # Check if record has an 'in' time and has NOT been checked 'out' yet
            if isinstance(notes, dict) and "in" in notes and "out" not in notes:
                return r
    except Exception as e:
        print(f"Error in get_active_checkin: {e}")
    return None


def add_attendance(user_id: str, event_name: str, event_date: str, status: str, notes: str | None,
                   recorder_id: str):
    """
    Adds a new attendance entry for a member.
    """
    # Calculate current Indian Standard Time (IST) timestamp
    now = datetime.now(IST).strftime("%H:%M:%S")

    # Format notes into valid JSON containing 'in' time
    formatted_notes = notes
    if not notes:
        formatted_notes = json.dumps({"in": now})
    elif isinstance(notes, str) and not (notes.startswith("{") and notes.endswith("}")):
        formatted_notes = json.dumps({"in": now, "info": notes})

    # Build dictionary payload matching attendance table schema
    data = {"user_id": user_id, "event_name": event_name, "event_date": event_date, "status": status, "notes": formatted_notes}
    
    # Execute database insertion
    exec_res = _get_client().table("attendance").insert(data).execute()
    res = (exec_res.data[0] if (exec_res and exec_res.data) else data)
    rec_id = res.get("id", "N/A") if isinstance(res, dict) else "N/A"
    
    # Log action to audit history
    try:
        log_action(recorder_id, "attendance_added", "attendance", rec_id, new_values=data)
    except Exception:
        pass
    return res


def delete_attendance(attendance_id: str, user_id: str):
    """
    Deletes an attendance record by its UUID identifier.
    """
    _get_client().table("attendance").delete().eq("id", attendance_id).execute()
    log_action(user_id, "attendance_deleted", "attendance", attendance_id)


def update_attendance(attendance_id: str, event_name: str, event_date: str, status: str, notes: str | None, user_id: str):
    """
    Updates details of an existing attendance record.
    """
    old_res = _get_client().table("attendance").select("*").eq("id", attendance_id).execute()
    old = old_res.data[0] if (old_res and old_res.data) else {}
    data = {"event_name": event_name, "event_date": event_date, "status": status, "notes": notes}
    _get_client().table("attendance").update(data).eq("id", attendance_id).execute()
    try:
        log_action(user_id, "attendance_updated", "attendance", attendance_id, old_values=old, new_values=data)
    except Exception:
        pass


def quick_toggle_attendance(user_id: str, event_date: str, recorder_id: str):
    """
    Toggles a member's kiosk attendance status:
      - If member is currently checked in: marks 'out' time (Check Out).
      - If member is not checked in: creates new 'present' entry with 'in' time (Check In).
    """
    try:
        # Check if member has an active open check-in session
        active = get_active_checkin(user_id, event_date)
        now = datetime.now(IST).strftime("%H:%M:%S")
        
        if active:
            # === CHECK OUT FLOW ===
            existing_notes = {}
            if active.get("notes"):
                try:
                    existing_notes = json.loads(active["notes"])
                except (json.JSONDecodeError, TypeError):
                    existing_notes = {}
            # Update notes dictionary with check-out timestamp
            existing_notes["out"] = now
            _get_client().table("attendance").update({
                "notes": json.dumps(existing_notes)
            }).eq("id", active["id"]).execute()
            
            try:
                log_action(recorder_id, "attendance_checked_out", "attendance", active["id"], new_values={"out_time": now})
            except Exception:
                pass
            return {"action": "checked_out", "record": active}
        else:
            # === CHECK IN FLOW ===
            notes = json.dumps({"in": now})
            data = {
                "user_id": user_id,
                "event_name": "Club Session",
                "event_date": event_date,
                "status": "present",
                "notes": notes
            }
            exec_res = _get_client().table("attendance").insert(data).execute()
            res = (exec_res.data[0] if (exec_res and exec_res.data) else data)
            rec_id = res.get("id", "N/A") if isinstance(res, dict) else "N/A"
            
            try:
                log_action(recorder_id, "attendance_checked_in", "attendance", rec_id, new_values=data)
            except Exception:
                pass
            return {"action": "checked_in", "record": res}
    except Exception as e:
        print(f"Error in quick_toggle_attendance: {e}")
        return {"action": "error", "message": str(e)}


def fix_all_attendance_utc_to_ist(user_id: str):
    """
    Utility function to migrate historical attendance timestamps created in UTC by adding +5h 30m to IST.
    """
    try:
        rows = _get_client().table("attendance").select("*").execute().data or []
        updated_count = 0
        for r in rows:
            notes_str = r.get("notes")
            if not notes_str:
                continue
            try:
                notes = json.loads(notes_str)
                modified = False
                for key in ["in", "out"]:
                    if key in notes and notes[key] and isinstance(notes[key], str):
                        val = notes[key]
                        if "AM" in val or "PM" in val or "IST" in val:
                            continue
                        parts = val.split(":")
                        if len(parts) >= 2:
                            hh = int(parts[0])
                            mm = int(parts[1])
                            ss = int(parts[2]) if len(parts) > 2 else 0
                            
                            # Shift +5 hours 30 minutes
                            mm_new = mm + 30
                            hh_add = 0
                            if mm_new >= 60:
                                mm_new -= 60
                                hh_add = 1
                            hh_new = (hh + 5 + hh_add) % 24
                            
                            notes[key] = f"{hh_new:02d}:{mm_new:02d}:{ss:02d}"
                            modified = True
                
                if modified:
                    _get_client().table("attendance").update({
                        "notes": json.dumps(notes)
                    }).eq("id", r["id"]).execute()
                    updated_count += 1
            except Exception as e:
                print(f"Error parsing attendance notes for {r.get('id')}: {e}")
                
        log_action(user_id, "fix_all_attendance_ist", "attendance", "all", new_values={"updated_count": updated_count})
        return updated_count
    except Exception as e:
        print(f"Error in fix_all_attendance_utc_to_ist: {e}")
        return 0
