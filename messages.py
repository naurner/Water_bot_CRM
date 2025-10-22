"""Модуль для текстовых сообщений бота"""
from config import WORK_START_HOUR, WORK_END_HOUR, DELIVERY_INTERVAL


class Messages:
    """Класс для текстовых сообщений"""

    @staticmethod
    def get_welcome_message(is_registered=False):
        """Приветственное сообщение"""
        status = "✅ Вы зарегистрированы!" if is_registered else "⚠️ Вы можете оформить заказ."
        return (
            f"🌊 Добро пожаловать в сервис доставки воды!\n\n"
            f"{status}\n\n"
            f"Выберите действие:"
        )

    @staticmethod
    def get_info_message():
        """Информационное сообщение"""
        return (
            f"ℹ️ Информация о доставке:\n\n"
            f"⏰ Время работы: {WORK_START_HOUR}:00 - {WORK_END_HOUR}:00\n"
            f"⏱ Интервал между заказами: {DELIVERY_INTERVAL} минут\n"
            f"💧 Доставка питьевой воды по вашему адресу\n\n"
            f"📢 Напоминания:\n"
            f"• В 8:00 утра в день доставки\n"
            f"• За 30 минут до доставки\n\n"
            f"Для оформления заказа нажмите '📝 Сделать заказ'"
        )

    @staticmethod
    def get_user_data_summary(name, phone, address):
        """Сводка данных пользователя"""
        return (
            f"✅ Используются ваши данные:\n"
            f"Имя: {name}\n"
            f"Телефон: {phone}\n"
            f"Адрес: {address}\n\n"
        )

    @staticmethod
    def get_current_user_data(name, phone, address):
        """Текущие данные пользователя"""
        return (
            f"📝 Ваши текущие данные:\n\n"
            f"👤 Имя: {name}\n"
            f"📞 Телефон: {phone}\n"
            f"📍 Адрес: {address}\n\n"
            f"Что вы хотите изменить?"
        )

    @staticmethod
    def get_order_confirmation(order_id, name, phone, address, bottles, delivery_date, delivery_time):
        """Подтверждение заказа"""
        bottle_word = 'бутылка' if bottles == 1 else 'бутылки' if bottles < 5 else 'бутылок'
        return (
            f"✅ Заказ успешно оформлен!\n\n"
            f"📋 Номер заказа: {order_id}\n"
            f"👤 Имя: {name}\n"
            f"📞 Телефон: {phone}\n"
            f"📍 Адрес: {address}\n"
            f"💧 Количество: {bottles} {bottle_word}\n"
            f"📅 Дата: {delivery_date}\n"
            f"⏰ Время: {delivery_time}\n\n"
            f"📢 Вы получите напоминания:\n"
            f"• В 8:00 утра в день доставки\n"
            f"• За 30 минут до доставки\n\n"
            f"Ожидайте доставку в указанное время!"
        )

    @staticmethod
    def get_order_details(order):
        """Детали заказа"""
        bottles = order.get('bottles', 1)
        bottle_word = 'бутылка' if bottles == 1 else 'бутылки' if bottles < 5 else 'бутылок'

        return (
            f"📦 Заказ {order['order_id']}\n\n"
            f"👤 Имя: {order['name']}\n"
            f"📞 Телефон: {order['phone']}\n"
            f"📍 Адрес: {order['address']}\n"
            f"💧 Количество: {bottles} {bottle_word}\n"
            f"📅 Дата доставки: {order.get('formatted_date', order['delivery_date'])}\n"
            f"⏰ Время: {order['delivery_time']}\n"
            f"📊 Статус: {order.get('status', 'Новый')}\n\n"
            f"Что вы хотите сделать с этим заказом?"
        )

    @staticmethod
    def get_orders_list(orders):
        """Список заказов"""
        message = "📋 Ваши активные заказы:\n\n"

        for order in orders:
            bottles = order.get('bottles', 1)
            bottle_word = 'бутылка' if bottles == 1 else 'бутылки' if bottles < 5 else 'бутылок'

            message += (
                f"📦 {order['order_id']}\n"
                f"📅 {order.get('formatted_date', order['delivery_date'])} в {order['delivery_time']}\n"
                f"💧 {bottles} {bottle_word}\n"
                f"📍 {order['address']}\n\n"
            )

        return message

    @staticmethod
    def get_error_message(error_type):
        """Сообщения об ошибках"""
        errors = {
            'invalid_phone': "❌ Неверный формат номера телефона. Пожалуйста, введите номер в формате +996 700 123 456.",
            'invalid_bottles': "❌ Пожалуйста, введите количество бутылок числом (например: 2, 3, 10).",
            'bottles_zero': "❌ Количество бутылок должно быть больше нуля. Пожалуйста, введите корректное число.",
            'bottles_max': "❌ Количество бутылок слишком большое. Пожалуйста, введите число не более 100.",
            'no_slots': "⚠️ На эту дату нет свободных слотов. Выберите другую дату.",
            'slot_taken': "⚠️ К сожалению, это время уже занято!",
            'not_registered': "❌ Вы не зарегистрированы. Сначала оформите заказ или зарегистрируйтесь.",
            'no_orders': "📋 У вас нет активных заказов.\n\nОформите новый заказ!",
            'order_not_found': "❌ Заказ не найден.",
            'cannot_cancel': (
                "❌ Невозможно отменить заказ!\n\n"
                "До доставки осталось менее 4 часов.\n"
                "Отмена заказа возможна только за 4 часа до доставки.\n\n"
                "Пожалуйста, свяжитесь с нами напрямую, если необходимо изменить заказ."
            )
        }
        return errors.get(error_type, "❌ Произошла ошибка.")

    @staticmethod
    def get_cancel_confirmation(order_id):
        """Подтверждение отмены заказа"""
        return (
            f"⚠️ Вы уверены, что хотите отменить заказ {order_id}?\n\n"
            f"Это действие нельзя отменить."
        )

    @staticmethod
    def get_cancel_success(order_id):
        """Успешная отмена заказа"""
        return (
            f"✅ Заказ {order_id} успешно отменен!\n\n"
            f"Вы можете оформить новый заказ в любое время."
        )

    @staticmethod
    def get_cancel_failed(order_id):
        """Ошибка отмены заказа"""
        return (
            f"❌ Не удалось отменить заказ {order_id}.\n"
            f"Попробуйте позже или свяжитесь с поддержкой."
        )

