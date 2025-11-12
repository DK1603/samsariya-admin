from typing import List, Optional, Dict, Set
from datetime import datetime, timedelta
from .database import db
from .config import ADMIN_IDS
from .models import Order, InventoryItem, Admin, Config, OrderStatus, ClientNotification
# Order Operations
def _stringify_mongo_id(doc: dict) -> dict:
    """Convert Mongo ObjectId in _id field to string for Pydantic models."""
    if doc is None:
        return doc
    _id = doc.get("_id")
    if _id is not None and not isinstance(_id, str):
        try:
            doc = dict(doc)
            doc["_id"] = str(_id)
        except Exception:
            pass
    return doc
 

# Order Operations
async def create_order(order: Order) -> str:
    """Create a new order"""
    order.updated_at = datetime.utcnow()
    result = await db.orders.insert_one(order.dict(exclude={'id'}))
    return str(result.inserted_id)

async def get_order(order_id: str) -> Optional[Order]:
    """Get order by ID"""
    from bson import ObjectId
    doc = await db.orders.find_one({"_id": ObjectId(order_id)})
    doc = _stringify_mongo_id(doc)
    return Order(**doc) if doc else None

async def get_new_orders() -> List[Order]:
    """Get all new orders"""
    cursor = db.orders.find({"status": OrderStatus.NEW}).sort("created_at", -1)
    orders = []
    async for doc in cursor:
        orders.append(Order(**_stringify_mongo_id(doc)))
    return orders

async def update_order_status(order_id: str, status: OrderStatus) -> bool:
    """Update order status"""
    from bson import ObjectId
    result = await db.orders.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": {"status": status, "updated_at": datetime.utcnow()}}
    )
    return result.modified_count > 0

async def update_order_message_id(order_id: str, message_id: int) -> bool:
    """Update order with client message ID for editing"""
    from bson import ObjectId
    result = await db.orders.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": {"client_message_id": message_id}}
    )
    return result.modified_count > 0

async def mark_order_sheet_synced(order_id: str) -> bool:
    """Mark order as synced to Google Sheets"""
    from bson import ObjectId
    result = await db.orders.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": {"sheet_synced": True, "updated_at": datetime.utcnow()}}
    )
    return result.modified_count > 0

async def get_orders_by_period(period: str) -> List[Order]:
    """Get orders for a specific period"""
    now = datetime.utcnow()
    if period == "today":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start_date = now - timedelta(days=7)
    elif period == "month":
        start_date = now - timedelta(days=30)
    else:
        return []
    
    cursor = db.orders.find({"created_at": {"$gte": start_date}}).sort("created_at", -1)
    orders = []
    async for doc in cursor:
        orders.append(Order(**_stringify_mongo_id(doc)))
    return orders

# -------------------------------
# Analytics helpers
# -------------------------------
def _period_start(period: str) -> datetime:
    now = datetime.utcnow()
    p = (period or "").lower().strip()
    if p in ("today", "day", "сегодня"):
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if p in ("week", "неделя"):
        return now - timedelta(days=7)
    if p in ("month", "месяц"):
        return now - timedelta(days=30)
    # default to week if unknown
    return now - timedelta(days=7)

