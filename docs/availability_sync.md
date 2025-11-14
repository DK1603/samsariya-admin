# Availability Synchronization Between Admin and Client Bots

## Overview

The availability system allows admins to enable/disable items (samsa types and packaging) in real-time. Changes made in the admin bot are immediately reflected in the client bot through MongoDB.

## MongoDB Structure

The availability collection uses a single document with ID `"availability"`:

```json
{
  "_id": "availability",
  "items": {
    "картошка": true,
    "тыква": true,
    "зелень": false,
    "мясо": true,
    "курица_с_сыром": true,
    "пакет": true,
    "коробка": true
  },
  "картошка": true,
  "тыква": true,
  "зелень": false,
  "мясо": true,
  "курица_с_сыром": true,
  "пакет": true,
  "коробка": true,
  "migrated_at": ISODate("..."),
  "synced_at": ISODate("...")
}
```

### Field Structure

- **Root-level fields** (e.g., `"картошка": true`) - Used by both bots for current availability status
- **`items` subdocument** - Legacy structure, kept for backward compatibility
- **`synced_at`** - Timestamp of last admin update
- **`migrated_at`** - Timestamp of initial migration

## How It Works

### Admin Bot (`set_availability_item`)

When an admin toggles availability:

1. Updates **root-level field**: `{key}: true/false`
2. Updates **nested field**: `items.{key}: true/false`
3. Updates **sync timestamp**: `synced_at: current_time`

This ensures both data structures stay synchronized.

### Client Bot

The client bot reads availability from either:
- Root-level fields (preferred)
- `items` subdocument (fallback)

When an item is disabled (`false`), it:
- Won't appear in the order menu
- Can't be selected by customers
- Is hidden from the catalog

## Admin Commands

### `/inventory`

Displays current availability status with toggle buttons:

```
📦 Текущая доступность:

✔️ картошка
✔️ тыква
❌ зелень
✔️ мясо
✔️ курица_с_сыром
✔️ пакет
✔️ коробка

💡 Нажмите кнопку для изменения статуса

[Отключить · картошка]
[Отключить · тыква]
[Включить · зелень]
...
```

**Features:**
- ✔️ Green checkmark = Item is available
- ❌ Red X = Item is disabled
- Click button to toggle status
- Changes take effect immediately

### `/set_avail <key> <0|1>`

Command-line toggle for availability:

```
/set_avail зелень 0    # Disable зелень
/set_avail зелень 1    # Enable зелень
```

**Response:**
```
✅ зелень: выключен
```

## Implementation Details

### `data/operations.py`

#### `get_availability_dict()`
- Reads availability document from MongoDB
- Extracts root-level boolean fields
- Excludes metadata: `_id`, `items`, `migrated_at`, `synced_at`
- Returns: `Dict[str, bool]` (e.g., `{"картошка": True, "зелень": False}`)

#### `set_availability_item(key, is_enabled)`
- Updates both root-level and nested `items.{key}` fields
- Updates `synced_at` timestamp
- Returns: `True` if successful, `False` otherwise

### `bot/handlers.py`

#### `/inventory` Command
1. Fetches all inventory keys from `inventory` collection
2. Gets current availability status from `availability` collection
3. Displays status with inline toggle buttons
4. Each button callback: `avail:{key}:{0|1}`

#### Callback Handler (`cb_toggle_availability`)
1. Validates the inventory key exists
2. Calls `set_availability_item(key, is_enabled)`
3. Refreshes the display with updated status
4. Shows confirmation: "✅ {key}: включен/выключен"

## Synchronization Flow

```
Admin Bot                    MongoDB                     Client Bot
─────────                    ───────                     ──────────
1. Admin clicks              2. Update:                  3. Client fetches
   "Отключить · зелень"         зелень: false               availability
                                items.зелень: false          
                                synced_at: now              
                                                         4. зелень hidden
                                                            from menu
```

## Testing Checklist

- [ ] `/inventory` shows all items from inventory collection
- [ ] Status indicators (✔️/❌) reflect MongoDB values
- [ ] Clicking "Отключить" changes status to ❌
- [ ] Clicking "Включить" changes status to ✔️
- [ ] Changes persist after bot restart
- [ ] Client bot immediately reflects changes (may need menu refresh)
- [ ] Both root-level and `items.{key}` fields are updated
- [ ] `synced_at` timestamp updates on each change

## Troubleshooting

### Items not showing in `/inventory`
- Check that items exist in `inventory` collection with `key` field
- Verify `get_inventory_keys()` returns the expected keys

### Changes not syncing to client bot
- Verify both root-level and `items.{key}` are being updated
- Check client bot is reading from the same MongoDB database
- Ensure client bot refreshes availability on menu access

### Toggle buttons not working
- Check `inventory_key_exists(key)` validates correctly
- Verify MongoDB connection is active
- Check admin permissions with `is_admin(user_id)`

## Notes

- Changes are **immediate** - no bot restart required
- The dual-field structure (root + nested) ensures compatibility with both bots
- The `synced_at` timestamp can be used for cache invalidation
- Default value is `True` if a key is missing from availability document

