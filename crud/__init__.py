"""
===============================================================================
KAIZEN / MISSION AVINYA - Central Database Package (crud)
===============================================================================
Module Purpose:
  Exposes all domain database services through a unified package namespace,
  allowing seamless `import crud` imports across all FastAPI router modules.
===============================================================================
"""

# Base & Audit Services
from .base import (
    _get_client,
    log_action,
    get_audit_logs,
    get_audit_log,
    revert_action,
    get_organization,
    update_organization_settings,
    get_kiosk_secret,
    set_kiosk_secret,
    get_key_holder,
    set_key_holder,
)

# Missions, Projects & Kanban Tasks
from .missions_tasks import (
    get_all_missions,
    get_mission,
    create_mission,
    update_mission,
    delete_mission,
    get_projects_for_mission,
    get_project,
    create_project,
    update_project,
    delete_project,
    get_tasks_for_project,
    get_task,
    create_task,
    update_task_status,
    update_task,
    delete_task,
    get_assignees,
    assign_users_to_task,
    get_tasks_for_user,
    get_comments_for_task,
    add_comment,
    get_attachments,
    add_attachment,
    delete_attachment,
    get_monthly_progress,
)

# Users, Profiles, Skills & Certifications
from .users import (
    get_all_users,
    get_users_by_role,
    get_all_users_detailed,
    create_user_by_admin,
    delete_user_completely,
    get_all_skills,
    create_skill,
    delete_skill,
    get_member_skills,
    set_member_skill,
    remove_member_skill,
    get_all_certifications,
    create_certification,
    delete_certification,
    get_member_certifications,
    add_member_certification,
    verify_member_certification,
    delete_member_certification,
)

# Attendance & Kiosk Terminal
from .attendance import (
    get_attendance,
    get_attendance_for_member,
    get_active_checkin,
    add_attendance,
    delete_attendance,
    update_attendance,
    quick_toggle_attendance,
    fix_all_attendance_utc_to_ist,
)

# Equipment, Inventory & Checkouts
from .equipment import (
    get_all_equipment,
    get_equipment,
    create_equipment,
    update_equipment,
    delete_equipment,
    get_maintenance_logs,
    add_maintenance_log,
    delete_maintenance_log,
    get_all_inventory,
    get_inventory_item,
    create_inventory_item,
    update_inventory_item,
    delete_inventory_item,
    log_inventory_transaction,
    get_inventory_transactions,
    get_active_checkouts,
    get_checkouts_for_equipment,
    checkout_equipment,
    return_equipment,
)

# Flight Telemetry & LiPo Battery Fleet
from .flights import (
    get_all_flight_logs,
    create_flight_log,
    delete_flight_log,
    get_all_battery_packs,
    create_battery_pack,
    increment_battery_cycle,
    update_battery_status,
)

# Events, Workshops & Probation Members
from .events import (
    get_all_events,
    get_event,
    create_event,
    delete_event,
    get_event_attendees,
    rsvp_event,
    get_probation_members,
)

# Budget, Transactions & Dues
from .budget import (
    get_budget_categories,
    create_budget_category,
    update_budget_category,
    delete_budget_category,
    get_transactions,
    create_transaction,
    update_transaction,
    delete_transaction,
    get_dues,
    create_dues_entry,
    mark_dues_paid,
    delete_dues,
)

# Documentation & Knowledge Base
from .documents import (
    get_all_documents,
    get_document,
    create_document,
    update_document,
    delete_document,
)

# Leaderboard & Gamification
from .leaderboard import (
    get_leaderboard_data,
)
