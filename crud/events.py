"""
===============================================================================
KAIZEN / MISSION AVINYA - Events, Workshops & Probation Member Tracker Services
===============================================================================
Module Purpose:
  Provides database CRUD operations for club workshops, competitions, event RSVPs,
  and probation member tracking with line-by-line comments.
===============================================================================
"""

# Import base DB client, audit logging, and user queries
from .base import _get_client, log_action
from .users import get_all_users_detailed


# =============================================================================
# EVENTS & WORKSHOPS SERVICES
# =============================================================================

def get_all_events():
    """
    Fetches all club events ordered by event date descending.
    """
    try:
        query = _get_client().table("events").select("*").order("event_date", desc=True)
        res = query.execute()
        return res.data if (res and res.data is not None) else []
    except Exception as e:
        print(f"Error fetching events: {e}")
        return []


def get_event(event_id: str):
    """
    Fetches details of a single event by its UUID identifier.
    """
    try:
        query = _get_client().table("events").select("*").eq("id", event_id).single()
        return query.execute().data
    except Exception as e:
        print(f"Error fetching event {event_id}: {e}")
        return None


def create_event(title: str, description: str | None, event_type: str, event_date: str, location: str | None, user_id: str):
    """
    Creates a new workshop, flight session, or competition event.
    """
    data = {
        "title": title,
        "description": description,
        "event_type": event_type,
        "event_date": event_date,
        "location": location,
        "created_by": user_id
    }
    res = _get_client().table("events").insert(data).execute().data[0]
    log_action(user_id, "event_created", "event", res["id"], new_values=data)
    return res


def delete_event(event_id: str, user_id: str):
    """
    Deletes an event record by its UUID identifier.
    """
    old = get_event(event_id)
    _get_client().table("events").delete().eq("id", event_id).execute()
    log_action(user_id, "event_deleted", "event", event_id, old_values=old)


def get_event_attendees(event_id: str):
    """
    Fetches all attendee RSVP registrations for an event.
    """
    try:
        query = _get_client().table("event_attendees").select("*").eq("event_id", event_id)
        res = query.execute()
        return res.data if (res and res.data is not None) else []
    except Exception as e:
        print(f"Error fetching attendees for event {event_id}: {e}")
        return []


def rsvp_event(event_id: str, user_id: str, status: str = "registered", notes: str | None = None):
    """
    Upserts an RSVP status for a member on an event ('registered', 'attended', 'cancelled').
    """
    existing = _get_client().table("event_attendees").select("*").eq("event_id", event_id).eq("user_id", user_id).execute().data
    if existing:
        _get_client().table("event_attendees").update({"status": status, "notes": notes}).eq("id", existing[0]["id"]).execute()
    else:
        _get_client().table("event_attendees").insert({
            "event_id": event_id,
            "user_id": user_id,
            "status": status,
            "notes": notes
        }).execute()
    log_action(user_id, "event_rsvp", "event_attendee", event_id, new_values={"status": status})


def get_probation_members():
    """
    Fetches member profiles currently under probationary or new-join status.
    """
    try:
        profiles = get_all_users_detailed()
        return [p for p in profiles if p.get("role") in ["probation", "probationary_member", "member", "new_member"]]
    except Exception as e:
        print(f"Error fetching probation members: {e}")
        return []
