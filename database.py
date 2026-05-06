import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
anon_key: str = os.environ.get("SUPABASE_KEY")
service_role_key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

print(f"DEBUG: SUPABASE_URL present: {bool(url)}")
print(f"DEBUG: SUPABASE_KEY present: {bool(anon_key)}")
print(f"DEBUG: SUPABASE_SERVICE_ROLE_KEY present: {bool(service_role_key)}")

supabase: Client = create_client(url, anon_key)
supabase_admin: Client = create_client(url, service_role_key) if service_role_key else None

print(f"DEBUG: supabase client initialized: {bool(supabase)}")
print(f"DEBUG: supabase_admin client initialized: {bool(supabase_admin)}")
