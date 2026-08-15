"""
===============================================================================
KAIZEN / MISSION AVINYA - Users, Profiles, Skills & Certifications Services
===============================================================================
Module Purpose:
  Provides administrative user management, complete cascade profile deletion,
  skills catalog management, and certification verifications with line-by-line comments.
===============================================================================
"""

# Import Python standard datetime utilities
from datetime import datetime, timezone

# Import base client, audit logging, and Supabase admin client
from .base import _get_client, log_action
from database import supabase, supabase_admin


# =============================================================================
# USER & PROFILE MANAGEMENT
# =============================================================================

def get_all_users():
    """
    Fetches basic role information for all system users.
    """
    # Select id and role columns from profiles table
    query = _get_client().table("profiles").select("id, role")
    res = query.execute()
    return res.data if (res and res.data is not None) else []


def get_users_by_role(role: str):
    """
    Fetches user profiles matching a specific clearance role (e.g. 'admin', 'lead', 'member').
    """
    # Query profiles filtering by target role
    query = _get_client().table("profiles").select("id, role, username, display_name").eq("role", role)
    res = query.execute()
    return res.data if (res and res.data is not None) else []


def get_all_users_detailed():
    """
    Fetches complete profile details for all registered members ordered by registration date.
    """
    # Query all profile fields ordered by created_at ascending
    query = _get_client().table("profiles").select("id, username, display_name, role, email, created_at").order("created_at")
    res = query.execute()
    return res.data if (res and res.data is not None) else []


def create_user_by_admin(email: str, password: str, display_name: str, role: str, admin_id: str):
    """
    Creates a new user in Supabase Auth and inserts their corresponding profile entry.
    """
    try:
        # Create user inside Supabase Auth system via service role admin API
        user_resp = supabase_admin.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True
        })
        new_user = user_resp.user
    except Exception as e:
        raise Exception(f"Failed to create auth user: {e}")

    # Prepare user profile data payload
    profile_data = {
        "id": new_user.id,
        "email": email,
        "display_name": display_name,
        "username": email.split("@")[0],
        "role": role,
    }
    # Insert new user profile into public profiles database table
    _get_client().table("profiles").insert(profile_data).execute()
    # Log user creation action to audit logs
    log_action(admin_id, "user_created", "user", new_user.id, new_values=profile_data)
    return new_user


def delete_user_completely(user_id: str, admin_id: str):
    """
    Performs a safe cascade deletion of a user profile by clearing all foreign key child
    table references prior to removing the user profile and auth account.
    """
    client = _get_client()

    # 1. Clean up child table references to prevent PostgreSQL 23503 foreign key constraint errors
    tables_to_delete_by_user = [
        "attendance", "task_assignees", "comments", "member_skills",
        "member_certifications", "event_attendees", "audit_logs"
    ]
    for t in tables_to_delete_by_user:
        try:
            client.table(t).delete().eq("user_id", user_id).execute()
        except Exception as e:
            print(f"Cleanup error in {t} for {user_id}: {e}")

    # Clear equipment checkout records for borrower
    try:
        client.table("equipment_checkouts").delete().eq("borrower_id", user_id).execute()
    except Exception as e:
        print(f"Cleanup error in equipment_checkouts for {user_id}: {e}")

    # Clear flight logs where user was pilot
    try:
        client.table("flight_logs").delete().eq("pilot_id", user_id).execute()
    except Exception as e:
        print(f"Cleanup error in flight_logs for {user_id}: {e}")

    # Nullify project lead references
    try:
        client.table("projects").update({"lead_id": None}).eq("lead_id", user_id).execute()
    except Exception as e:
        print(f"Cleanup error in projects for {user_id}: {e}")

    # Nullify equipment assignment references
    try:
        client.table("equipment").update({"assigned_to": None}).eq("assigned_to", user_id).execute()
    except Exception as e:
        print(f"Cleanup error in equipment for {user_id}: {e}")

    # Nullify event creator references
    try:
        client.table("events").update({"created_by": None}).eq("created_by", user_id).execute()
    except Exception as e:
        print(f"Cleanup error in events for {user_id}: {e}")

    # 2. Delete public profile row from profiles table
    client.table("profiles").delete().eq("id", user_id).execute()

    # 3. Delete user account from Supabase Auth service
    try:
        supabase_admin.auth.admin.delete_user(user_id)
    except Exception as e:
        print(f"Cleanup error in supabase_admin delete_user: {e}")

    # Log user deletion action in audit history
    log_action(admin_id, "user_deleted", "user", user_id)


