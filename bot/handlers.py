from aiogram import types, Router
from aiogram.filters import Command
from data.config import ADMIN_IDS, WORK_HOURS
from data.operations import (
    is_admin,
    get_new_orders,
    get_inventory,
    get_inventory_keys,
    get_admins,
    get_availability_dict,
    set_availability_item,
    get_order,
    update_order_status,
    inventory_key_exists,
    create_client_notification,
    analytics_summary,
    analytics_earnings,
)
from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from data.models import OrderStatus

router = Router()

# 1. Authentication & Main Menu
@router.message(Command("start"))
async def cmd_start(message: types.Message):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔️ Доступ запрещён. Вы не администратор.")
        return
    
    await message.answer(
        f"👋 Привет, {message.from_user.full_name}! Вы вошли как администратор.\n\n"
        "Используйте команды из меню или введите /help для справки."
    )


@router.message(Command("menu"))
async def cmd_menu(message: types.Message):
    """Show main admin menu"""
    if not await is_admin(message.from_user.id):
        await message.answer("⛔️ Доступ запрещён. Вы не администратор.")
        return
    
    menu_text = """🔧 **Главное меню администратора:**

**📋 Заказы:**
/new_orders — Новые заказы
/order_<ID> — Детали заказа

**📦 Инвентарь:**
/inventory — Управление доступностью
/add_item — Добавить товар
/remove_item — Удалить товар

**📊 Статистика:**
/weekly_report — Недельный отчёт
/stats_orders [today|week|month] — Сводка заказов
/earnings [today|week|month] — Выручка

**⚙️ Настройки:**
/config — Текущие настройки
/broadcast — Рассылка администраторам

**❓ Справка:**
/help — Подробная справка"""
    
    await message.answer(menu_text, parse_mode="Markdown")

# 2. Order Management
def _format_order_summary(order) -> str:
    # Handle all possible contact formats
    if order.customer_name:
        # Latest format: customer_* fields
        name = order.customer_name
    elif order.name:
        # New format: separate name, phone, address
        name = order.name
    elif order.contact:
        # Old format: "Name, Phone, Address"
        parts = order.contact.split(',')
        name = parts[0].strip() if parts else "—"
    else:
        name = "—"
    
    # Build summary lines
    lines = []
    
    # Add payment verification warning for card payments
    if order.requires_payment_check:
        lines.append("⚠️ ТРЕБУЕТ ПРОВЕРКИ ОПЛАТЫ")
    
    lines.append(f"🆔 {order.id}")
    lines.append(f"👤 {name}")
    
    # Determine payment method clearly
    payment_method = ""
    if "карт" in order.method.lower() or "card" in order.method.lower():
        payment_method = "💳 Оплата картой"
        if order.payment_verified:
            payment_method += " ✅"
        elif order.requires_payment_check:
            payment_method += " ⏳"
    else:
        payment_method = "💵 Наличные"
    
    lines.append(f"💰 {order.total:,} сум")
    lines.append(f"💳 {payment_method}")
    
    # Show claimed payment amount if card payment
    if order.requires_payment_check and order.payment_amount:
        lines.append(f"⚠️ Клиент указал: {order.payment_amount:,} сум")
    
    lines.append(f"📦 {len(order.items)} позиций")
    lines.append(f"📅 {order.created_at.strftime('%d.%m.%Y %H:%M')}")
    
    return "\n".join(lines)


