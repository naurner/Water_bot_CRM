import os
from dotenv import load_dotenv

load_dotenv()

# Токен Telegram бота
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Настройки времени работы доставки
WORK_START_HOUR = 9  # Начало работы доставки (9:00)
WORK_END_HOUR = 20   # Конец работы доставки (20:00)
DELIVERY_INTERVAL = 30  # Интервал между доставками в минутах

# Минимальное время для переноса заказа (в часах)
MIN_HOURS_TO_RESCHEDULE = 4

# Файлы для хранения данных
USERS_FILE = 'users.xlsx'
ORDERS_FILE = 'orders.xlsx'
