import os
from pathlib import Path
from supabase import create_client, Client
from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

url: str = os.environ.get("SUPABASE_URL")
anon_key: str = os.environ.get("SUPABASE_KEY")
service_key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(url, anon_key)
supabase_admin: Client = create_client(url, service_key)