def _build_order_actions_kb(order, expanded: bool = False) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    # Collapsed: only show "Open" and "Cancel" buttons
    if not expanded:
        kb.row(
            InlineKeyboardButton(text="👁 Открыть", callback_data=f"order:open:{order.id}")
        )
        kb.row(
            InlineKeyboardButton(text="✖️ Отменить", callback_data=f"order:confirm:{order.id}:cancelled")
        )
        return kb.as_markup()

    # Expanded: закрыть + доступные переходы + hide option
    kb.row(
        InlineKeyboardButton(text="🔽 Закрыть", callback_data=f"order:close:{order.id}")
    )
    
    # For card payments requiring verification in NEW status
    if order.status == OrderStatus.NEW and order.requires_payment_check:
        kb.row(
            InlineKeyboardButton(text="✅ Подтвердить оплату", callback_data=f"order:confirm:{order.id}:accepted")
        )
        kb.row(
            InlineKeyboardButton(text="❌ Отклонить оплату", callback_data=f"order:confirm:{order.id}:payment_failed")
        )
        kb.row(
            InlineKeyboardButton(text="✖️ Отменить заказ", callback_data=f"order:confirm:{order.id}:cancelled")
        )
    else:
        # Normal status transitions
        next_actions_map = {
            OrderStatus.NEW: [OrderStatus.ACCEPTED, OrderStatus.CANCELLED],
            OrderStatus.ACCEPTED: [OrderStatus.IN_PROGRESS, OrderStatus.CANCELLED],
            OrderStatus.IN_PROGRESS: [OrderStatus.READY, OrderStatus.CANCELLED],
            OrderStatus.READY: [OrderStatus.COMPLETED, OrderStatus.CANCELLED],
        }
        title_map = {
            OrderStatus.ACCEPTED: "✅ Принять",
            OrderStatus.IN_PROGRESS: "▶️ В работу",
            OrderStatus.READY: "🍽 Готово",
            OrderStatus.COMPLETED: "✔️ Завершить",
            OrderStatus.CANCELLED: "✖️ Отменить",
        }
        actions = next_actions_map.get(order.status, [])
        for status in actions:
            kb.row(
                InlineKeyboardButton(
                    text=title_map.get(status, status.value),
                    callback_data=f"order:confirm:{order.id}:{status.value}",
                )
            )
    
    # Add hide option for completed, cancelled, or payment_failed orders
    if order.status in [OrderStatus.COMPLETED, OrderStatus.CANCELLED, OrderStatus.PAYMENT_FAILED]:
        kb.row(
            InlineKeyboardButton(text="🙈 Скрыть", callback_data=f"order:confirm_hide:{order.id}")
        )
    
    return kb.as_markup()

def _build_confirmation_kb(order_id: str, status: str) -> InlineKeyboardMarkup:
    """Build confirmation keyboard for status changes"""
    kb = InlineKeyboardBuilder()
    
    status_texts = {
        "accepted": "принять",
        "in_progress": "перевести в работу", 
        "ready": "отметить как готово",
        "completed": "завершить",
        "cancelled": "отменить",
        "payment_failed": "отклонить оплату"
    }
    
    status_text = status_texts.get(status, status)
    
    kb.row(
        InlineKeyboardButton(
            text=f"✅ Да, {status_text}",
            callback_data=f"order:set:{order_id}:{status}"
        )
    )
    kb.row(
        InlineKeyboardButton(
            text="❌ Нет, отмена",
            callback_data=f"order:open:{order_id}"
        )
    )
    return kb.as_markup()

def _build_hide_confirmation_kb(order_id: str) -> InlineKeyboardMarkup:
    """Build confirmation keyboard for hiding orders"""
    kb = InlineKeyboardBuilder()
    
    kb.row(
        InlineKeyboardButton(
            text="✅ Да, скрыть",
            callback_data=f"order:hide:{order_id}"
        )
    )
    kb.row(
        InlineKeyboardButton(
            text="❌ Нет, отмена",
            callback_data=f"order:open:{order_id}"
        )
    )
    return kb.as_markup()


