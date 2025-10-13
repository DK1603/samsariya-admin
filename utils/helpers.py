"""Helper utilities for Samsariya Admin Bot."""
from data.config import ADMIN_IDS

def is_admin(user_id):
    """Check if the user_id is in the admin list."""
    return user_id in ADMIN_IDS

def parse_period(period_str):
    """Parse period string (today, week, month) and return date range."""
    pass

def send_broadcast(text, admin_ids):
    """Send a broadcast message to all admins."""
    pass 