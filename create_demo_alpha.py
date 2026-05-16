import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Path to the .env file in the same directory
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

try:
    from database import supabase, supabase_admin
    import crud
except ImportError:
    print("Error: Could not import project modules. Make sure you are in the project root.")
    sys.exit(1)

def create_demo_alpha():
    if not supabase_admin:
        print("Error: SUPABASE_SERVICE_ROLE_KEY is required to create demo data.")
        return

    email = "test@vihang.com"
    password = "12345678"
    club_name = "Alpha"
    display_name = "Alpha Administrator"

    print(f"--- Creating Demo Environment for '{club_name}' ---")

    try:
        # 1. Create or Find Organization
        print(f"Checking for organization: {club_name}...")
        org_res = supabase_admin.table("organizations").select("*").ilike("name", club_name).execute()
        if org_res.data:
            org_id = org_res.data[0]["id"]
            print(f"Organization found. ID: {org_id}")
            # Cleanup existing data for this org to ensure fresh demo
            print("Cleaning up existing demo data for 'Alpha'...")
            supabase_admin.table("tasks").delete().eq("organization_id", org_id).execute()
            supabase_admin.table("projects").delete().eq("organization_id", org_id).execute()
            supabase_admin.table("missions").delete().eq("organization_id", org_id).execute()
        else:
            print(f"Creating organization: {club_name}...")
            org_res = supabase_admin.table("organizations").insert({"name": club_name}).execute()
            if not org_res.data:
                raise Exception("Failed to create organization")
            org_id = org_res.data[0]["id"]
            print(f"Organization created. ID: {org_id}")

        # 2. Create Admin User
        print(f"Ensuring Admin user exists: {email}...")
        try:
            auth_res = supabase_admin.auth.admin.create_user({
                "email": email,
                "password": password,
                "email_confirm": True,
                "user_metadata": {"organization_id": str(org_id), "role": "admin"}
            })
            user_id = auth_res.user.id
            print(f"New user created ID: {user_id}")
        except Exception as e:
            if "already been registered" in str(e):
                user_lookup = supabase_admin.table("profiles").select("id").eq("email", email).execute()
                user_id = user_lookup.data[0]["id"]
                supabase_admin.table("profiles").update({"organization_id": org_id, "role": "admin", "display_name": display_name}).eq("id", user_id).execute()
                print(f"Existing user linked ID: {user_id}")
            else:
                raise e

        # 3. Create 3 Missions
        print("Creating 3 missions...")
        mission_ids = []
        for i in range(1, 4):
            m = supabase_admin.table("missions").insert({
                "name": f"Mission Operation {i}", 
                "description": f"Strategic objective level {i} for the Alpha division.",
                "organization_id": org_id
            }).execute().data[0]
            mission_ids.append(m["id"])
        
        # 4. Create 5 Projects per Mission (Total 15)
        print("Creating 15 projects (5 per mission)...")
        project_ids = []
        for idx, m_id in enumerate(mission_ids):
            for j in range(1, 6):
                p = supabase_admin.table("projects").insert({
                    "mission_id": m_id,
                    "name": f"Project {idx+1}.{j}",
                    "description": f"Sub-initiative supporting Mission {idx+1}.",
                    "lead_id": user_id,
                    "organization_id": org_id
                }).execute().data[0]
                project_ids.append(p["id"])

        # 5. Create 7 Tasks per Project (Total 105)
        print("Creating 105 tasks (7 per project)...")
        for p_id in project_ids:
            for k in range(1, 8):
                status = ["todo", "in_progress", "done"][k % 3]
                priority = ["low", "medium", "high"][k % 3]
                supabase_admin.table("tasks").insert({
                    "project_id": p_id, 
                    "title": f"Task {k} for Project {p_id[:4]}", 
                    "description": f"Requirement unit {k} details.",
                    "status": status, 
                    "priority": priority,
                    "organization_id": org_id
                }).execute()

        print("\n" + "="*40)
        print("SUCCESS! Alpha Demo Environment Ready.")
        print(f"Club Identity: {club_name}")
        print(f"User Email:    {email}")
        print(f"Password:      {password}")
        print("="*40)

    except Exception as e:
        print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    create_demo_alpha()
