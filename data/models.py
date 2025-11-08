from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum

class OrderStatus(str, Enum):
    NEW = "new"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    READY = "ready"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class PaymentMethod(str, Enum):
    CASH = "cash"
    CARD = "card"

class Order(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: int
    items: Dict[str, int]  # item_key: quantity
    total: int
    # Support multiple contact formats
    contact: Optional[str] = None  # Legacy format: "Name, Phone, Address"
    name: Optional[str] = None     # New format: separate name
    phone: Optional[str] = None    # New format: separate phone
    address: Optional[str] = None  # New format: separate address
    # Latest format: customer_* fields
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_address: Optional[str] = None
    delivery: str
    time: str
    method: str
    summary: Optional[str] = None
    status: OrderStatus = OrderStatus.NEW
    # Payment verification fields
    payment_verified: Optional[bool] = None
    payment_amount: Optional[int] = None
    is_preorder: Optional[bool] = None
    # Message tracking for editing
    client_message_id: Optional[int] = None  # Telegram message ID sent to client
    # Sheet sync flag
    sheet_synced: Optional[bool] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class InventoryItem(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    key: str  # e.g., "картошка"
    name: str  # e.g., "Самса из картошки"
    emoji: str  # e.g., "🥔"
    price: int
    available: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Admin(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: int
    name: str
    role: str = "admin"
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Config(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    key: str
    value: str
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ClientNotification(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: int
    order_id: str
    status: OrderStatus
    message: str
    sent: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow) 