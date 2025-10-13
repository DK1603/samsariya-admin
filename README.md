# Samsariya Admin Telegram Bot

This is the admin bot for the Samsariya project, designed to help administrators manage orders, inventory, and view statistics. It is the second bot in the system, after the client-facing Samsariya bot.

## Features

### 1. Authentication
- `/start` — Checks if the user is an admin and greets them.

### 2. Order Management
- `/new_orders` — List new (unprocessed) orders (ID, name, amount).
- `/order_<ID>` — Show full order details (items, quantity, contact, address, payment method).
- `/set_status_<ID>_<status>` — Change order status (accepted, in_progress, ready, completed, cancelled) and notify the client.

### 3. Inventory Management
- `/inventory` — Show current items and their availability (✔️/❌).
- `/add_item <key> <name> <price>` — Add a new item to the catalog.
- `/remove_item <key>` — Remove an item from the catalog.
- `/set_avail <key> <0|1>` — Enable (1) or disable (0) item availability.

### 4. General
- `/broadcast <text>` — Send a notification to all admins.
- `/help` — Show help for available commands.
- `/config` — Show current settings (working hours, admin list, etc.).

### 5. Statistics
- `/stats_orders [<period>]` — Show order history for a period (today, week, month) with details: order count, most popular item.
- `/weekly_report` — Generate and send a weekly sales report: revenue, average check, top-3 popular items.
- `/monthly_report` — Same as above, but for the month.
- `/earnings <period>` — Show total earnings for a period (today, week, month).
- `/demand_chart <period>` — Send a chart (how many times each item was ordered in the period).

---

## Project Structure
- `bot/` — Main bot logic and command handlers
- `data/` — Data storage (orders, inventory, config)
- `utils/` — Utility functions
- `tests/` — Unit tests

---

## Getting Started

### 1. Set up MongoDB Atlas
1. Follow the setup guide in `docs/mongodb_setup.md`
2. Get your MongoDB connection string
3. Create a `.env` file based on `env.example`

### 2. Install Dependencies
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment
1. Copy `env.example` to `.env`
2. Set your bot token and MongoDB URI
3. Add admin user IDs (comma-separated)

### 4. Initialize Database
```bash
python scripts/migrate_to_mongodb.py
```

### 5. Run the Bot
```bash
python run_bot.py
```

## Environment Variables
- `BOT_TOKEN`: Your Telegram bot token
- `MONGODB_URI`: MongoDB Atlas connection string
- `ADMIN_IDS`: Comma-separated list of admin user IDs
- `WORK_HOURS`: Working hours (e.g., "09:00-21:00") 