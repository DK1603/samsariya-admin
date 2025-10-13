import os
import motor.motor_asyncio
from typing import Optional
from .models import Order, InventoryItem, Admin, Config

class Database:
    def __init__(self):
        self.client: Optional[motor.motor_asyncio.AsyncIOMotorClient] = None
        self.db: Optional[motor.motor_asyncio.AsyncIOMotorDatabase] = None
        
    async def connect(self):
        """Connect to MongoDB Atlas"""
        try:
            mongodb_uri = os.getenv("MONGODB_URI")
            if not mongodb_uri:
                raise ValueError("MONGODB_URI environment variable not set")
            
            self.client = motor.motor_asyncio.AsyncIOMotorClient(mongodb_uri)
            self.db = self.client.samsariya
            
            # Test connection
            await self.client.admin.command('ping')
            print("✅ Connected to MongoDB Atlas")
            
        except Exception as e:
            print(f"❌ Failed to connect to MongoDB: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            print("🔌 Disconnected from MongoDB")
    
    # Collections
    @property
    def orders(self):
        return self.db.orders
    
    @property
    def inventory(self):
        return self.db.inventory
    
    @property
    def admins(self):
        return self.db.admins
    
    @property
    def config(self):
        return self.db.config

    @property
    def availability(self):
        return self.db.availability

    @property
    def notifications(self):
        return self.db.notifications

# Global database instance
db = Database() 