import logging
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from database import Database
from config import TELEGRAM_BOT_TOKEN, WORK_START_HOUR, WORK_END_HOUR, DELIVERY_INTERVAL, MIN_HOURS_TO_RESCHEDULE
from utils import validate_kyrgyzstan_phone, format_kyrgyzstan_phone
from reminder_service import ReminderScheduler
from address_validator import test_address_validation, get_address_validator

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
(CHOOSING_ACTION, REGISTRATION_NAME, REGISTRATION_PHONE, REGISTRATION_ADDRESS,
 ORDER_NAME, ORDER_PHONE, ORDER_ADDRESS, ORDER_BOTTLES, ORDER_DATE, ORDER_TIME,
 RESCHEDULE_SELECT, RESCHEDULE_DATE, RESCHEDULE_TIME, ORDER_ACTION,
 EDIT_NAME, EDIT_PHONE, EDIT_ADDRESS) = range(17)


class WaterBot:
    """Telegram бот для заказа воды"""

    def __init__(self):
        Database.init_users_file()
        Database.init_orders_file()

    @staticmethod
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user_id = update.effective_user.id
        user = Database.get_user(user_id)

        keyboard = [
            ['📦 Сделать заказ'],
            ['ℹ️ Информация']
        ]

        # Добавляем кнопку изменения данных только для зарегистрированных пользователей
        if user:
            keyboard.insert(1, ['✏️ Изменить данные'])

        # Проверяем наличие активных заказов
        active_orders = Database.get_active_user_orders(user_id)
        if active_orders:
            keyboard.insert(1, ['📋 Мои заказы'])

        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        welcome_text = (
            f"🌊 Добро пожаловать в сервис доставки воды!\n\n"
            f"{'✅ Вы зарегистрированы!' if user else '⚠️ Вы можете оформить заказ.'}\n\n"
            f"Выберите действие:"
        )

        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
        return CHOOSING_ACTION

    @staticmethod
    async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик главного меню"""
        text = update.message.text
        user_id = update.effective_user.id

        if text == '📦 Сделать заказ':
            user = Database.get_user(user_id)

            if user:
                # Зарегистрированный пользователь
                context.user_data['order_type'] = 'registered'
                context.user_data['name'] = user['name']
                context.user_data['phone'] = user['phone']
                context.user_data['address'] = user['address']

                # Клавиатура для выбора количества бутылок
                keyboard = [
                    ['2', '3', '4'],
                    ['5', '6', '7'],
                    ['◀️ Назад']
                ]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

                await update.message.reply_text(
                    f"✅ Используются ваши данные:\n"
                    f"Имя: {user['name']}\n"
                    f"Телефон: {user['phone']}\n"
                    f"Адрес: {user['address']}\n\n"
                    f"💧 Введите количество бутылок воды (можете выбрать из предложенных или ввести свое число):",
                    reply_markup=reply_markup
                )

                return ORDER_BOTTLES
            else:
                # Незарегистрированный пользователь
                keyboard = [
                    ['👤 Зарегистрироваться'],
                    ['📦 Заказать без регистрации'],
                    ['◀️ Назад']
                ]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

                await update.message.reply_text(
                    "Вы не зарегистрированы. Выберите вариант:",
                    reply_markup=reply_markup
                )
                return CHOOSING_ACTION

        elif text == '👤 Регистрация':
            await update.message.reply_text(
                "📝 Введите ваше имя:",
                reply_markup=ReplyKeyboardRemove()
            )
            return REGISTRATION_NAME

        elif text == '👤 Зарегистрироваться':
            await update.message.reply_text(
                "📝 Введите ваше имя:",
                reply_markup=ReplyKeyboardRemove()
            )
            return REGISTRATION_NAME

        elif text == '📦 Заказать без регистрации':
            context.user_data['order_type'] = 'guest'
            await update.message.reply_text(
                "📝 Введите ваше имя:",
                reply_markup=ReplyKeyboardRemove()
            )
            return ORDER_NAME

        elif text == 'ℹ️ Информация':
            info_text = (
                f"ℹ️ Информация о доставке:\n\n"
                f"⏰ Время работы: {WORK_START_HOUR}:00 - {WORK_END_HOUR}:00\n"
                f"⏱ Интервал между заказами: {DELIVERY_INTERVAL} минут\n"
                f"💧 Доставка питьевой воды по вашему адресу\n\n"
                f"🔔 Напоминания:\n"
                f"• В 8:00 утра в день доставки\n"
                f"• За 30 минут до доставки\n\n"
                f"Для оформления заказа нажмите '📦 Сделать заказ'"
            )
            await update.message.reply_text(info_text)
            return CHOOSING_ACTION

        elif text == '📋 Мои заказы':
            return await WaterBot.show_my_orders(update, context)

        elif text == '✏️ Изменить данные':
            user = Database.get_user(user_id)
            if user:
                keyboard = [
                    ['✏️ Изменить имя'],
                    ['📱 Изменить телефон'],
                    ['📍 Изменить адрес'],
                    ['◀️ Назад']
                ]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

                await update.message.reply_text(
                    f"📝 Ваши текущие данные:\n\n"
                    f"👤 Имя: {user['name']}\n"
                    f"📱 Телефон: {user['phone']}\n"
                    f"📍 Адрес: {user['address']}\n\n"
                    f"Что вы хотите изменить?",
                    reply_markup=reply_markup
                )
                return CHOOSING_ACTION
            else:
                await update.message.reply_text(
                    "❌ Вы не зарегистрированы. Сначала оформите заказ или зарегистрируйтесь."
                )
                return CHOOSING_ACTION

        elif text == '✏️ Изменить имя':
            await update.message.reply_text(
                "📝 Введите новое имя:",
                reply_markup=ReplyKeyboardRemove()
            )
            return EDIT_NAME

        elif text == '📱 Изменить телефон':
            await update.message.reply_text(
                "📱 Введите новый номер телефона в формате:\n"
                "+996 700 123 456 или 0700123456",
                reply_markup=ReplyKeyboardRemove()
            )
            return EDIT_PHONE

        elif text == '📍 Изменить адрес':
            await update.message.reply_text(
                "📍 Введите новый адрес доставки:",
                reply_markup=ReplyKeyboardRemove()
            )
            return EDIT_ADDRESS

        elif text == '◀️ Назад':
            return await WaterBot.start(update, context)

        return CHOOSING_ACTION

    # Регистрация
    @staticmethod
    async def registration_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получение имени при регистрации"""
        context.user_data['reg_name'] = update.message.text
        await update.message.reply_text(
            "📱 Введите ваш номер телефона (например: +996 700 123 456):"
        )
        return REGISTRATION_PHONE

    @staticmethod
    async def registration_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получение телефона при регистрации"""
        phone_number = update.message.text

        # Валидация номера телефона
        if not validate_kyrgyzstan_phone(phone_number):
            await update.message.reply_text(
                "❌ Неверный формат номера телефона. Пожалуйста, введите номер в формате +996 700 123 456."
            )
            return REGISTRATION_PHONE

        context.user_data['reg_phone'] = phone_number
        await update.message.reply_text(
            "📍 Введите адрес доставки:"
        )
        return REGISTRATION_ADDRESS

    @staticmethod
    async def registration_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Завершение регистрации"""
        address = update.message.text
        user_id = update.effective_user.id

        # Форматируем номер телефона перед сохранением
        formatted_phone = format_kyrgyzstan_phone(context.user_data['reg_phone'])

        Database.save_user(
            user_id,
            context.user_data['reg_name'],
            formatted_phone,
            address
        )

        keyboard = [
            ['📦 Сделать заказ'],
            ['✏️ Изменить данные'],
            ['ℹ️ Информация']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            "✅ Регистрация успешно завершена!\n"
            "Теперь вы можете оформить заказ.",
            reply_markup=reply_markup
        )

        # Очищаем временные данные
        context.user_data.clear()

        return CHOOSING_ACTION

    # Заказ без регистрации
    @staticmethod
    async def order_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получение имени для заказа"""
        context.user_data['name'] = update.message.text
        await update.message.reply_text(
            "📱 Введите ваш номер телефона в формате:\n"
            "+996 700 123 456 или 0700123456"
        )
        return ORDER_PHONE

    @staticmethod
    async def order_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получение телефона для заказа"""
        phone_number = update.message.text

        # Валидация номера телефона
        if not validate_kyrgyzstan_phone(phone_number):
            await update.message.reply_text(
                "❌ Неверный формат номера телефона. Пожалуйста, введите номер в формате +996 700 123 456."
            )
            return ORDER_PHONE

        context.user_data['phone'] = phone_number
        await update.message.reply_text(
            "📍 Введите адрес доставки:"
        )
        return ORDER_ADDRESS

    @staticmethod
    async def order_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получение адреса и переход к выбору количества бутылок"""
        context.user_data['address'] = update.message.text

        # Клавиатура для выбора количества бутылок
        keyboard = [
            ['2', '3', '4'],
            ['5', '6', '7'],
            ['◀️ Назад']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            "💧 Введите количество бутылок воды (можете выбрать из предложенных или ввести свое число):",
            reply_markup=reply_markup
        )
        return ORDER_BOTTLES

    @staticmethod
    async def order_bottles(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получение количества бутылок"""
        text = update.message.text

        if text == '◀️ Назад':
            # Возвращаемся в главное меню
            context.user_data.clear()
            return await WaterBot.start(update, context)

        # Пытаемся преобразовать текст в число
        try:
            bottles = int(text.strip())

            # Проверяем, что количество разумное (больше 0)
            if bottles <= 0:
                await update.message.reply_text(
                    "❌ Количество бутылок должно быть больше нуля. Пожалуйста, введите корректное число."
                )
                return ORDER_BOTTLES

            if bottles > 100:
                await update.message.reply_text(
                    "❌ Количество бутылок слишком большое. Пожалуйста, введите число не более 100."
                )
                return ORDER_BOTTLES

            context.user_data['bottles'] = bottles

            await update.message.reply_text(
                f"✅ Выбрано: {bottles} бутыл{'ка' if bottles == 1 else 'ки' if bottles < 5 else 'ок'}\n"
                f"Теперь выберите дату доставки:",
                reply_markup=ReplyKeyboardRemove()
            )

            return await WaterBot.show_date_selection(update, context)
        except ValueError:
            await update.message.reply_text(
                "❌ Пожалуйста, введите количество бутылок числом (например: 2, 3, 10)."
            )
            return ORDER_BOTTLES

    @staticmethod
    async def show_date_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать выбор даты"""
        keyboard = []
        today = datetime.now()

        # Предлагаем следующие 7 дней
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

        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            await update.callback_query.message.edit_text(
                "📅 Выберите дату доставки:",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                "📅 Выберите дату доставки:",
                reply_markup=reply_markup
            )

        return ORDER_DATE

    @staticmethod
    async def handle_date_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора даты"""
        query = update.callback_query
        await query.answer()

        if query.data == "cancel":
            await query.message.edit_text("❌ Заказ отменен.")
            context.user_data.clear()
            return await WaterBot.start_after_callback(update, context)

        date_str = query.data.replace("date_", "")
        context.user_data['delivery_date'] = date_str

        # Генерируем доступное время
        return await WaterBot.show_time_selection(update, context)

    @staticmethod
    async def show_time_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать выбор времени"""
        date_str = context.user_data['delivery_date']
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')

        keyboard = []
        current_time = datetime.now()
        min_hours_ahead = 4  # Минимум 4 часа до доставки

        # Генерируем слоты времени с интервалом 30 минут
        for hour in range(WORK_START_HOUR, WORK_END_HOUR):
            for minute in [0, 30]:
                time_slot = f"{hour:02d}:{minute:02d}"
                slot_datetime = datetime.strptime(f"{date_str} {time_slot}", '%Y-%m-%d %H:%M')

                # Проверяем, что время не в прошлом и не менее чем за 4 часа
                time_until_slot = (slot_datetime - current_time).total_seconds() / 3600  # в часах
                if time_until_slot < min_hours_ahead:
                    continue

                # Проверяем доступность слота - показываем только свободные
                if Database.is_time_slot_available(date_str, time_slot):
                    keyboard.append([InlineKeyboardButton(
                        f"⏰ {time_slot}",
                        callback_data=f"time_{time_slot}"
                    )])

        # Если нет доступных слотов
        if not keyboard:
            keyboard.append([InlineKeyboardButton("❌ Нет свободных слотов", callback_data="no_slots")])

        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_to_date")])
        keyboard.append([InlineKeyboardButton("❌ Отменить", callback_data="cancel")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        query = update.callback_query
        await query.message.edit_text(
            f"⏰ Выберите время доставки на {date_obj.strftime('%d.%m.%Y')}:\n"
            f"(Показаны только свободные слоты, доступные не менее чем за 4 часа)",
            reply_markup=reply_markup
        )

        return ORDER_TIME

    @staticmethod
    async def handle_time_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора времени и создание заказа"""
        query = update.callback_query
        await query.answer()

        if query.data == "cancel":
            await query.message.edit_text("❌ Заказ отменен.")
            context.user_data.clear()
            return await WaterBot.start_after_callback(update, context)

        if query.data == "back_to_date":
            return await WaterBot.show_date_selection(update, context)

        if query.data == "no_slots":
            await query.answer("⚠️ На эту дату нет свободных слотов. Выберите другую дату.", show_alert=True)
            return await WaterBot.show_date_selection(update, context)

        if query.data == "occupied":
            await query.answer("⚠️ Это время уже занято!", show_alert=True)
            return ORDER_TIME

        time_str = query.data.replace("time_", "")

        # Проверяем доступность еще раз
        date_str = context.user_data['delivery_date']
        if not Database.is_time_slot_available(date_str, time_str):
            await query.answer("⚠️ К сожалению, это время уже занято!", show_alert=True)
            return await WaterBot.show_time_selection(update, context)

        # Форматируем номер телефона перед сохранением
        formatted_phone = format_kyrgyzstan_phone(context.user_data['phone'])

        # Создаем заказ
        user_id = update.effective_user.id
        delivery_date = datetime.strptime(date_str, '%Y-%m-%d')
        bottles = context.user_data.get('bottles', 1)

        order_id = Database.save_order(
            user_id,
            context.user_data['name'],
            formatted_phone,
            context.user_data['address'],
            delivery_date,
            time_str,
            bottles
        )

        # Планируем напоминания через JobQueue
        reminders = await ReminderScheduler.schedule_reminders(
            context,
            user_id,
            order_id,
            date_str,
            time_str,
            context.user_data['address']
        )

        # Сохраняем ID запланированных сообщений в базе данных
        if reminders:
            morning_msg_id = reminders['morning'].get('message_id')
            pre_delivery_msg_id = reminders['pre_delivery'].get('message_id')
            Database.update_order_reminder_ids(order_id, morning_msg_id, pre_delivery_msg_id)
            logger.info(f"Сохранены ID напоминаний для заказа {order_id}: morning={morning_msg_id}, pre_delivery={pre_delivery_msg_id}")

        # Формируем сообщение о подтверждении
        confirmation_text = (
            f"✅ Заказ успешно оформлен!\n\n"
            f"📋 Номер заказа: {order_id}\n"
            f"👤 Имя: {context.user_data['name']}\n"
            f"📱 Телефон: {formatted_phone}\n"
            f"📍 Адрес: {context.user_data['address']}\n"
            f"💧 Количество: {bottles} бутыл{'ка' if bottles == 1 else 'ки' if bottles < 5 else 'ок'}\n"
            f"📅 Дата: {delivery_date.strftime('%d.%m.%Y')}\n"
            f"⏰ Время: {time_str}\n\n"
            f"🔔 Вы получите напоминания:\n"
            f"• В 8:00 утра в день доставки\n"
            f"• За 30 минут до доставки\n\n"
            f"Ожидайте доставку в указанное время!"
        )

        await query.message.edit_text(confirmation_text)

        # Очищаем данные
        context.user_data.clear()

        # Возвращаем в главное меню
        keyboard = [
            ['📦 Сделать заказ'],
            ['✏️ Изменить данные'],
            ['📋 Мои заказы'],
            ['ℹ️ Информация']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Чем еще могу помочь?",
            reply_markup=reply_markup
        )

        return CHOOSING_ACTION

    @staticmethod
    async def start_after_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Возврат в главное меню после callback"""
        user_id = update.effective_user.id
        user = Database.get_user(user_id)

        keyboard = [
            ['📦 Сделать заказ'],
            ['ℹ️ Информация']
        ]

        # Добавляем кнопку изменения данных только для зарегистрированных пользователей
        if user:
            keyboard.insert(1, ['✏️ Изменить данные'])

        # Проверяем наличие активных заказов
        active_orders = Database.get_active_user_orders(user_id)
        if active_orders:
            keyboard.insert(1, ['📋 Мои заказы'])

        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Главное меню:",
            reply_markup=reply_markup
        )

        return CHOOSING_ACTION

    @staticmethod
    async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отмена текущей операции"""
        context.user_data.clear()

        user_id = update.effective_user.id
        user = Database.get_user(user_id)

        keyboard = [
            ['📦 Сделать заказ'],
            ['ℹ️ Информация']
        ]

        # Добавляем кнопку изменения данных только для зарегистрированных пользователей
        if user:
            keyboard.insert(1, ['✏️ Изменить данные'])

        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            "❌ Операция отменена.",
            reply_markup=reply_markup
        )

        return CHOOSING_ACTION

    @staticmethod
    async def show_my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать список заказов пользователя"""
        user_id = update.effective_user.id
        orders = Database.get_active_user_orders(user_id)

        if not orders:
            keyboard = [
                ['📦 Сделать заказ'],
                ['◀️ Назад']
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

            await update.message.reply_text(
                "📋 У вас нет активных заказов.\n\nОформите новый заказ!",
                reply_markup=reply_markup
            )
            return CHOOSING_ACTION

        # Формируем сообщение с inline кнопками для каждого заказа
        message = "📋 Ваши активные заказы:\n\n"
        keyboard = []

        for order in orders:
            delivery_dt = datetime.strptime(
                f"{order['delivery_date']} {order['delivery_time']}",
                '%Y-%m-%d %H:%M'
            )
            bottles = order.get('bottles', 1)

            message += (
                f"📦 {order['order_id']}\n"
                f"📅 {delivery_dt.strftime('%d.%m.%Y')} в {order['delivery_time']}\n"
                f"💧 {bottles} бутыл{'ка' if bottles == 1 else 'ки' if bottles < 5 else 'ок'}\n"
                f"📍 {order['address']}\n\n"
            )

            # Добавляем кнопку для выбора заказа
            keyboard.append([InlineKeyboardButton(
                f"🔧 Управление заказом {order['order_id']}",
                callback_data=f"select_order_{order['order_id']}"
            )])

        keyboard.append([InlineKeyboardButton("◀️ Назад в меню", callback_data="back_to_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message, reply_markup=reply_markup)

        return ORDER_ACTION

    @staticmethod
    async def handle_order_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора заказа - показываем меню действий"""
        query = update.callback_query
        await query.answer()

        # Обработка кнопки "Перенести заказ"
        if query.data.startswith("reschedule_"):
            order_id = query.data.replace("reschedule_", "")
            context.user_data['reschedule_order_id'] = order_id

            # Показываем выбор новой даты
            await query.message.edit_text(f"⏰ Перенос заказа {order_id}\n\nВыберите новую дату доставки:")
            return await WaterBot.show_reschedule_date_selection(update, context)

        if query.data == "back_to_menu":
            user_id = update.effective_user.id
            user = Database.get_user(user_id)

            keyboard = [
                ['📦 Сделать заказ'],
                ['ℹ️ Информация']
            ]

            if user:
                keyboard.insert(1, ['✏️ Изменить данные'])

            # Проверяем наличие активных заказов
            active_orders = Database.get_active_user_orders(user_id)
            if active_orders:
                keyboard.insert(1, ['📋 Мои заказы'])

            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

            await query.message.edit_text("Главное меню:")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Выберите действие:",
                reply_markup=reply_markup
            )
            return CHOOSING_ACTION

        if query.data.startswith("select_order_"):
            order_id = query.data.replace("select_order_", "")
            order = Database.get_order_by_id(order_id)

            if not order:
                await query.message.edit_text("❌ Заказ не найден.")
                return await WaterBot.start_after_callback(update, context)

            # Формируем подробную информацию о заказе
            delivery_dt = datetime.strptime(
                f"{order['delivery_date']} {order['delivery_time']}",
                '%Y-%m-%d %H:%M'
            )
            bottles = order.get('bottles', 1)

            order_info = (
                f"📦 Заказ {order['order_id']}\n\n"
                f"👤 Имя: {order['name']}\n"
                f"📱 Телефон: {order['phone']}\n"
                f"📍 Адрес: {order['address']}\n"
                f"💧 Количество: {bottles} бутыл{'ка' if bottles == 1 else 'ки' if bottles < 5 else 'ок'}\n"
                f"📅 Дата доставки: {delivery_dt.strftime('%d.%m.%Y')}\n"
                f"⏰ Время: {order['delivery_time']}\n"
                f"📊 Статус: {order.get('status', 'Новый')}\n\n"
                f"Что вы хотите сделать с этим заказом?"
            )

            # Проверяем, можно ли перенести заказ
            can_reschedule = ReminderScheduler.can_reschedule(
                order['delivery_date'],
                order['delivery_time'],
                MIN_HOURS_TO_RESCHEDULE
            )

            keyboard = []

            # Кнопка отмены заказа
            keyboard.append([InlineKeyboardButton(
                "❌ Отменить заказ",
                callback_data=f"cancel_order_{order_id}"
            )])

            # Кнопка переноса заказа (только если доступно)
            if can_reschedule:
                keyboard.append([InlineKeyboardButton(
                    "⏰ Перенести заказ",
                    callback_data=f"reschedule_{order_id}"
                )])

            keyboard.append([InlineKeyboardButton("◀️ Назад к заказам", callback_data="back_to_orders")])
            keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")])

            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.edit_text(order_info, reply_markup=reply_markup)

            return ORDER_ACTION

        if query.data == "back_to_orders":
            # Возвращаемся к списку заказов
            user_id = update.effective_user.id
            orders = Database.get_active_user_orders(user_id)

            if not orders:
                await query.message.edit_text("📋 У вас нет активных заказов.")
                return await WaterBot.start_after_callback(update, context)

            message = "📋 Ваши активные заказы:\n\n"
            keyboard = []

            for order in orders:
                delivery_dt = datetime.strptime(
                    f"{order['delivery_date']} {order['delivery_time']}",
                    '%Y-%m-%d %H:%M'
                )
                bottles = order.get('bottles', 1)

                message += (
                    f"📦 {order['order_id']}\n"
                    f"📅 {delivery_dt.strftime('%d.%m.%Y')} в {order['delivery_time']}\n"
                    f"💧 {bottles} бутыл{'ка' if bottles == 1 else 'ки' if bottles < 5 else 'ок'}\n"
                    f"📍 {order['address']}\n\n"
                )

                keyboard.append([InlineKeyboardButton(
                    f"🔧 Управление заказом {order['order_id']}",
                    callback_data=f"select_order_{order['order_id']}"
                )])

            keyboard.append([InlineKeyboardButton("◀️ Назад в меню", callback_data="back_to_menu")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.edit_text(message, reply_markup=reply_markup)

            return ORDER_ACTION

        if query.data.startswith("cancel_order_"):
            order_id = query.data.replace("cancel_order_", "")

            # Проверяем, можно ли отменить заказ (минимум 4 часа до доставки)
            order = Database.get_order_by_id(order_id)
            if order:
                delivery_dt = datetime.strptime(
                    f"{order['delivery_date']} {order['delivery_time']}",
                    '%Y-%m-%d %H:%M'
                )
                time_until_delivery = (delivery_dt - datetime.now()).total_seconds() / 3600  # в часах

                if time_until_delivery < 4:
                    await query.message.edit_text(
                        f"❌ Невозможно отменить заказ!\n\n"
                        f"До доставки осталось менее 4 часов.\n"
                        f"Отмена заказа возможна только за 4 часа до доставки.\n\n"
                        f"Пожалуйста, свяжитесь с нами напрямую, если необходимо изменить заказ."
                    )

                    # Возвращаемся к информации о заказе
                    keyboard = [[InlineKeyboardButton("◀️ Назад к заказу", callback_data=f"select_order_{order_id}")]]
                    keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")])
                    reply_markup = InlineKeyboardMarkup(keyboard)

                    await query.message.edit_text(
                        await query.message.text + "\n\nВыберите действие:",
                        reply_markup=reply_markup
                    )
                    return ORDER_ACTION

            # Подтверждение отмены
            keyboard = [
                [InlineKeyboardButton("✅ Да, отменить", callback_data=f"confirm_cancel_{order_id}")],
                [InlineKeyboardButton("❌ Нет, вернуться", callback_data=f"select_order_{order_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.message.edit_text(
                f"⚠️ Вы уверены, что хотите отменить заказ {order_id}?\n\n"
                f"Это действие нельзя отменить.",
                reply_markup=reply_markup
            )

            return ORDER_ACTION

        if query.data.startswith("confirm_cancel_"):
            order_id = query.data.replace("confirm_cancel_", "")

            # Отменяем напоминания для этого заказа
            cancelled_reminders = await ReminderScheduler.cancel_reminders_for_order(context, order_id)
            logger.info(f"Отменено {cancelled_reminders} напоминаний для заказа {order_id}")

            # Отменяем заказ
            success = Database.cancel_order(order_id)

            if success:
                await query.message.edit_text(
                    f"✅ Заказ {order_id} успешно отменен!\n\n"
                    f"Вы можете оформить новый заказ в любое время."
                )
            else:
                await query.message.edit_text(
                    f"❌ Не удалось отменить заказ {order_id}.\n"
                    f"Попробуйте позже или свяжитесь с поддержкой."
                )

            context.user_data.clear()
            return await WaterBot.start_after_callback(update, context)

        return ORDER_ACTION

    @staticmethod
    async def handle_reschedule_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка callback для переноса заказа"""
        query = update.callback_query
        await query.answer()

        if query.data.startswith("reschedule_"):
            order_id = query.data.replace("reschedule_", "")
            context.user_data['reschedule_order_id'] = order_id

            # Показываем выбор новой даты
            await query.message.edit_text(f"⏰ Перенос заказа {order_id}\n\nВыберите новую дату доставки:")
            return await WaterBot.show_reschedule_date_selection(update, context)

        return ORDER_ACTION

    @staticmethod
    async def show_reschedule_date_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать выбор даты для переноса заказа"""
        keyboard = []
        today = datetime.now()

        # Предлагаем следующие 7 дней
        for i in range(7):
            date = today + timedelta(days=i)
            date_str = date.strftime('%Y-%m-%d')

            if i == 0:
                button_text = f"Сегодня ({date.strftime('%d.%m')})"
            elif i == 1:
                button_text = f"Завтра ({date.strftime('%d.%m')})"
            else:
                button_text = date.strftime('%d.%m.%Y (%A)')

            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"reschedule_date_{date_str}")])

        keyboard.append([InlineKeyboardButton("❌ Отменить", callback_data="cancel")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            await update.callback_query.message.edit_text(
                "📅 Выберите новую дату доставки:",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                "📅 Выберите новую дату доставки:",
                reply_markup=reply_markup
            )

        return RESCHEDULE_DATE

    @staticmethod
    async def handle_reschedule_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора новой даты для переноса заказа"""
        query = update.callback_query
        await query.answer()

        if query.data == "cancel":
            await query.message.edit_text("❌ Перенос заказа отменен.")
            context.user_data.clear()
            return await WaterBot.start_after_callback(update, context)

        date_str = query.data.replace("reschedule_date_", "")
        context.user_data['new_delivery_date'] = date_str

        # Генерируем доступное время для новой даты
        return await WaterBot.show_reschedule_time_selection(update, context)

    @staticmethod
    async def show_reschedule_time_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать выбор времени для переноса заказа"""
        date_str = context.user_data['new_delivery_date']
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')

        keyboard = []
        current_time = datetime.now()
        min_hours_ahead = 4  # Минимум 4 часа до доставки

        # Генерируем слоты времени с интервалом 30 минут
        for hour in range(WORK_START_HOUR, WORK_END_HOUR):
            for minute in [0, 30]:
                time_slot = f"{hour:02d}:{minute:02d}"
                slot_datetime = datetime.strptime(f"{date_str} {time_slot}", '%Y-%m-%d %H:%M')

                # Проверяем, что время не в прошлом и не менее чем за 4 часа
                time_until_slot = (slot_datetime - current_time).total_seconds() / 3600  # в часах
                if time_until_slot < min_hours_ahead:
                    continue

                # Проверяем доступность слота - показываем только свободные
                if Database.is_time_slot_available(date_str, time_slot):
                    keyboard.append([InlineKeyboardButton(
                        f"⏰ {time_slot}",
                        callback_data=f"reschedule_time_{time_slot}"
                    )])

        # Если нет доступных слотов
        if not keyboard:
            keyboard.append([InlineKeyboardButton("❌ Нет свободных слотов", callback_data="no_slots")])

        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_to_reschedule_date")])
        keyboard.append([InlineKeyboardButton("❌ Отменить", callback_data="cancel")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        query = update.callback_query
        await query.message.edit_text(
            f"⏰ Выберите новое время доставки на {date_obj.strftime('%d.%m.%Y')}:\n"
            f"(Показаны только свободные слоты, доступные не менее чем за 4 часа)",
            reply_markup=reply_markup
        )

        return RESCHEDULE_TIME

    @staticmethod
    async def handle_reschedule_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора нового времени для переноса заказа"""
        query = update.callback_query
        await query.answer()

        if query.data == "cancel":
            await query.message.edit_text("❌ Перенос заказа отменен.")
            context.user_data.clear()
            return await WaterBot.start_after_callback(update, context)

        if query.data == "back_to_reschedule_date":
            return await WaterBot.show_reschedule_date_selection(update, context)

        if query.data == "no_slots":
            await query.answer("⚠️ На эту дату нет свободных слотов. Выберите другую дату.", show_alert=True)
            return await WaterBot.show_reschedule_date_selection(update, context)

        if query.data == "occupied":
            await query.answer("⚠️ Это время уже занято!", show_alert=True)
            return RESCHEDULE_TIME

        time_str = query.data.replace("reschedule_time_", "")

        # Проверяем доступность еще раз
        date_str = context.user_data['new_delivery_date']
        if not Database.is_time_slot_available(date_str, time_str):
            await query.answer("⚠️ К сожалению, это время уже занято!", show_alert=True)
            return await WaterBot.show_reschedule_time_selection(update, context)

        order_id = context.user_data.get('reschedule_order_id')

        # Получаем данные заказа для новых напоминаний
        order = Database.get_order_by_id(order_id)
        user_id = update.effective_user.id

        # Отменяем старые напоминания
        cancelled_reminders = await ReminderScheduler.cancel_reminders_for_order(context, order_id)
        logger.info(f"Отменено {cancelled_reminders} старых напоминаний для заказа {order_id}")

        # Обновляем заказ с новой датой и временем
        success = Database.update_order_schedule(order_id, date_str, time_str)

        if success:
            # Создаем новые напоминания для перенесенного заказа
            reminders = await ReminderScheduler.schedule_reminders(
                context,
                user_id,
                order_id,
                date_str,
                time_str,
                order['address']
            )

            # Сохраняем новые ID запланированных сообщений
            if reminders:
                morning_msg_id = reminders['morning'].get('message_id')
                pre_delivery_msg_id = reminders['pre_delivery'].get('message_id')
                Database.update_order_reminder_ids(order_id, morning_msg_id, pre_delivery_msg_id)
                logger.info(f"Сохранены новые ID напоминаний для перенесенного заказа {order_id}")

            logger.info(f"Запланированы новые напоминания для перенесенного заказа {order_id}")

            await query.message.edit_text(
                f"✅ Заказ успешно перенесен!\n\n"
                f"📅 Новая дата: {date_str}\n"
                f"⏰ Новое время: {time_str}\n\n"
                f"🔔 Вы получите обновленные напоминания:\n"
                f"• В 8:00 утра в день доставки\n"
                f"• За 30 минут до доставки"
            )
        else:
            await query.message.edit_text(
                f"❌ Не удалось перенести заказ. Попробуйте позже или свяжитесь с поддержкой."
            )

        context.user_data.clear()
        return await WaterBot.start_after_callback(update, context)

    # Изменение данных пользователя
    @staticmethod
    async def edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Изменение имени пользователя"""
        user_id = update.effective_user.id
        new_name = update.message.text

        # Обновляем имя в базе данных
        Database.update_user_name(user_id, new_name)

        await update.message.reply_text(
            "✅ Имя успешно изменено!\n\n"
            "Что вы хотите сделать дальше?",
            reply_markup=ReplyKeyboardRemove()
        )

        return await WaterBot.show_edit_menu(update, context)

    @staticmethod
    async def edit_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Изменение номера телефона пользователя"""
        user_id = update.effective_user.id
        new_phone = update.message.text

        # Валидация номера телефона
        if not validate_kyrgyzstan_phone(new_phone):
            await update.message.reply_text(
                "❌ Неверный формат номера телефона. Пожалуйста, введите номер в формате +996 700 123 456."
            )
            return EDIT_PHONE

        # Обновляем телефон в базе данных
        Database.update_user_phone(user_id, new_phone)

        await update.message.reply_text(
            "✅ Номер телефона успешно изменен!\n\n"
            "Что вы хотите сделать дальше?",
            reply_markup=ReplyKeyboardRemove()
        )

        return await WaterBot.show_edit_menu(update, context)

    @staticmethod
    async def edit_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Изменение адреса пользователя"""
        user_id = update.effective_user.id
        new_address = update.message.text

        # Обновляем адрес в базе данных
        Database.update_user_address(user_id, new_address)

        await update.message.reply_text(
            "✅ Адрес доставки успешно изменен!\n\n"
            "Что вы хотите сделать дальше?",
            reply_markup=ReplyKeyboardRemove()
        )

        return await WaterBot.show_edit_menu(update, context)

    @staticmethod
    async def show_edit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать меню редактирования данных"""
        user_id = update.effective_user.id
        user = Database.get_user(user_id)

        keyboard = [
            ['✏️ Изменить имя'],
            ['📱 Изменить телефон'],
            ['📍 Изменить адрес'],
            ['◀️ Назад']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            "Выберите, что вы хотите изменить:",
            reply_markup=reply_markup
        )

        return CHOOSING_ACTION

    @staticmethod
    async def handle_edit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора действия в меню редактирования"""
        text = update.message.text

        if text == '✏️ Изменить имя':
            await update.message.reply_text(
                "Введите новое имя:"
            )
            return EDIT_NAME

        elif text == '📱 Изменить телефон':
            await update.message.reply_text(
                "Введите новый номер телефона в формате:\n"
                "+996 700 123 456 или 0700123456"
            )
            return EDIT_PHONE

        elif text == '📍 Изменить адрес':
            await update.message.reply_text(
                "Введите новый адрес доставки:"
            )
            return EDIT_ADDRESS

        elif text == '◀️ Назад':
            return await WaterBot.start(update, context)

        return CHOOSING_ACTION

    # Тестовая команда для проверки адресов
    @staticmethod
    async def test_address_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /address для тестирования валидации адресов"""
        # Проверяем, передан ли адрес в команде
        if context.args and len(context.args) > 0:
            # Объединяем все аргументы в один адрес
            address = " ".join(context.args)

            await update.message.reply_text(
                "🔍 Проверяю адрес...\nПожалуйста, подождите..."
            )

            # Запускаем валидацию
            result = await test_address_validation(address)

            await update.message.reply_text(result)
        else:
            # Если адрес не передан, показываем инструкцию
            help_text = (
                "📍 **Тестирование валидации адресов**\n\n"
                "Использование:\n"
                "`/address <адрес>`\n\n"
                "Примеры:\n"
                "• `/address Бишкек, Ленинский район, ул. Исанова 42`\n"
                "• `/address Бишкек, мкр Асанбай, 12/3`\n"
                "• `/address Ош, ул. Ленина 25`\n\n"
                "Модуль проверит:\n"
                "✅ Находится ли адрес в Кыргызстане\n"
                "✅ Определит город\n"
                "✅ Определит район (если возможно)\n"
                "✅ Получит координаты (если доступен Google API)\n\n"
                "💡 Для работы с Google Maps API добавьте в .env:\n"
                "`GOOGLE_MAPS_API_KEY=ваш_ключ`"
            )

            await update.message.reply_text(
                help_text,
                parse_mode='Markdown'
            )
def main():
    """Запуск бота"""
    if not TELEGRAM_BOT_TOKEN:
        print("⚠️ Ошибка: не указан TELEGRAM_BOT_TOKEN в файле .env")
        print("Создайте файл .env на основе .env.example и добавьте токен бота")
        return

    # Инициализация бота
    bot = WaterBot()

    # Создание приложения
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Добавляем обработчик команды /start (вне ConversationHandler для перезапуска)
    application.add_handler(CommandHandler('start', WaterBot.start))

    # Добавляем команду для тестирования валидации адресов
    application.add_handler(CommandHandler('address', WaterBot.test_address_command))

    # Создание ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, WaterBot.handle_main_menu)],
        states={
            CHOOSING_ACTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, WaterBot.handle_main_menu),
            ],
            REGISTRATION_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, WaterBot.registration_name)
            ],
            REGISTRATION_PHONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, WaterBot.registration_phone)
            ],
            REGISTRATION_ADDRESS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, WaterBot.registration_address)
            ],
            ORDER_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, WaterBot.order_name)
            ],
            ORDER_PHONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, WaterBot.order_phone)
            ],
            ORDER_ADDRESS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, WaterBot.order_address)
            ],
            ORDER_BOTTLES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, WaterBot.order_bottles)
            ],
            ORDER_DATE: [
                CallbackQueryHandler(WaterBot.handle_date_selection)
            ],
            ORDER_TIME: [
                CallbackQueryHandler(WaterBot.handle_time_selection)
            ],
            ORDER_ACTION: [
                CallbackQueryHandler(WaterBot.handle_order_selection),
                CallbackQueryHandler(WaterBot.handle_reschedule_callback)
            ],
            RESCHEDULE_DATE: [
                CallbackQueryHandler(WaterBot.handle_reschedule_date)
            ],
            RESCHEDULE_TIME: [
                CallbackQueryHandler(WaterBot.handle_reschedule_time)
            ],
            EDIT_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, WaterBot.edit_name)
            ],
            EDIT_PHONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, WaterBot.edit_phone)
            ],
            EDIT_ADDRESS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, WaterBot.edit_address)
            ],
        },
        fallbacks=[CommandHandler('cancel', WaterBot.cancel)],
    )

    application.add_handler(conv_handler)

    # Запуск бота
    print("🤖 Бот запущен и готов к работе!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
