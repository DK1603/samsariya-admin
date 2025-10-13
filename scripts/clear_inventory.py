#!/usr/bin/env python3
"""
Clear all documents from the MongoDB `inventory` collection.

Usage examples:
  - Dry run (show how many items would be removed):
      python scripts/clear_inventory.py --dry-run

  - Remove without interactive prompt:
      python scripts/clear_inventory.py --yes

  - Default (asks for confirmation):
      python scripts/clear_inventory.py
"""

import asyncio
import os
import sys
import argparse

# Ensure project root is on sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from data.database import db


async def clear_inventory(non_interactive: bool, dry_run: bool) -> None:
    # Load environment variables from .env
    load_dotenv()

    # Connect to database
    await db.connect()
    try:
        current_count = await db.inventory.count_documents({})
        if dry_run:
            print(f"[DRY RUN] Inventory documents present: {current_count}. No changes made.")
            return

        if current_count == 0:
            print("Inventory is already empty. Nothing to remove.")
            return

        if not non_interactive:
            answer = input(
                f"You are about to permanently delete {current_count} inventory documents. Continue? [y/N]: "
            ).strip().lower()
            if answer not in {"y", "yes"}:
                print("Aborted.")
                return

        result = await db.inventory.delete_many({})
        print(f"✅ Removed {result.deleted_count} inventory documents.")
    finally:
        await db.disconnect()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clear MongoDB inventory collection")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Do not prompt for confirmation (non-interactive mode)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show how many documents would be removed without deleting anything",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(clear_inventory(non_interactive=args.yes, dry_run=args.dry_run))


