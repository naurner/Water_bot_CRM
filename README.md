# Water Delivery CRM Bot

Telegram bot that automates order management for a water delivery business. Replaces spreadsheets and manual tracking with a conversational interface for operators.

## Features

- **Order intake** via chat — name, address, quantity, delivery time
- **Phone validation** — enforces `+996 (XXX) XXX-XXX` format
- **Reminder system** — notifies operators 30 minutes before delivery
- **7-day delivery schedule** — plan ahead by day of the week
- **Repeat order shortcuts** — one tap to re-order last delivery
- **Excel export** — full order history in a spreadsheet
- **Address-based filtering** — view orders by delivery zone

## Stack

`Python` `aiogram` `PostgreSQL` `SQLAlchemy` `openpyxl` `APScheduler`

## Quick Start

```bash
git clone https://github.com/naurner/Water_bot_CRM
cd Water_bot_CRM
pip install -r requirements.txt
cp config.py.example config.py   # fill in BOT_TOKEN and DB credentials
python main.py
```

## Config

```python
# config.py
BOT_TOKEN   = "your_telegram_bot_token"
DB_HOST     = "localhost"
DB_NAME     = "water_crm"
DB_USER     = "postgres"
DB_PASSWORD = "password"
```

