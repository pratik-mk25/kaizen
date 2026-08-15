"""
===============================================================================
KAIZEN / MISSION AVINYA - Core Database Base Operations
===============================================================================
Module Purpose:
  Provides the primary database client accessor and centralized audit logging
  services for recording all system activity.
===============================================================================
"""

# Import Python standard datetime utilities for timestamp generation
from datetime import datetime, timezone, timedelta

# Import standard JSON module for serializing audit log payload data
import json

# Import initialized Supabase client instances (anon and admin service-role)
from database import supabase, supabase_admin


def _get_client():
    """
    Returns the admin service-role Supabase client.
    
    Why supabase_admin is used:
      Using the service-role client bypasses restrictive Row-Level Security (RLS)
      policies when performing administrative operations (such as Kiosk check-ins,
      user management, and global audit logging).
    """
    # Return the service-role admin client
    return supabase_admin


def log_action(user_id: str, action: str, entity_type: str, entity_id: str,
               old_values: dict | None = None, new_values: dict | None = None):
    """
    Logs an action to the central `audit_logs` table for tracking & undo capability.
    
    Parameters:
      user_id (str): UUID of the user performing the action.
      action (str): Action descriptor (e.g., 'task_created', 'attendance_added').
      entity_type (str): Type of entity affected (e.g., 'task', 'attendance', 'user').
      entity_id (str): UUID of the target entity.
      old_values (dict|None): Dictionary of values before change (if update/delete).
      new_values (dict|None): Dictionary of new values applied (if create/update).
    """
    # Retrieve the database client
    client = _get_client()
    
    try:
        # Construct the payload dictionary matching database schema
        data = {
            "user_id": user_id,  # User who triggered the action
            "action": action,  # Verb describing the action performed
            "entity_type": entity_type,  # Entity category name
            "entity_id": str(entity_id),  # Target record unique identifier
            "old_values": json.dumps(old_values) if old_values else None,  # JSON string of previous state
            "new_values": json.dumps(new_values) if new_values else None,  # JSON string of new state
        }

        # Insert the record into the audit_logs database table
        client.table("audit_logs").insert(data).execute()
    except Exception as e:
        # Catch and print any audit log insertion error without crashing caller operation
        print(f"DEBUG: Failed to log action {action}: {e}")


def get_audit_logs(limit=50, user_id=None, entity_type=None):
    """
    Fetches system audit logs ordered by creation timestamp descending.
    """
    # Query audit_logs table ordering newest first
    query = _get_client().table("audit_logs").select("*").order("created_at", desc=True).limit(limit)
    
    # Filter by user_id if provided
    if user_id:
        query = query.eq("user_id", user_id)
        
    # Filter by entity_type if provided
    if entity_type:
        query = query.eq("entity_type", entity_type)
        
    # Execute query and return data payload or empty list fallback
    res = query.execute()
    return res.data if (res and res.data is not None) else []


def get_audit_log(log_id: str):
    """
    Fetches a single audit log entry by its unique log ID.
    """
    # Query single log matching log_id
    return _get_client().table("audit_logs").select("*").eq("id", log_id).single().execute().data


def revert_action(log_id: str, admin_id: str):
    """
    Reverts a previous action using saved old_values from audit logs (Undo capability).
    """
    # Fetch log entry
    log = get_audit_log(log_id)
    if not log:
        return
        
    # Parse entity_type, old_values, and new_values
    entity_type = log["entity_type"]
    entity_id = log["entity_id"]
    old_values = json.loads(log["old_values"]) if log.get("old_values") else None
    
    # If old values existed for a deleted item, re-insert it
    if old_values and log["action"].endswith("_deleted"):
        table = f"{entity_type}s" if not entity_type.endswith('s') else entity_type
        _get_client().table(table).insert(old_values).execute()
    # If old values existed for an updated item, restore them
    elif old_values and log["action"].endswith("_updated"):
        table = f"{entity_type}s" if not entity_type.endswith('s') else entity_type
        _get_client().table(table).update(old_values).eq("id", entity_id).execute()
    # If item was newly created, delete it to revert
    elif log["action"].endswith("_created"):
        table = f"{entity_type}s" if not entity_type.endswith('s') else entity_type
        _get_client().table(table).delete().eq("id", entity_id).execute()
        
    # Log the revert action
    log_action(admin_id, "revert_action", "audit_log", log_id, new_values={"reverted_action": log["action"]})


def get_organization():
    """
    Fetches global organization settings record (creates default if missing).
    """
    try:
        # Query organizations table
        rows = _get_client().table("organizations").select("*").order("created_at", desc=True).limit(1).execute().data
        if rows:
            return rows[0]
        # Insert default organization if table is empty
        _get_client().table("organizations").insert({"name": "Drone Club OS", "discord_webhook_url": None}).execute()
        rows = _get_client().table("organizations").select("*").order("created_at", desc=True).limit(1).execute().data
        return rows[0] if rows else {"id": "N/A", "name": "Drone Club OS", "discord_webhook_url": None}
    except Exception as e:
        print(f"Error fetching organization: {e}")
        return {"id": "N/A", "name": "Drone Club OS", "discord_webhook_url": None}


def update_organization_settings(name: str, discord_webhook_url: str, user_id: str):
    """
    Updates organization name and Discord notification webhook URL.
    """
    org = get_organization()
    _get_client().table("organizations").update({"name": name, "discord_webhook_url": discord_webhook_url}).eq("id", org["id"]).execute()
    log_action(user_id, "organization_updated", "organization", org["id"], old_values=org, new_values={"name": name, "discord_webhook_url": discord_webhook_url})


def get_kiosk_secret():
    """
    Retrieves configured kiosk authentication secret code.
    """
    org = get_organization()
    return org.get("kiosk_secret", "")


def set_kiosk_secret(secret: str, user_id: str):
    """
    Updates kiosk authentication secret code.
    """
    org = get_organization()
    _get_client().table("organizations").update({"kiosk_secret": secret}).eq("id", org["id"]).execute()
    log_action(user_id, "kiosk_secret_updated", "organization", org["id"], new_values={"kiosk_secret": "***"})


def get_key_holder():
    """
    Retrieves current lab/office physical key holder location or member name.
    """
    org = get_organization()
    return org.get("key_holder", "HOD Cabin")


def set_key_holder(holder: str, user_id: str):
    """
    Updates lab/office physical key holder location.
    """
    org = get_organization()
    _get_client().table("organizations").update({"key_holder": holder}).eq("id", org["id"]).execute()
    log_action(user_id, "key_holder_updated", "organization", org["id"], old_values={"key_holder": org.get("key_holder")}, new_values={"key_holder": holder})
