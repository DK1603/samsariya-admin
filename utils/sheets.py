import asyncio
import json
from typing import Dict, Tuple
from datetime import datetime

import aiohttp

from data.config import SHEETS_WEBHOOK_URL
from data.models import Order


def _split_items(items: Dict[str, int]) -> Tuple[str, str]:
    samsa_parts = []
    packaging_parts = []
    for key, qty in items.items():
        key_l = key.lower()
        entry = f"{key}: {qty} шт"
        if "пакет" in key_l or "короб" in key_l or "коробка" in key_l:
            packaging_parts.append(entry)
        else:
            samsa_parts.append(entry)
    return ", ".join(samsa_parts), ", ".join(packaging_parts)


def _normalize_method(method: str) -> str:
    if not method:
        return ""
    return method.replace("💳", "").replace("💵", "").strip()


def build_row(order: Order) -> Dict[str, str]:
    samsa_details, packaging_details = _split_items(order.items)
    customer_name = order.customer_name or order.name or ""
    customer_phone = order.customer_phone or order.phone or ""
    customer_address = order.customer_address or order.address or ""
    ts = order.created_at if isinstance(order.created_at, datetime) else datetime.utcnow()
    return {
        "timestamp": ts.isoformat(),
        "order_id": order.id or "",
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "customer_address": customer_address,
        "total": str(order.total),
        "payment_method": _normalize_method(order.method),
        "status": order.status.value if hasattr(order.status, "value") else str(order.status),
        "samsa_details": samsa_details,
        "packaging_details": packaging_details,
    }


async def append_order_to_sheet(order: Order) -> bool:
    if not SHEETS_WEBHOOK_URL:
        return False
    payload = build_row(order)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(SHEETS_WEBHOOK_URL, json=payload, timeout=15) as resp:
                return 200 <= resp.status < 300
    except Exception:
        return False

