import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
anon_key: str = os.environ.get("SUPABASE_KEY")
service_role_key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(url, anon_key)
supabase_admin: Client = create_client(url, service_role_key) if service_role_key else None