async def analytics_summary(period: str) -> Dict[str, object]:
    """
    Compute analytics for a period.
    Metrics:
      - orders_total: non-cancelled count
      - orders_completed: completed count
      - revenue_completed: sum(total) for completed
      - avg_check_completed: revenue_completed / orders_completed (if >0)
      - top_items: list[(key, qty)] top-3 by quantity across non-cancelled
    """
    start = _period_start(period)
    cursor = db.orders.find({"created_at": {"$gte": start}})

    # Aggregate on raw docs to tolerate unknown statuses like 'pending_admin_confirmation'
    orders_total = 0
    orders_completed = 0
    revenue_completed = 0
    item_key_to_qty: Dict[str, int] = {}

    async for raw in cursor:
        doc = _stringify_mongo_id(raw)
        status_raw = str(doc.get("status", "")).lower()

        is_cancelled = status_raw in ("cancelled", "canceled", "payment_failed")
        is_completed = status_raw == "completed"

        if not is_cancelled:
            orders_total += 1
            items = doc.get("items") or {}
            if isinstance(items, dict):
                for key, qty in items.items():
                    try:
                        item_key_to_qty[key] = item_key_to_qty.get(key, 0) + int(qty or 0)
                    except Exception:
                        continue

        if is_completed:
            orders_completed += 1
            try:
                revenue_completed += int(doc.get("total") or 0)
            except Exception:
                pass

    avg_check_completed = (revenue_completed // orders_completed) if orders_completed > 0 else 0
    top_items = sorted(item_key_to_qty.items(), key=lambda kv: kv[1], reverse=True)[:3]

    return {
        "orders_total": orders_total,
        "orders_completed": orders_completed,
        "revenue_completed": revenue_completed,
        "avg_check_completed": avg_check_completed,
        "top_items": top_items,
        "period": period,
        "start": start,
    }

async def analytics_earnings(period: str) -> int:
    """Return revenue for completed orders in period."""
    summary = await analytics_summary(period)
    return int(summary["revenue_completed"])

# Inventory Operations
async def get_inventory() -> List[InventoryItem]:
    """Return inventory items when they match the InventoryItem model.

    Note: This is preserved for compatibility but may return an empty list if documents
    follow the client-bot schema without `name`/`emoji` fields.
    """
    cursor = db.inventory.find({"key": {"$exists": True}})
    items: List[InventoryItem] = []
    async for doc in cursor:
        try:
            items.append(InventoryItem(**_stringify_mongo_id(doc)))
        except Exception:
            # Skip docs that don't match this schema
            continue
    return items

async def get_inventory_keys() -> List[str]:
    """Fetch and return sorted list of inventory keys from the collection.

    This works with the client-bot schema (key, display_name, short_name, price, ...).
    """
    cursor = db.inventory.find({}, {"key": 1}).sort("key", 1)
    keys: List[str] = []
    async for doc in cursor:
        key = doc.get("key")
        if isinstance(key, str):
            keys.append(key)
    return keys

async def inventory_key_exists(key: str) -> bool:
    """Check if an inventory item with this key exists in any supported schema."""
    count = await db.inventory.count_documents({"key": key}, limit=1)
    return count > 0

async def add_inventory_item(item: InventoryItem) -> str:
    """Add new inventory item"""
    result = await db.inventory.insert_one(item.dict(exclude={'id'}))
    return str(result.inserted_id)

async def update_inventory_availability(key: str, available: bool) -> bool:
    """Update item availability"""
    result = await db.inventory.update_one(
        {"key": key},
        {"$set": {"available": available}}
    )
    return result.modified_count > 0

async def remove_inventory_item(key: str) -> bool:
    """Remove inventory item"""
    result = await db.inventory.delete_one({"key": key})
    return result.deleted_count > 0

# Admin Operations
async def get_admins() -> List[Admin]:
    """Get all admins"""
    cursor = db.admins.find()
    admins = []
    async for doc in cursor:
        admins.append(Admin(**_stringify_mongo_id(doc)))
    return admins

async def is_admin(user_id: int) -> bool:
    """Check if user is admin.

    Priority:
    1) Environment variable ADMIN_IDS
    2) Fallback to admins stored in MongoDB
    """
    try:
        if int(user_id) in ADMIN_IDS:
            return True
    except Exception:
        # Ignore cast issues and continue to DB fallback
        pass

    admin = await db.admins.find_one({"user_id": int(user_id)})
    return admin is not None

async def add_admin(admin: Admin) -> str:
    """Add new admin"""
    result = await db.admins.insert_one(admin.dict(exclude={'id'}))
    return str(result.inserted_id)

# Config Operations
async def get_config(key: str) -> Optional[str]:
    """Get config value"""
    doc = await db.config.find_one({"key": key})
    return doc["value"] if doc else None

async def set_config(key: str, value: str) -> bool:
    """Set config value"""
    result = await db.config.update_one(
        {"key": key},
        {"$set": {"value": value, "updated_at": datetime.utcnow()}},
        upsert=True
    )
    return True 

# Availability Operations (shared doc approach)
AVAILABILITY_DOC_ID = "availability"

async def get_availability_dict() -> Dict[str, bool]:
    """Fetch the availability map from a single availability doc."""
    doc = await db.availability.find_one({"_id": AVAILABILITY_DOC_ID})
    if not doc:
        return {}
    # Exclude MongoDB fields
    return {k: v for k, v in doc.items() if k not in {"_id"}}

async def set_availability_item(key: str, is_enabled: bool) -> bool:
    """Toggle a single item's availability in the shared availability doc."""
    result = await db.availability.update_one(
        {"_id": AVAILABILITY_DOC_ID},
        {"$set": {key: is_enabled}},
        upsert=True,
    )
    # Consider upsert or modified as success
    return (result.modified_count + (1 if result.upserted_id else 0)) > 0

async def seed_inventory_from_catalog(all_keys: Dict[str, str]) -> None:
    """Merge all catalog keys into availability doc, defaulting to True if missing."""
    existing = await db.availability.find_one({"_id": AVAILABILITY_DOC_ID}) or {"_id": AVAILABILITY_DOC_ID}
    updates: Dict[str, bool] = {}
    for key in all_keys.keys():
        if key not in existing:
            updates[key] = True
    if updates:
        await db.availability.update_one(
            {"_id": AVAILABILITY_DOC_ID},
            {"$set": updates},
            upsert=True,
        )

async def seed_availability_from_inventory() -> None:
    """Ensure every inventory item key exists in the availability doc (default True)."""
    existing = await db.availability.find_one({"_id": AVAILABILITY_DOC_ID}) or {"_id": AVAILABILITY_DOC_ID}
    existing_keys: Set[str] = set(existing.keys())
    # Collect all item keys from inventory collection
    cursor = db.inventory.find({}, {"key": 1})
    updates: Dict[str, bool] = {}
    async for doc in cursor:
        key = doc.get("key")
        if isinstance(key, str) and key not in existing_keys:
            updates[key] = True
    if updates:
        await db.availability.update_one(
            {"_id": AVAILABILITY_DOC_ID},
            {"$set": updates},
            upsert=True,
        )

# Client Notification Operations
async def create_client_notification(user_id: int, order_id: str, status: OrderStatus, message: str) -> str:
    """Create a notification for the client bot to send"""
    notification = ClientNotification(
        user_id=user_id,
        order_id=order_id,
        status=status,
        message=message
    )
    result = await db.notifications.insert_one(notification.dict(exclude={'id'}))
    return str(result.inserted_id)

async def get_pending_notifications() -> List[ClientNotification]:
    """Get all pending notifications for the client bot"""
    cursor = db.notifications.find({"sent": False}).sort("created_at", 1)
    notifications = []
    async for doc in cursor:
        notifications.append(ClientNotification(**_stringify_mongo_id(doc)))
    return notifications

async def mark_notification_sent(notification_id: str) -> bool:
    """Mark a notification as sent"""
    from bson import ObjectId
    result = await db.notifications.update_one(
        {"_id": ObjectId(notification_id)},
        {"$set": {"sent": True}}
    )
    return result.modified_count > 0