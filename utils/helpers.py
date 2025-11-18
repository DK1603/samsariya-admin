"""Helper utilities for Samsariya Admin Bot."""
from data.config import ADMIN_IDS
from datetime import datetime, timedelta

# Uzbekistan timezone offset (UTC+5)
UZB_TIMEZONE_OFFSET = timedelta(hours=5)

def to_uzbekistan_time(utc_dt: datetime) -> datetime:
    """Convert UTC datetime to Uzbekistan local time (UTC+5).
    
    Args:
        utc_dt: datetime object in UTC timezone
        
    Returns:
        datetime object in Uzbekistan local time (UTC+5)
    """
    if utc_dt is None:
        return None
    return utc_dt + UZB_TIMEZONE_OFFSET

def format_uzbekistan_datetime(utc_dt: datetime) -> str:
    """Format UTC datetime as Uzbekistan local time string.
    
    Args:
        utc_dt: datetime object in UTC timezone
        
    Returns:
        Formatted string in DD.MM.YYYY HH:MM format (Uzbekistan time)
    """
    if utc_dt is None:
        return "—"
    local_dt = to_uzbekistan_time(utc_dt)
    return local_dt.strftime('%d.%m.%Y %H:%M')

def is_admin(user_id):
    """Check if the user_id is in the admin list."""
    return user_id in ADMIN_IDS

def parse_period(period_str):
    """Parse period string (today, week, month) and return date range."""
    pass

def send_broadcast(text, admin_ids):
    """Send a broadcast message to all admins."""
    pass 