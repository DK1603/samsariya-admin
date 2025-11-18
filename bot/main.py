import asyncio
import sys
import os
import signal
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from data.config import BOT_TOKEN, ADMIN_IDS
from data.database import db
from bot.handlers import router
from data.operations import seed_availability_from_inventory, get_new_orders
from utils.sheets import append_order_to_sheet
from data.operations import mark_order_sheet_synced
from data.models import OrderStatus
from utils.helpers import format_uzbekistan_datetime

async def set_bot_commands(bot: Bot):
    """Set up bot commands menu"""
    commands = [
        BotCommand(command="start", description="🚀 Запустить бота"),
        BotCommand(command="menu", description="🔧 Главное меню"),
        BotCommand(command="help", description="❓ Справка"),
        BotCommand(command="new_orders", description="📋 Новые заказы"),
        BotCommand(command="inventory", description="📦 Управление доступностью"),
        BotCommand(command="weekly_report", description="📈 Недельный отчёт"),
        BotCommand(command="stats_orders", description="📊 Сводка по заказам"),
        BotCommand(command="earnings", description="💰 Выручка за период"),
        BotCommand(command="config", description="⚙️ Настройки"),
        BotCommand(command="broadcast", description="📢 Рассылка"),
    ]
    await bot.set_my_commands(commands)

def format_order_summary(order) -> str:
    """Format order summary for notifications"""
    # Handle all possible contact formats
    if order.customer_name:
        name = order.customer_name
    elif order.name:
        name = order.name
    elif order.contact:
        name = order.contact.split(',')[0]
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
    lines.append(f"📅 {format_uzbekistan_datetime(order.created_at)}")
    
    return "\n".join(lines)

def build_order_actions_kb(order) -> dict:
    """Build order action keyboard for notifications.
    
    Shows only "Open" and "Cancel" buttons to prevent accidental acceptance
    of card payment orders without verification.
    """
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    
    kb = InlineKeyboardBuilder()
    # Only show "Open" and "Cancel" buttons in collapsed view
    kb.row(InlineKeyboardButton(text="👁 Открыть", callback_data=f"order:open:{order.id}"))
    kb.row(InlineKeyboardButton(text="✖️ Отменить", callback_data=f"order:confirm:{order.id}:cancelled"))
    return kb.as_markup()

# Track notified orders to avoid duplicates
notified_orders = set()

async def check_new_orders(bot: Bot):
    """Check for new orders and notify admins"""
    try:
        orders = await get_new_orders()
        if orders:
            for order in orders:
                # Only notify if we haven't notified about this order before
                if order.id not in notified_orders:
                    # Send to all admins
                    for admin_id in ADMIN_IDS:
                        try:
                            await bot.send_message(
                                admin_id,
                                f"🆕 **Новый заказ!**\n\n{format_order_summary(order)}",
                                reply_markup=build_order_actions_kb(order),
                                parse_mode="Markdown"
                            )
                        except Exception as e:
                            print(f"Failed to send order notification to admin {admin_id}: {e}")
                    
                    # Push to Google Sheets once (avoid duplicates)
                    try:
                        if not getattr(order, "sheet_synced", False):
                            ok = await append_order_to_sheet(order)
                            if ok:
                                await mark_order_sheet_synced(order.id)
                    except Exception as e:
                        print(f"Failed to sync order {order.id} to Sheets: {e}")

                    # Mark as notified
                    notified_orders.add(order.id)
                    print(f"Notified admins about new order: {order.id}")
    except Exception as e:
        print(f"Error checking new orders: {e}")

async def order_monitor(bot: Bot):
    """Monitor for new orders every 10 seconds"""
    while True:
        await check_new_orders(bot)
        await asyncio.sleep(10)  # Check every 10 seconds

async def shutdown_handler(bot: Bot, monitor_task):
    """Handle graceful shutdown"""
    print("\n🛑 Получен сигнал завершения...")
    print("📤 Закрытие соединений...")
    
    # Cancel monitoring task
    if monitor_task and not monitor_task.done():
        monitor_task.cancel()
        try:
            await asyncio.wait_for(monitor_task, timeout=2.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass
    
    # Close bot session
    try:
        await bot.session.close()
    except Exception:
        pass
    
    # Disconnect from MongoDB
    try:
        await db.disconnect()
    except Exception:
        pass
    
    print("✅ Соединения закрыты успешно")
    print("👋 Бот остановлен")

async def main():
    # Connect to MongoDB
    await db.connect()
    # Ensure availability doc has all known inventory keys
    await seed_availability_from_inventory()
    
    # Initialize bot
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    
    # Set up bot commands menu
    await set_bot_commands(bot)
    
    print("Samsariya Admin Bot is running...")
    print("Bot commands menu has been set up!")
    print("Order monitoring is active - new orders will be sent automatically!")
    print("Press Ctrl+C to stop the bot gracefully")
    
    monitor_task = None
    
    try:
        # Start order monitoring in background
        monitor_task = asyncio.create_task(order_monitor(bot))
        
        # Start the bot
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        print("\n⚠️ Получен сигнал прерывания (Ctrl+C)")
    except asyncio.CancelledError:
        # This is expected when shutting down gracefully
        pass
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
    finally:
        await shutdown_handler(bot, monitor_task)

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    print("\n🛑 Получен сигнал завершения (Ctrl+C)")
    print("⏳ Завершение работы...")

if __name__ == "__main__":
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен пользователем")
    except asyncio.CancelledError:
        # This is expected during graceful shutdown
        print("\n👋 Бот остановлен")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        sys.exit(1)