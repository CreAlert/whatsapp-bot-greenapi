import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
env_path = Path(__file__).parent.parent / 'config' / '.env'
load_dotenv(dotenv_path=env_path)

# Initialize Supabase
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# Admin configuration
ADMIN_PHONES = os.getenv("ADMIN_PHONES", "").split(",")

# Define states
class States:
    INITIAL = "INITIAL"
    CLASS_SELECTION = "CLASS_SELECTION"
    DAY_SELECTION = "DAY_SELECTION"
    TASK_LIST = "TASK_LIST"
    NOTIFICATION_SETUP = "NOTIFICATION_SETUP"
    ADMIN_MENU = "ADMIN_MENU"
    ADMIN_ADD_TASK = "ADMIN_ADD_TASK"

def is_admin(phone_number: str) -> bool:
    """Check if phone number is in admin whitelist"""
    return phone_number in ADMIN_PHONES 