# =============================================================================
# SKILLS MANAGEMENT
# =============================================================================

def get_all_skills():
    """
    Fetches all available skill catalog entries ordered by name.
    """
    query = _get_client().table("skills").select("*").order("name")
    res = query.execute()
    return res.data if (res and res.data is not None) else []


def create_skill(name: str, category: str, user_id: str):
    """
    Creates a new skill category entry (e.g., 'Soldering', 'PX4 Firmware', 'CAD Design').
    """
    data = {"name": name, "category": category}
    res = _get_client().table("skills").insert(data).execute().data[0]
    log_action(user_id, "skill_created", "skill", res["id"], new_values=data)
    return res


def delete_skill(skill_id: str, user_id: str):
    """
    Deletes a skill entry from the global catalog.
    """
    _get_client().table("skills").delete().eq("id", skill_id).execute()
    log_action(user_id, "skill_deleted", "skill", skill_id)


def get_member_skills(user_id: str):
    """
    Fetches all technical skills assigned to a specific member with joined skill details.
    """
    rows = _get_client().table("member_skills").select("*, skills(name, category)").eq("user_id", user_id).execute().data
    return rows or []


def set_member_skill(user_id: str, skill_id: str, proficiency_level: str):
    """
    Upserts a member's skill proficiency level ('beginner', 'intermediate', 'advanced', 'expert').
    """
    data = {
        "user_id": user_id,
        "skill_id": skill_id,
        "proficiency_level": proficiency_level,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    _get_client().table("member_skills").upsert(data, on_conflict="user_id,skill_id").execute()


def remove_member_skill(user_id: str, skill_id: str):
    """
    Removes a technical skill assignment from a member.
    """
    _get_client().table("member_skills").delete().eq("user_id", user_id).eq("skill_id", skill_id).execute()


# =============================================================================
# CERTIFICATIONS MANAGEMENT
# =============================================================================

def get_all_certifications():
    """
    Fetches all formal certification definitions (e.g. DGCA Pilot License, Part 107).
    """
    query = _get_client().table("certifications").select("*").order("name")
    res = query.execute()
    return res.data if (res and res.data is not None) else []


def create_certification(name: str, issuing_body: str | None, user_id: str):
    """
    Creates a new certification entry in the global catalog.
    """
    data = {"name": name, "issuing_body": issuing_body}
    res = _get_client().table("certifications").insert(data).execute().data[0]
    log_action(user_id, "certification_created", "certification", res["id"], new_values=data)
    return res


def delete_certification(cert_id: str, user_id: str):
    """
    Deletes a certification definition from catalog.
    """
    _get_client().table("certifications").delete().eq("id", cert_id).execute()
    log_action(user_id, "certification_deleted", "certification", cert_id)


def get_member_certifications(user_id: str):
    """
    Fetches all certifications obtained by a specific member.
    """
    rows = _get_client().table("member_certifications").select("*, certifications(name, issuing_body)").eq("user_id", user_id).order("date_obtained", desc=True).execute().data
    return rows or []


def add_member_certification(member_id: str, certification_id: str, date_obtained: str, expiry_date: str | None,
                              admin_id: str):
    """
    Records a certification earned by a member.
    """
    data = {
        "user_id": member_id,
        "certification_id": certification_id,
        "date_obtained": date_obtained,
        "expiry_date": expiry_date,
        "verification_status": "pending"
    }
    res = _get_client().table("member_certifications").insert(data).execute().data[0]
    log_action(admin_id, "member_cert_added", "member_certification", res["id"], new_values=data)
    return res


def verify_member_certification(cert_id: str, status: str):
    """
    Updates the verification status of a member certification ('verified', 'pending', 'expired').
    """
    query = _get_client().table("member_certifications").update({"verification_status": status}).eq("id", cert_id)
    query.execute()


def delete_member_certification(cert_id: str, user_id: str):
    """
    Deletes a member certification record.
    """
    _get_client().table("member_certifications").delete().eq("id", cert_id).execute()
    log_action(user_id, "member_cert_deleted", "member_certification", cert_id)
