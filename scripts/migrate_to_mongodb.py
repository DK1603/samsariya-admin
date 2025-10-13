#!/usr/bin/env python3
"""
Migration script to initialize MongoDB with sample data
Run this after setting up MongoDB Atlas connection
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.database import db
from data.models import Admin, InventoryItem, Config
from data.config import ADMIN_IDS, WORK_HOURS

async def migrate():
    """Migrate data to MongoDB"""
    print("🔄 Starting migration to MongoDB...")
    
    # Connect to database
    await db.connect()
    
    try:
        # Create admin users
        print("👥 Creating admin users...")
        for admin_id in ADMIN_IDS:
            admin = Admin(
                user_id=admin_id,
                name=f"Admin {admin_id}"
            )
            await db.admins.insert_one(admin.dict(exclude={'id'}))
        
        # Create sample inventory
        print("📦 Creating sample inventory...")
        sample_items = [
            InventoryItem(
                key="картошка",
                name="Самса из картошки",
                emoji="🥔",
                price=8000,
                available=True
            ),
            InventoryItem(
                key="мясо",
                name="Самса с мясом",
                emoji="🥩",
                price=12000,
                available=True
            ),
            InventoryItem(
                key="курица_с_сыром",
                name="Самса с курицей и сыром",
                emoji="🍗",
                price=10000,
                available=True
            ),
            InventoryItem(
                key="тыква",
                name="Самса с тыквой",
                emoji="🎃",
                price=7000,
                available=True
            ),
            InventoryItem(
                key="зелень",
                name="Самса с зеленью",
                emoji="🌿",
                price=6000,
                available=True
            )
        ]
        
        for item in sample_items:
            await db.inventory.insert_one(item.dict(exclude={'id'}))
        
        # Create config
        print("⚙️ Creating config...")
        configs = [
            Config(key="work_hours", value=WORK_HOURS),
            Config(key="bot_name", value="Samsariya Admin Bot"),
            Config(key="currency", value="сум")
        ]
        
        for config in configs:
            await db.config.insert_one(config.dict(exclude={'id'}))
        
        print("✅ Migration completed successfully!")
        print(f"📊 Created {len(sample_items)} inventory items")
        print(f"👥 Created {len(ADMIN_IDS)} admin users")
        print(f"⚙️ Created {len(configs)} config entries")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(migrate()) 