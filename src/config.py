import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
env_path = Path(__file__).parent.parent / 'config' / '.env'
logger.info(f"[CONFIG_PY] Attempting to load .env from: {env_path}")
# load_dotenv(dotenv_path=env_path)

# Initialize Supabase
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

logger.info(f"[CONFIG_PY] Read SUPABASE_URL from env: {'Exists and has value' if supabase_url else 'MISSING or None'}")
logger.info(f"[CONFIG_PY] Read SUPABASE_KEY from env: {'Exists and has value' if supabase_key else 'MISSING or None'}")
if supabase_key:
    logger.info(f"[CONFIG_PY] SUPABASE_KEY length: {len(supabase_key)}")
if not supabase_url or not supabase_key:
    logger.error("[CONFIG_PY] CRITICAL: SUPABASE_URL or SUPABASE_KEY is missing after os.getenv!")

options = ClientOptions(
    auto_refresh_token=True,
    persist_session=True
)

# supabase: Client = create_client(supabase_url, supabase_key, options=options)
supabase: Client = None
try:
    if supabase_url and supabase_key:
        supabase = create_client(supabase_url, supabase_key, options=options)
        logger.info("[CONFIG_PY] Supabase client CREATED successfully.")
    else:
        logger.error("[CONFIG_PY] Supabase client NOT created due to missing URL/Key.")
except Exception as e:
    logger.error(f"[CONFIG_PY] Error creating Supabase client: {e}", exc_info=True)

# Admin configuration
ADMIN_PHONES = os.getenv("ADMIN_PHONES", "").split(",")
logger.info(f"[CONFIG_PY] Admin phones loaded: {ADMIN_PHONES}")

# Define states
class States:
    INITIAL = "INITIAL"
    CLASS_SELECTION = "CLASS_SELECTION"
    DAY_SELECTION = "DAY_SELECTION"
    TASK_LIST = "TASK_LIST"
    NOTIFICATION_SETUP = "NOTIFICATION_SETUP"
    ADMIN_MENU = "ADMIN_MENU"
    ADMIN_ADD_TASK = "ADMIN_ADD_TASK"
    ADMIN_CLASS_SELECTION = "ADMIN_CLASS_SELECTION"
    ADMIN_DAY_SELECTION = "ADMIN_DAY_SELECTION"
    ADMIN_TASK_NAME = "ADMIN_TASK_NAME"
    ADMIN_TASK_TYPE = "ADMIN_TASK_TYPE"
    ADMIN_TASK_DESCRIPTION = "ADMIN_TASK_DESCRIPTION"
    ADMIN_TASK_DEADLINE = "ADMIN_TASK_DEADLINE"

def is_admin(phone_number: str) -> bool:
    """Check if phone number is in admin whitelist"""
    return phone_number in ADMIN_PHONES 