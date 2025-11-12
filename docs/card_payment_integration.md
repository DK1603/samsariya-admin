# Card Payment Integration - Admin Bot

## Overview

The admin bot now fully supports card payment orders from the client bot. Card payment orders require manual verification by admins before they can be processed.

## Key Changes

### 1. Data Model Updates (`data/models.py`)

Added new fields to the `Order` model:
- `requires_payment_check: Optional[bool]` - Flag indicating card payment needs verification
- Added `PAYMENT_FAILED` status to `OrderStatus` enum

### 2. Order Display (`bot/handlers.py`)

#### Summary View
Card payment orders now show:
- ⚠️ Warning banner: "ТРЕБУЕТ ПРОВЕРКИ ОПЛАТЫ"
- Payment status indicators:
  - 💳✅ - Payment verified
  - 💳⏳ - Awaiting verification
  - 💳 - Card payment
- Claimed payment amount from client

#### Detailed View
Full order details include:
- Contact information (phone, address)
- Payment verification status
- Warning about 10-minute verification window
- All order items and delivery details

### 3. Order Processing

#### New Orders Display (`/new_orders`)
Orders are now separated into two sections:
1. **Card Payment Orders** (shown first, with priority)
   - Flagged with ⚠️ warning
   - Require immediate attention
2. **Regular Orders**
   - Normal cash orders
   - Standard processing flow

#### Action Buttons
For card payment orders in NEW status:
- ✅ **Подтвердить оплату** - Confirm payment → moves to ACCEPTED
- ❌ **Отклонить оплату** - Reject payment → moves to PAYMENT_FAILED
- ✖️ **Отменить заказ** - Cancel order → moves to CANCELLED

For regular orders:
- ✅ **Принять** - Accept order → ACCEPTED
- ✖️ **Отменить** - Cancel order → CANCELLED

### 4. Status Flow

#### Card Payment Orders
```
NEW (requires_payment_check=true)
  ├─> ACCEPTED (payment confirmed) → IN_PROGRESS → READY → COMPLETED
  ├─> PAYMENT_FAILED (payment rejected)
  └─> CANCELLED (order cancelled)
```

#### Regular Orders
```
NEW
  ├─> ACCEPTED → IN_PROGRESS → READY → COMPLETED
  └─> CANCELLED
```

### 5. Client Notifications

Status updates are sent to clients via the client bot:
- ✅ **ACCEPTED** - "Ваш заказ принят" (payment confirmed for card)
- ❌ **PAYMENT_FAILED** - "Оплата отклонена" (payment rejected)
- ❌ **CANCELLED** - "Заказ отменён" (order cancelled)
- 👨‍🍳 **IN_PROGRESS** - "Ваш заказ готовится"
- 🚚 **READY** - "Ваш заказ в пути"
- 🏠 **COMPLETED** - "Заказ доставлен"

### 6. Analytics Updates (`data/operations.py`)

Analytics now treat `payment_failed` orders the same as cancelled orders:
- Excluded from total order count
- Not counted in revenue calculations
- Not included in top items analysis

## Usage Instructions

### For Admins

1. **Check New Orders**
   ```
   /new_orders
   ```
   - Card payment orders appear first with ⚠️ warning
   - Regular orders appear below

2. **Verify Card Payment**
   - Click "👁 Открыть" to see full details
   - Check payment amount claimed by client
   - Verify payment in your payment system (within 10 minutes)
   - Click "✅ Подтвердить оплату" to accept
   - Click "❌ Отклонить оплату" to reject

3. **Process Order**
   - Once payment confirmed (ACCEPTED status):
     - "▶️ В работу" - Start preparing
     - "🍽 Готово" - Mark as ready
     - "✔️ Завершить" - Complete delivery
   - At any stage:
     - "✖️ Отменить" - Cancel the order

4. **Hide Completed Orders**
   - After completion/cancellation/rejection:
     - Click "🙈 Скрыть" to remove from view

### Commands

- `/new_orders` - View all new orders (card payments shown first)
- `/order_<ID>` - View detailed order information
- `/stats_orders [period]` - Order statistics (excludes payment_failed)
- `/earnings [period]` - Revenue report (excludes payment_failed)
- `/help` - Full command reference

## Testing Checklist

- [ ] Card payment order appears in `/new_orders` with ⚠️ warning
- [ ] Payment amount is displayed correctly
- [ ] "Подтвердить оплату" button moves order to ACCEPTED
- [ ] "Отклонить оплату" button moves order to PAYMENT_FAILED
- [ ] Client receives notification for payment confirmation
- [ ] Client receives notification for payment rejection
- [ ] PAYMENT_FAILED orders can be hidden
- [ ] Analytics exclude PAYMENT_FAILED orders
- [ ] Regular cash orders still work normally

## Notes

- The 10-minute timer is tracked on the client side
- `payment_verified` indicates client submitted proof (not admin verification)
- Admin verification updates the `status` field to ACCEPTED or PAYMENT_FAILED
- All status changes trigger client notifications via the client bot
- Orders with `requires_payment_check=true` are prioritized in the display

