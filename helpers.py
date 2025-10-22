"""Модуль вспомогательных функций для работы с заказами и временем"""
from datetime import datetime
from config import WORK_START_HOUR, WORK_END_HOUR, MIN_HOURS_TO_RESCHEDULE
from database import Database


class OrderHelpers:
    """Вспомогательные функции для работы с заказами"""

    @staticmethod
    def get_available_time_slots(date_str):
        """Получить список доступных временных слотов для даты"""
        available_slots = []
        current_time = datetime.now()

        for hour in range(WORK_START_HOUR, WORK_END_HOUR):
            for minute in [0, 30]:
                time_slot = f"{hour:02d}:{minute:02d}"
                slot_datetime = datetime.strptime(f"{date_str} {time_slot}", '%Y-%m-%d %H:%M')

                # Пропускаем прошедшее время
                if slot_datetime <= current_time:
                    continue

                # Проверяем доступность слота
                if Database.is_time_slot_available(date_str, time_slot):
                    available_slots.append(time_slot)

        return available_slots

    @staticmethod
    def format_delivery_date(delivery_date_str):
        """Форматировать дату доставки для отображения"""
        try:
            date_obj = datetime.strptime(delivery_date_str, '%Y-%m-%d')
            return date_obj.strftime('%d.%m.%Y')
        except:
            return delivery_date_str

    @staticmethod
    def can_cancel_order(order):
        """Проверить, можно ли отменить заказ"""
        try:
            delivery_dt = datetime.strptime(
                f"{order['delivery_date']} {order['delivery_time']}",
                '%Y-%m-%d %H:%M'
            )
            time_until_delivery = (delivery_dt - datetime.now()).total_seconds() / 3600
            return time_until_delivery >= MIN_HOURS_TO_RESCHEDULE
        except:
            return False

    @staticmethod
    def format_bottle_word(count):
        """Получить правильное склонение слова 'бутылка'"""
        if count == 1:
            return 'бутылка'
        elif 2 <= count <= 4:
            return 'бутылки'
        else:
            return 'бутылок'

    @staticmethod
    def enrich_order_data(order):
        """Обогатить данные заказа дополнительной информацией"""
        enriched = order.copy()
        enriched['formatted_date'] = OrderHelpers.format_delivery_date(order.get('delivery_date', ''))
        enriched['bottle_word'] = OrderHelpers.format_bottle_word(order.get('bottles', 1))
        return enriched

    @staticmethod
    def validate_bottle_count(text):
        """Валидировать количество бутылок"""
        try:
            bottles = int(text.strip())

            if bottles <= 0:
                return None, 'bottles_zero'

            if bottles > 100:
                return None, 'bottles_max'

            return bottles, None
        except ValueError:
            return None, 'invalid_bottles'
