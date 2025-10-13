#!/usr/bin/env python3
"""
Notification sender script for the client bot.
This script should be called periodically by the client bot to send pending notifications.

Usage:
    python scripts/notification_sender.py --bot-token YOUR_CLIENT_BOT_TOKEN
"""

import asyncio
import sys
import os
import argparse

# Ensure project root is on sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from aiogram import Bot
from data.database import db
from data.operations import get_pending_notifications, mark_notification_sent

load_dotenv()


async def send_pending_notifications(bot_token: str):
    """Send all pending notifications to clients."""
    bot = Bot(token=bot_token)
    
    try:
        # Connect to database
        await db.connect()
        
        # Get pending notifications
        notifications = await get_pending_notifications()
        
        if not notifications:
            print("No pending notifications found.")
            return
        
        print(f"Found {len(notifications)} pending notifications.")
        
        sent_count = 0
        for notification in notifications:
            try:
                # Send the notification to the client
                await bot.send_message(notification.user_id, notification.message)
                
                # Mark as sent
                await mark_notification_sent(notification.id)
                sent_count += 1
                
                print(f"✅ Sent notification to user {notification.user_id} for order {notification.order_id}")
                
            except Exception as e:
                print(f"❌ Failed to send notification to user {notification.user_id}: {e}")
                # Don't mark as sent if delivery failed
                continue
        
        print(f"Successfully sent {sent_count}/{len(notifications)} notifications.")
        
    finally:
        await db.disconnect()
        await bot.session.close()


def parse_args():
    parser = argparse.ArgumentParser(description="Send pending notifications to clients")
    parser.add_argument(
        "--bot-token",
        required=True,
        help="Client bot token for sending notifications"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(send_pending_notifications(args.bot_token))
