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
    try:
        query = _get_client().table("profiles").select("id, username, display_name, role, email, created_at").order("created_at")
        res = query.execute()
        return res.data if (res and res.data is not None) else []
    except Exception as e:
        print(f"Error in get_all_users_detailed: {e}")
        return []


import re
import random

def derive_display_name_from_email(email: str) -> str:
    """
    Turns sanskar.helunde@vihang.com into 'Sanskar Helunde'
    """
    if not email:
        return "Member"
    local_part = email.split("@")[0]
    parts = re.split(r"[._\-+]+", local_part)
    clean_parts = [p.capitalize() for p in parts if p]
    return " ".join(clean_parts) if clean_parts else local_part.capitalize()

def generate_temporary_password() -> str:
    """
    Generates a memorable and secure temporary password e.g. 'Kaizen-7492' or 'Avinya-8314'
    """
    prefix = random.choice(["Kaizen", "Avinya", "Pilot", "Drone", "Falcon", "Apex", "Vortex", "Horizon"])
    num = random.randint(1000, 9999)
    return f"{prefix}-{num}"

def create_user_by_admin(email: str, password: str, display_name: str, role: str, admin_id: str):
    """
    Creates a new user in Supabase Auth and safely syncs their profile.
    Self-healing:
      - If user already exists in Supabase Auth, adopts the account, updates password and updates profile.
      - Uses upsert/update on public.profiles to NEVER throw duplicate key 23505 constraints from DB triggers.
      - Auto-formats display_name and username if omitted.
      - Clears the in-memory username cache.
    """
    client = _get_client()
    clean_email = email.strip().lower()
    clean_name = (display_name or "").strip() or derive_display_name_from_email(clean_email)
    clean_username = clean_email.split("@")[0].lower().replace("+", "_")
    target_role = role if role in ("member", "lead", "admin") else "member"

    user_id = None
    is_adopted = False

    # 1. Try creating user in Supabase Auth
    try:
        user_resp = supabase_admin.auth.admin.create_user({
            "email": clean_email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {"display_name": clean_name}
        })
        if user_resp and getattr(user_resp, "user", None):
            user_id = user_resp.user.id
    except Exception as e:
        err_str = str(e).lower()
        # If user already registered or exists in Supabase Auth, self-heal and adopt
        if any(term in err_str for term in ("already registered", "already in use", "already been registered", "exists", "duplicate")):
            is_adopted = True
            try:
                # First check profiles table
                prof = client.table("profiles").select("id").eq("email", clean_email).execute()
                if prof and prof.data:
                    user_id = prof.data[0]["id"]
                else:
                    # Search via admin auth listing
                    users_list = supabase_admin.auth.admin.list_users()
                    user_items = getattr(users_list, "users", users_list) if users_list else []
                    for u in user_items:
                        u_email = getattr(u, "email", None) or (u.get("email") if isinstance(u, dict) else None)
                        if u_email and u_email.lower() == clean_email:
                            user_id = getattr(u, "id", None) or (u.get("id") if isinstance(u, dict) else None)
                            break
            except Exception as find_err:
                print(f"Error locating existing auth user {clean_email}: {find_err}")
                
            # Update password in Auth if user found
            if user_id and password:
                try:
                    supabase_admin.auth.admin.update_user_by_id(user_id, {
                        "password": password,
                        "user_metadata": {"display_name": clean_name}
                    })
                except Exception as update_err:
                    print(f"Error updating existing user password: {update_err}")
        else:
            raise Exception(f"Failed to create user in Auth: {str(e)}")

    if not user_id:
        raise Exception(f"Could not provision or locate account for {clean_email}. If they exist in auth, please check credentials.")

    # 2. Safely sync profile in public.profiles (guaranteed no 23505 duplicate key)
    profile_data = {
        "id": user_id,
        "email": clean_email,
        "display_name": clean_name,
        "username": clean_username,
        "role": target_role,
    }

    try:
        existing = client.table("profiles").select("id").eq("id", user_id).execute()
        if existing and existing.data:
            client.table("profiles").update(profile_data).eq("id", user_id).execute()
        else:
            client.table("profiles").upsert(profile_data, on_conflict="id").execute()
    except Exception:
        # Fallback to direct update
        client.table("profiles").update(profile_data).eq("id", user_id).execute()

    # 3. Invalidate username map cache
    try:
        import templates_utils
        templates_utils._USERNAME_MAP_CACHE = None
        templates_utils._USERNAME_MAP_CACHE_EXPIRY = 0
    except Exception:
        pass

    # 4. Log action
    act = "user_adopted" if is_adopted else "user_created"
    log_action(admin_id, act, "user", user_id, new_values=profile_data)

    profile_data["adopted"] = is_adopted
    return profile_data

def reset_user_password_by_admin(user_id: str, new_password: str, admin_id: str):
    """
    Updates a user's password directly via Supabase Auth admin API without requiring
    dashboard access or email reset links.
    """
    if not new_password or len(new_password) < 6:
        raise ValueError("Password must be at least 6 characters")
    try:
        supabase_admin.auth.admin.update_user_by_id(user_id, {"password": new_password})
        log_action(admin_id, "password_reset", "user", user_id)
        return True
    except Exception as e:
        raise Exception(f"Failed to update password: {str(e)}")

def create_users_bulk(users_data: list, admin_id: str) -> dict:
    """
    Bulk provisions multiple users in a single operation.
    """
    results = {
        "success": [],
        "failed": [],
        "total": len(users_data)
    }
    for item in users_data:
        email = (item.get("email") or "").strip().lower()
        if not email or "@" not in email:
            results["failed"].append({"email": email or "Unknown", "error": "Invalid email address"})
            continue
        pwd = item.get("password") or generate_temporary_password()
        name = item.get("display_name") or derive_display_name_from_email(email)
        role = item.get("role") or "member"
        try:
            res = create_user_by_admin(email, pwd, name, role, admin_id)
            results["success"].append({
                "id": res["id"],
                "email": email,
                "display_name": name,
                "role": role,
                "password": pwd,
                "adopted": res.get("adopted", False)
            })
        except Exception as e:
            results["failed"].append({"email": email, "error": str(e)})

    return results


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

    # Invalidate username map cache
    try:
        import templates_utils
        templates_utils._USERNAME_MAP_CACHE = None
        templates_utils._USERNAME_MAP_CACHE_EXPIRY = 0
    except Exception:
        pass


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