@router.message(Command("new_orders"))
async def cmd_new_orders(message: types.Message):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔️ Доступ запрещён. Вы не администратор.")
        return
    
    orders = await get_new_orders()
    if not orders:
        await message.answer("📭 Новых заказов нет.")
        return
    
    # Separate card payment orders requiring verification
    card_payment_orders = [o for o in orders if o.requires_payment_check]
    regular_orders = [o for o in orders if not o.requires_payment_check]
    
    # Show card payment orders first (priority)
    if card_payment_orders:
        await message.answer("⚠️ Заказы с оплатой картой (требуют проверки):")
        for order in card_payment_orders:
            await message.answer(_format_order_summary(order), reply_markup=_build_order_actions_kb(order, expanded=False))
    
    # Then show regular orders
    if regular_orders:
        await message.answer("📋 Обычные заказы:")
        for order in regular_orders:
            await message.answer(_format_order_summary(order), reply_markup=_build_order_actions_kb(order, expanded=False))

@router.message(lambda m: m.text and m.text.startswith("/order_"))
async def cmd_order_detail(message: types.Message):
    """Show full order details by ID."""
    if not await is_admin(message.from_user.id):
        await message.answer("⛔️ Доступ запрещён. Вы не администратор.")
        return
    order_id = message.text.split("/order_")[-1].strip()
    order = await get_order(order_id)
    if not order:
        await message.answer("Заказ не найден.")
        return
    # Build detailed view
    lines = ["📦 Детали заказа:"]
    lines.append(_format_order_summary(order))
    
    # Contact details
    if order.customer_phone:
        lines.append(f"📞 {order.customer_phone}")
    elif order.phone:
        lines.append(f"📞 {order.phone}")
    
    if order.customer_address:
        lines.append(f"📍 {order.customer_address}")
    elif order.address:
        lines.append(f"📍 {order.address}")
    
    lines.append(f"🚚 {order.delivery}")
    lines.append(f"⏰ {order.time}")
    lines.append(f"💳 {order.method}")
    
    # Payment verification warning
    if order.requires_payment_check:
        lines.append("\n⚠️ ТРЕБУЕТ ПРОВЕРКИ ОПЛАТЫ")
        if order.payment_amount:
            lines.append(f"Клиент указал сумму: {order.payment_amount:,} сум")
        if order.payment_verified:
            lines.append("✅ Клиент отправил подтверждение оплаты")
        lines.append("⏰ Проверьте оплату в течение 10 минут")
    
    lines.append("\n📦 Состав:")
    for key, qty in order.items.items():
        lines.append(f" • {key}: {qty} шт")
    
    if order.summary:
        lines.append("\nПримечание:")
        lines.append(order.summary)

    await message.answer("\n".join(lines), reply_markup=_build_order_actions_kb(order, expanded=True))

async def _notify_client_status(order, new_status: OrderStatus):
    """Send status update directly to client and edit existing message if possible."""
    from data.operations import update_order_message_id
    from aiogram import Bot
    from data.config import CLIENT_BOT_TOKEN
    
    status_texts = {
        OrderStatus.ACCEPTED: "✅ Ваш заказ принят",
        OrderStatus.IN_PROGRESS: "👨‍🍳 Ваш заказ готовится", 
        OrderStatus.READY: "🚚 Ваш заказ в пути",
        OrderStatus.COMPLETED: "🏠 Заказ доставлен",
        OrderStatus.CANCELLED: "❌ Заказ отменён",
        OrderStatus.PAYMENT_FAILED: "❌ Оплата отклонена",
    }
    
    # Get customer name
    customer_name = order.customer_name or order.name or "Клиент"
    
    # Build concise order summary
    order_items = []
    for key, qty in order.items.items():
        order_items.append(f"• {key}: {qty} шт")
    
    status_text = status_texts.get(new_status, f"Статус заказа обновлён: {new_status.value}")
    
    # Create concise message
    message = f"{status_text}\n\n"
    message += f"👤 {customer_name}\n"
    message += f"💰 {order.total:,} сум\n"
    message += f"📦 Состав:\n" + "\n".join(order_items)
    
    # Add delivery info for ready status
    if new_status == OrderStatus.READY:
        message += f"\n🚚 {order.delivery}"
        if order.time:
            message += f"\n⏰ {order.time}"
    
    # Create bot instance for sending messages to clients
    if not CLIENT_BOT_TOKEN:
        print("❌ CLIENT_BOT_TOKEN not configured")
        return
    
    bot = Bot(token=CLIENT_BOT_TOKEN)
    
    try:
        if order.client_message_id:
            # Edit existing message
            try:
                await bot.edit_message_text(
                    chat_id=order.user_id,
                    message_id=order.client_message_id,
                    text=message
                )
                print(f"✏️ Edited message for user {order.user_id}, order {order.id}")
            except Exception as e:
                print(f"❌ Failed to edit message: {e}")
                # If editing fails, send new message
                sent_message = await bot.send_message(
                    chat_id=order.user_id,
                    text=message
                )
                await update_order_message_id(order.id, sent_message.message_id)
        else:
            # Send new message
            sent_message = await bot.send_message(
                chat_id=order.user_id,
                text=message
            )
            await update_order_message_id(order.id, sent_message.message_id)
            print(f"📤 Sent new message for user {order.user_id}, order {order.id}")
    except Exception as e:
        print(f"❌ Failed to send message to user {order.user_id}: {e}")
    finally:
        await bot.session.close()


