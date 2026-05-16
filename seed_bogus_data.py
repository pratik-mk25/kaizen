import os
from datetime import datetime
from database import supabase_admin
import crud

def seed():
    # 1. Get the VIHANG org
    res = supabase_admin.table('organizations').select('id').eq('name', 'VIHANG').execute()
    if not res.data:
        print("VIHANG org not found")
        return
    org_id = res.data[0]['id']

    # 2. Get users in VIHANG
    users_res = supabase_admin.table('profiles').select('id, username').eq('organization_id', org_id).execute()
    users = users_res.data
    if not users:
        print("No users found")
        return

    # 3. Get or create a Mission
    mission_res = supabase_admin.table('missions').select('id').eq('organization_id', org_id).execute()
    if mission_res.data:
        mission_id = mission_res.data[0]['id']
    else:
        print("Creating fake mission")
        m = crud.create_mission("Aero-Dynamics Revamp", "Testing", users[0]['id'], org_id)
        mission_id = m['id']

    # 4. Get or create Projects
    project_res = supabase_admin.table('projects').select('id').eq('organization_id', org_id).execute()
    if project_res.data:
        p1_id = project_res.data[0]['id']
        p2_id = project_res.data[-1]['id'] # use same if only 1
    else:
        print("Creating fake projects")
        p1 = crud.create_project("Propeller Stress Test", "Testing", mission_id, None, users[0]['id'], org_id)
        p2 = crud.create_project("Club Project Sync", "Testing", mission_id, None, users[0]['id'], org_id)
        p1_id = p1['id']
        p2_id = p2['id']

    # 5. Create Fake Completed Tasks for different users
    print("Creating bogus completed tasks...")
    import random
    
    tasks_to_create = [
        ("Calibrate Sensors", p1_id, users[0]['id']),
        ("Balance Props", p1_id, users[1 % len(users)]['id']),
        ("Flash Firmware", p2_id, users[2 % len(users)]['id']),
        ("Test Telemetry", p2_id, users[0]['id']),
        ("Review Logs", p1_id, users[1 % len(users)]['id']),
        ("Optimize Battery", p2_id, users[0]['id'])
    ]

    for title, pid, uid in tasks_to_create:
        # Create task
        task = crud.create_task(title, "Bogus data", pid, uid, "high", None, org_id)
        # Assign to user
        crud.assign_users_to_task(task['id'], [uid], uid)
        # Mark as done (this updates 'updated_at' to now, which makes it show in this month's analytics)
        crud.update_task_status(task['id'], "done", uid, org_id)

    print("Bogus data injected successfully!")

if __name__ == "__main__":
    seed()
