"""Модуль для создания клавиатур Telegram бота"""
from telegram import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime, timedelta


class Keyboards:
    """Класс для создания клавиатур"""

    @staticmethod
    def get_main_menu(has_user=False, has_orders=False):
        """Получить клавиатуру главного меню"""
        keyboard = [['📝 Сделать заказ'], ['ℹ️ Информация']]

        if has_user:
            keyboard.insert(1, ['✏️ Изменить данные'])

        if has_orders:
            keyboard.insert(1, ['📋 Мои заказы'])

        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    @staticmethod
    def get_guest_order_menu():
        """Получить меню для гостевого заказа"""
        keyboard = [
            ['👤 Зарегистрироваться'],
            ['📝 Заказать без регистрации'],
            ['◀️ Назад']
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    @staticmethod
    def get_bottles_keyboard():
        """Получить клавиатуру для выбора количества бутылок"""
        keyboard = [
            ['2', '3', '4'],
            ['5', '6', '7'],
            ['◀️ Назад']
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    @staticmethod
    def get_edit_data_keyboard():
        """Получить клавиатуру для редактирования данных"""
        keyboard = [
            ['✏️ Изменить имя'],
            ['📞 Изменить телефон'],
            ['📍 Изменить адрес'],
            ['◀️ Назад']
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    @staticmethod
    def get_date_selection_keyboard():
        """Получить inline клавиатуру для выбора даты"""
        keyboard = []
        today = datetime.now()

        for i in range(7):
            date = today + timedelta(days=i)
            date_str = date.strftime('%Y-%m-%d')

            if i == 0:
                button_text = f"Сегодня ({date.strftime('%d.%m')})"
            elif i == 1:
                button_text = f"Завтра ({date.strftime('%d.%m')})"
            else:
                button_text = date.strftime('%d.%m.%Y (%A)')

            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"date_{date_str}")])

        keyboard.append([InlineKeyboardButton("❌ Отменить", callback_data="cancel")])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def get_time_selection_keyboard(date_str, available_slots):
        """Получить inline клавиатуру для выбора времени"""
        keyboard = []

        if not available_slots:
            keyboard.append([InlineKeyboardButton("❌ Нет свободных слотов", callback_data="no_slots")])
        else:
            for time_slot in available_slots:
                keyboard.append([InlineKeyboardButton(
                    f"⏰ {time_slot}",
                    callback_data=f"time_{time_slot}"
                )])

        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_to_date")])
        keyboard.append([InlineKeyboardButton("❌ Отменить", callback_data="cancel")])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def get_order_actions_keyboard(order_id, can_reschedule=True):
        """Получить клавиатуру действий с заказом"""
        keyboard = [
            [InlineKeyboardButton("❌ Отменить заказ", callback_data=f"cancel_order_{order_id}")]
        ]

        if can_reschedule:
            keyboard.append([InlineKeyboardButton("⏰ Перенести заказ", callback_data=f"reschedule_{order_id}")])

        keyboard.append([InlineKeyboardButton("◀️ Назад к заказам", callback_data="back_to_orders")])
        keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")])

        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def get_orders_list_keyboard(orders):
        """Получить клавиатуру со списком заказов"""
        keyboard = []

        for order in orders:
            keyboard.append([InlineKeyboardButton(
                f"📦 Управление заказом {order['order_id']}",
                callback_data=f"select_order_{order['order_id']}"
            )])

        keyboard.append([InlineKeyboardButton("◀️ Назад в меню", callback_data="back_to_menu")])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def get_cancel_confirmation_keyboard(order_id):
        """Получить клавиатуру подтверждения отмены"""
        keyboard = [
            [InlineKeyboardButton("✅ Да, отменить", callback_data=f"confirm_cancel_{order_id}")],
            [InlineKeyboardButton("❌ Нет, вернуться", callback_data=f"select_order_{order_id}")]
        ]
        return InlineKeyboardMarkup(keyboard)