@router.message(lambda m: m.text and m.text.startswith("/set_status_"))
async def cmd_set_status(message: types.Message):
    """Change order status by command: /set_status_<ID>_<status>."""
    if not await is_admin(message.from_user.id):
        await message.answer("⛔️ Доступ запрещён. Вы не администратор.")
        return
    try:
        _, rest = message.text.split("/set_status_", 1)
        order_id, status_text = rest.split("_", 1)
        new_status = OrderStatus(status_text)
    except Exception:
        await message.answer(
            "Использование: /set_status_<ID>_<status>\n"
            "Статусы: new, accepted, in_progress, ready, completed, cancelled"
        )
        return

    ok = await update_order_status(order_id, new_status)
    if ok:
        order = await get_order(order_id)
        await _notify_client_status(order, new_status)
        await message.answer("Статус обновлён.")
    else:
        await message.answer("Не удалось обновить статус. Проверьте ID и попробуйте ещё раз.")





@router.callback_query(lambda c: c.data and c.data.startswith("order:"))
async def cb_order_actions(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return
    parts = callback.data.split(":")
    # Patterns: order:open:<id> | order:close:<id> | order:view:<id> | order:confirm:<id>:<status> | order:set:<id>:<status> | order:confirm_hide:<id> | order:hide:<id>
    if len(parts) < 3:
        await callback.answer("Ошибка данных", show_alert=True)
        return
    action = parts[1]
    order_id = parts[2]

    if action == "open" or action == "view":
        order = await get_order(order_id)
        if not order:
            await callback.answer("Не найдено", show_alert=True)
            return
        
        # Build clean order details
        lines = []
        
        # Show name at the top (most important info) - check all possible name fields
        if order.customer_name:
            lines.append(f"👤 {order.customer_name}")
        elif order.name:
            lines.append(f"👤 {order.name}")
        elif order.contact:
            lines.append(f"👤 {order.contact.split(',')[0]}")
        else:
            lines.append("👤 Имя не указано")
        
        # Order ID and amount
        lines.append(f"🆔 {order.id}")
        lines.append(f"💰 {order.total:,} сум")
        
        # Payment verification status (if card payment)
        if "карт" in order.method.lower() or "card" in order.method.lower():
            if order.payment_verified:
                lines.append("💳 ✅ Оплата подтверждена")
            else:
                lines.append("💳 ⏳ Требует проверки оплаты")
        
        # Contact details (check all possible contact fields)
        if order.customer_name and order.customer_phone and order.customer_address:
            # Latest format: customer_* fields
            lines.append(f"📞 {order.customer_phone}")
            lines.append(f"📍 {order.customer_address}")
        elif order.name and order.phone and order.address:
            # New format: separate fields
            lines.append(f"📞 {order.phone}")
            lines.append(f"📍 {order.address}")
        elif order.contact and ',' in order.contact:
            # Old format: combined contact
            parts = order.contact.split(',')
            if len(parts) >= 2:
                lines.append(f"📞 {parts[1].strip()}")
            if len(parts) >= 3:
                lines.append(f"📍 {parts[2].strip()}")
        
        # Delivery info (clean up duplicate emojis)
        delivery_text = order.delivery.replace("🚚", "").strip()
        lines.append(f"🚚 {delivery_text}")
        lines.append(f"⏰ {order.time}")
        
        # Payment method (clean up duplicate emojis)
        method_text = order.method.replace("💳", "").replace("💰", "").strip()
        lines.append(f"💳 {method_text}")
        
        # Items with prices
        lines.append("\n📦 Заказ:")
        for key, qty in order.items.items():
            lines.append(f"• {key}: {qty} шт")
        
        # Clean summary (remove HTML tags) - only if it contains useful info beyond the order items
        if order.summary:
            clean_summary = order.summary.replace('<b>', '').replace('</b>', '').replace('<br>', '\n')
            # Only show if it's not just a duplicate of the order items
            if not any(key in clean_summary.lower() for key in order.items.keys()):
                lines.append(f"\n📄 {clean_summary}")
        
        await callback.message.edit_text("\n".join(lines), reply_markup=_build_order_actions_kb(order, expanded=True))
        await callback.answer()
        return

    if action == "close":
        order = await get_order(order_id)
        if not order:
            await callback.answer("Не найдено", show_alert=True)
            return
        await callback.message.edit_text(_format_order_summary(order), reply_markup=_build_order_actions_kb(order, expanded=False))
        await callback.answer()
        return

    if action == "confirm" and len(parts) == 4:
        # Show confirmation dialog
        status_text = parts[3]
        status_names = {
            "accepted": "принять заказ",
            "in_progress": "перевести заказ в работу",
            "ready": "отметить заказ как готовый",
            "completed": "завершить заказ",
            "cancelled": "отменить заказ"
        }
        
        status_name = status_names.get(status_text, status_text)
        
        await callback.message.edit_text(
            f"⚠️ **Подтверждение действия**\n\n"
            f"Вы уверены, что хотите {status_name}?\n\n"
            f"Это действие нельзя отменить!",
            reply_markup=_build_confirmation_kb(order_id, status_text),
            parse_mode="Markdown"
        )
        await callback.answer()
        return

    if action == "confirm_hide":
        # Show hide confirmation dialog
        await callback.message.edit_text(
            f"⚠️ **Подтверждение скрытия**\n\n"
            f"Вы уверены, что хотите скрыть этот заказ?\n\n"
            f"Заказ будет удалён из вашего интерфейса, но останется в базе данных.",
            reply_markup=_build_hide_confirmation_kb(order_id),
            parse_mode="Markdown"
        )
        await callback.answer()
        return

    if action == "hide":
        # Hide the order message
        await callback.message.delete()
        await callback.answer("✅ Заказ скрыт")
        return

    if action == "set" and len(parts) == 4:
        status_text = parts[3]
        try:
            new_status = OrderStatus(status_text)
        except Exception:
            await callback.answer("Некорректный статус", show_alert=True)
            return
        ok = await update_order_status(order_id, new_status)
        if not ok:
            await callback.answer("Не удалось обновить", show_alert=True)
            return
        order = await get_order(order_id)
        await _notify_client_status(order, new_status)
        
        # Update the message to show the new status instead of confirmation dialog
        status_names = {
            "accepted": "принят",
            "in_progress": "переведён в работу", 
            "ready": "готов",
            "completed": "завершён",
            "cancelled": "отменён"
        }
        
        status_name = status_names.get(status_text, status_text)
        
        # Build updated message with new status (same clean format)
        lines = []
        
        # Show name at the top (most important info) - check all possible name fields
        if order.customer_name:
            lines.append(f"👤 {order.customer_name}")
        elif order.name:
            lines.append(f"👤 {order.name}")
        elif order.contact:
            lines.append(f"👤 {order.contact.split(',')[0]}")
        else:
            lines.append("👤 Имя не указано")
        
        # Order ID and amount
        lines.append(f"🆔 {order.id}")
        lines.append(f"💰 {order.total:,} сум")
        
        # Payment verification status (if card payment)
        if "карт" in order.method.lower() or "card" in order.method.lower():
            if order.payment_verified:
                lines.append("💳 ✅ Оплата подтверждена")
            else:
                lines.append("💳 ⏳ Требует проверки оплаты")
        
        # Contact details (check all possible contact fields)
        if order.customer_name and order.customer_phone and order.customer_address:
            # Latest format: customer_* fields
            lines.append(f"📞 {order.customer_phone}")
            lines.append(f"📍 {order.customer_address}")
        elif order.name and order.phone and order.address:
            # New format: separate fields
            lines.append(f"📞 {order.phone}")
            lines.append(f"📍 {order.address}")
        elif order.contact and ',' in order.contact:
            # Old format: combined contact
            parts = order.contact.split(',')
            if len(parts) >= 2:
                lines.append(f"📞 {parts[1].strip()}")
            if len(parts) >= 3:
                lines.append(f"📍 {parts[2].strip()}")
        
        # Delivery info (clean up duplicate emojis)
        delivery_text = order.delivery.replace("🚚", "").strip()
        lines.append(f"🚚 {delivery_text}")
        lines.append(f"⏰ {order.time}")
        
        # Payment method (clean up duplicate emojis)
        method_text = order.method.replace("💳", "").replace("💰", "").strip()
        lines.append(f"💳 {method_text}")
        
        # Items with prices
        lines.append("\n📦 Заказ:")
        for key, qty in order.items.items():
            lines.append(f"• {key}: {qty} шт")
        
        # Clean summary (remove HTML tags) - only if it contains useful info beyond the order items
        if order.summary:
            clean_summary = order.summary.replace('<b>', '').replace('</b>', '').replace('<br>', '\n')
            # Only show if it's not just a duplicate of the order items
            if not any(key in clean_summary.lower() for key in order.items.keys()):
                lines.append(f"\n📄 {clean_summary}")
        
        # Status update
        lines.append(f"\n✅ Заказ {status_name}")
        
        await callback.message.edit_text(
            "\n".join(lines), 
            reply_markup=_build_order_actions_kb(order, expanded=True),
            parse_mode="Markdown"
        )
        await callback.answer("✅ Статус обновлён")




# 3. Inventory Management
@router.message(Command("inventory"))
async def cmd_inventory(message: types.Message):
    """Show items with availability and provide inline toggle buttons for admins."""
    if not await is_admin(message.from_user.id):
        await message.answer("⛔️ Доступ запрещён. Вы не администратор.")
        return

    availability = await get_availability_dict()
    keys = await get_inventory_keys()
    if not keys:
        await message.answer("Инвентарь пуст.")
        return

    # Build inline keyboard with toggle buttons (only existing items)
    kb = InlineKeyboardBuilder()
    lines = []
    # availability may be either flat fields or nested under `items`
    nested = availability.get("items") if isinstance(availability, dict) else None
    avail_map = nested if isinstance(nested, dict) else availability
    for key in keys:
        is_enabled = bool(avail_map.get(key, True))
        status = "✔️" if is_enabled else "❌"
        lines.append(f"{status} {key}")
        toggle_to = "0" if is_enabled else "1"
        kb.row(
            InlineKeyboardButton(
                text=("Отключить" if is_enabled else "Включить") + f" · {key}",
                callback_data=f"avail:{key}:{toggle_to}",
            )
        )

    text = "Текущая доступность:\n\n" + "\n".join(lines)
    await message.answer(text, reply_markup=kb.as_markup())

@router.message(Command("add_item"))
async def cmd_add_item(message: types.Message):
    """Add a new item to the catalog."""
    pass

@router.message(Command("remove_item"))
async def cmd_remove_item(message: types.Message):
    """Remove an item from the catalog."""
    pass

@router.message(Command("set_avail"))
async def cmd_set_avail(message: types.Message):
    """Enable or disable item availability via command: /set_avail <key> <0|1>."""
    if not await is_admin(message.from_user.id):
        await message.answer("⛔️ Доступ запрещён. Вы не администратор.")
        return

    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("Использование: /set_avail <ключ> <0|1>")
        return
    key, raw = parts[1], parts[2]
    if raw not in {"0", "1"}:
        await message.answer("Значение должно быть 0 (выключить) или 1 (включить)")
        return
    is_enabled = raw == "1"
    ok = await set_availability_item(key, is_enabled)
    if ok:
        await message.answer(
            f"Готово. {key}: {'включен' if is_enabled else 'выключен'}. Используйте /inventory для просмотра."
        )
    else:
        await message.answer("Не удалось обновить доступность. Попробуйте позже.")


@router.callback_query(lambda c: c.data and c.data.startswith("avail:"))
async def cb_toggle_availability(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return

    _, key, to = callback.data.split(":", 2)
    is_enabled = to == "1"
    # Validate inventory key to avoid toggling non-existent fields
    if not await inventory_key_exists(key):
        await callback.answer("Нет такого товара", show_alert=True)
        return
    ok = await set_availability_item(key, is_enabled)
    if ok:
        # Refresh the message content
        availability = await get_availability_dict()
        keys = await get_inventory_keys()
        kb = InlineKeyboardBuilder()
        lines = []
        nested = availability.get("items") if isinstance(availability, dict) else None
        avail_map = nested if isinstance(nested, dict) else availability
        for k in keys:
            enabled = bool(avail_map.get(k, True))
            status = "✔️" if enabled else "❌"
            lines.append(f"{status} {k}")
            toggle_to = "0" if enabled else "1"
            kb.row(
                InlineKeyboardButton(
                    text=("Отключить" if enabled else "Включить") + f" · {k}",
                    callback_data=f"avail:{k}:{toggle_to}",
                )
            )
        text = "Текущая доступность:\n\n" + "\n".join(lines)
        await callback.message.edit_text(text, reply_markup=kb.as_markup())
        await callback.answer("Обновлено")
    else:
        await callback.answer("Не удалось обновить", show_alert=True)

# 4. General
@router.message(Command("broadcast"))
async def cmd_broadcast(message: types.Message, bot: Bot):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔️ Доступ запрещён. Вы не администратор.")
        return
    text = message.text.partition(' ')[2].strip()
    if not text:
        await message.answer("Использование: /broadcast <текст>")
        return
    count = 0
    for admin_id in ADMIN_IDS:
        if admin_id != message.from_user.id:
            try:
                await bot.send_message(admin_id, f"[Broadcast] {text}")
                count += 1
            except Exception:
                pass
    await message.answer(f"Сообщение отправлено {count} администраторам.")

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔️ Доступ запрещён. Вы не администратор.")
        return
    
    help_text = """🔧 **Доступные команды:**

**Основные:**
/start — Главное меню
/menu — Показать меню
/help — Эта справка

**Заказы:**
/new_orders — Новые заказы (отдельно показывает заказы с оплатой картой)
/order_<ID> — Детали заказа

**Работа с заказами:**
• Для заказов с оплатой картой: подтвердить/отклонить оплату
• Для обычных заказов: принять → в работу → готово → завершить
• Все заказы можно отменить на любом этапе
• После завершения/отмены можно скрыть заказ из списка

**Инвентарь:**
/inventory — Управление доступностью
/add_item — Добавить товар
/remove_item — Удалить товар

**Статистика:**
/weekly_report — Недельный отчёт (итоги, выручка, топ‑позиции)
/stats_orders [today|week|month] — Сводка по заказам (по умолчанию week)
/earnings [today|week|month] — Выручка за период (по умолчанию week)

**Настройки:**
/config — Текущие настройки
/broadcast — Рассылка администраторам

**Статусы заказов:**
• new — Новый заказ
• accepted — Принят (оплата подтверждена для карты)
• in_progress — В работе
• ready — Готов к доставке
• completed — Завершён
• cancelled — Отменён
• payment_failed — Оплата отклонена"""
    
    await message.answer(help_text, parse_mode="Markdown")

@router.message(Command("config"))
async def cmd_config(message: types.Message):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔️ Доступ запрещён. Вы не администратор.")
        return
    
    admins = await get_admins()
    admin_names = ', '.join(admin.name for admin in admins) or "—"
    env_admins = ', '.join(str(a) for a in ADMIN_IDS) or "—"
    await message.answer(
        "Текущие настройки:\n"
        f"Рабочие часы: {WORK_HOURS}\n"
        f"Администраторы (БД): {admin_names}\n"
        f"Администраторы (ENV): {env_admins}"
    )

# 5. Statistics
@router.message(Command("stats_orders"))
async def cmd_stats_orders(message: types.Message):
    """Show order stats for a period: today|week|month (default: week)."""
    if not await is_admin(message.from_user.id):
        await message.answer("⛔️ Доступ запрещён. Вы не администратор.")
        return
    parts = (message.text or "").split()
    period = parts[1].lower() if len(parts) > 1 else "week"
    summary = await analytics_summary(period)
    orders_total = summary["orders_total"]
    orders_completed = summary["orders_completed"]
    revenue = summary["revenue_completed"]
    avg_check = summary["avg_check_completed"]
    top_items = summary["top_items"]
    top_lines = "\n".join([f"• {k}: {v} шт" for k, v in top_items]) or "—"
    text = (
        f"📊 Статистика ({period}):\n\n"
        f"Заказы (всего, без отмен): {orders_total}\n"
        f"Завершено: {orders_completed}\n"
        f"Выручка (завершённые): {revenue:,} сум\n"
        f"Средний чек: {avg_check:,} сум\n\n"
        f"Топ позиций:\n{top_lines}"
    )
    await message.answer(text)

@router.message(Command("weekly_report"))
async def cmd_weekly_report(message: types.Message):
    """Generate and send a weekly sales report."""
    if not await is_admin(message.from_user.id):
        await message.answer("⛔️ Доступ запрещён. Вы не администратор.")
        return
    summary = await analytics_summary("week")
    orders_total = summary["orders_total"]
    orders_completed = summary["orders_completed"]
    revenue = summary["revenue_completed"]
    avg_check = summary["avg_check_completed"]
    top_items = summary["top_items"]
    top_lines = "\n".join([f"• {k}: {v} шт" for k, v in top_items]) or "—"
    text = (
        "📈 Недельный отчёт:\n\n"
        f"Заказы (всего, без отмен): {orders_total}\n"
        f"Завершено: {orders_completed}\n"
        f"Выручка (завершённые): {revenue:,} сум\n"
        f"Средний чек: {avg_check:,} сум\n\n"
        f"Топ позиций:\n{top_lines}"
    )
    await message.answer(text)

@router.message(Command("monthly_report"))
async def cmd_monthly_report(message: types.Message):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔️ Доступ запрещён. Вы не администратор.")
        return
    await message.answer("Команда отключена. Используйте /weekly_report.")

@router.message(Command("earnings"))
async def cmd_earnings(message: types.Message):
    """Show total earnings for a period: today|week|month (default: week)."""
    if not await is_admin(message.from_user.id):
        await message.answer("⛔️ Доступ запрещён. Вы не администратор.")
        return
    parts = (message.text or "").split()
    period = parts[1].lower() if len(parts) > 1 else "week"
    from data.operations import analytics_earnings
    revenue = await analytics_earnings(period)
    await message.answer(f"💰 Выручка ({period}, завершённые заказы): {revenue:,} сум")

# demand_chart removed per request