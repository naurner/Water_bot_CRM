# Water Delivery Bot

Telegram bot for a water delivery service in Bishkek. Customers order bottled water in a chat instead of calling: they leave their details once, pick a day and a time slot, and get reminders before the courier arrives.

## What it does

- **Registration**: name, phone and address are asked once and reused; phone numbers are checked against the Kyrgyz format (`+996 700 123 456` or `0700123456`).
- **Ordering**: number of bottles, a day within the next 7 days, a 30-minute slot between 9:00 and 20:00. Slots already taken are not offered.
- **My orders**: list of active orders with details, cancel and reschedule buttons.
- **Rescheduling and cancelling** are allowed up to 4 hours before delivery.
- **Reminders**: at 8:00 on the delivery day and 30 minutes before the slot. Cancelling or moving an order removes or moves its reminders.
- **Address check** (optional): with a Google Maps API key, addresses are geocoded and the district of Bishkek is detected; `/address <text>` tests it.
- **Storage**: users and orders are kept in two Excel files (`users.xlsx`, `orders.xlsx`), which the owner can open and edit directly.

## Stack

Python 3.10+ · python-telegram-bot 20 (ConversationHandler, JobQueue) · openpyxl · requests · python-dotenv · pytest

## Project layout

| File | Purpose |
|---|---|
| `main.py` | conversation flow: menu, registration, ordering, my orders, reschedule, cancel |
| `database.py` | reading and writing users and orders in Excel |
| `reminder_service.py` | delivery reminders through JobQueue, reschedule rules |
| `address_validator.py` | Google Geocoding check and district detection |
| `keyboards.py`, `messages.py`, `states.py` | keyboards, message texts, conversation states |
| `config.py` | working hours, slot length, file names, token from `.env` |

## Run

```bash
git clone https://github.com/naurner/Water_bot_CRM
cd Water_bot_CRM
pip install -r requirements.txt
cp .env.example .env        # put TELEGRAM_BOT_TOKEN in it
python main.py
```

## Tests

```bash
pip install pytest pytest-asyncio
pytest -v
```

## Known limitations

- Reminders are kept in memory: if the bot restarts, reminders for orders created before the restart are not restored.
- Excel storage is fine for one small business, but concurrent writes are not protected; the next step would be SQLite or PostgreSQL.
