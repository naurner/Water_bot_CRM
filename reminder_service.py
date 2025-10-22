from datetime import datetime, timedelta
import logging
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


class ReminderScheduler:
    """Планировщик напоминаний через Telegram Scheduled Messages API"""

    @staticmethod
    async def schedule_reminders(context, chat_id, order_id, delivery_date_str, delivery_time_str, address):
        """
        Запланировать напоминания для заказа через Telegram Scheduled Messages

        :param context: Context приложения с bot
        :param chat_id: ID чата пользователя
        :param order_id: ID заказа
        :param delivery_date_str: Дата доставки в формате YYYY-MM-DD
        :param delivery_time_str: Время доставки в формате HH:MM
        :param address: Адрес доставки
        :return: Dict с информацией о запланированных напоминаниях или None при ошибке
        """
        try:
            delivery_datetime = datetime.strptime(
                f"{delivery_date_str} {delivery_time_str}",
                '%Y-%m-%d %H:%M'
            )

            # Утреннее напоминание в 8:00 дня доставки
            morning_reminder_time = datetime.strptime(
                f"{delivery_date_str} 08:00",
                '%Y-%m-%d %H:%M'
            )

            # Напоминание за 30 минут до доставки
            pre_delivery_reminder_time = delivery_datetime - timedelta(minutes=30)

            # Текущее время
            now = datetime.now()

            # Планируем утреннее напоминание, если время еще не прошло
            morning_scheduled = False
            morning_message_id = None
            if morning_reminder_time > now:
                morning_text = (
                    f"🌅 Доброе утро!\n\n"
                    f"Напоминаем, что сегодня в {delivery_time_str} "
                    f"к вам приедет доставка воды.\n\n"
                    f"📋 Заказ: {order_id}\n"
                    f"📍 Адрес: {address}"
                )

                try:
                    # Преобразуем в Unix timestamp
                    schedule_timestamp = int(morning_reminder_time.timestamp())

                    # Отправляем отложенное сообщение через Telegram API
                    message = await context.bot.send_message(
                        chat_id=chat_id,
                        text=morning_text,
                        schedule_date=schedule_timestamp
                    )
                    morning_message_id = message.message_id
                    morning_scheduled = True

                    logger.info(f"Утреннее напоминание запланировано на {morning_reminder_time} (message_id: {morning_message_id}) для заказа {order_id}")
                except TelegramError as e:
                    logger.error(f"Ошибка планирования утреннего напоминания: {e}")
                except Exception as e:
                    logger.error(f"Неожиданная ошибка при планировании утреннего напоминания: {e}")

            # Планируем напоминание за 30 минут, если время еще не прошло
            pre_delivery_scheduled = False
            pre_delivery_message_id = None
            if pre_delivery_reminder_time > now:
                pre_delivery_text = (
                    f"⏰ Напоминание!\n\n"
                    f"Через 30 минут (в {delivery_time_str}) "
                    f"к вам приедет доставка воды.\n\n"
                    f"📋 Заказ: {order_id}\n"
                    f"📍 Адрес: {address}\n\n"
                    f"Пожалуйста, будьте готовы принять доставку! 👍"
                )

                try:
                    # Преобразуем в Unix timestamp
                    schedule_timestamp = int(pre_delivery_reminder_time.timestamp())

                    # Отправляем отложенное сообщение через Telegram API
                    message = await context.bot.send_message(
                        chat_id=chat_id,
                        text=pre_delivery_text,
                        schedule_date=schedule_timestamp
                    )
                    pre_delivery_message_id = message.message_id
                    pre_delivery_scheduled = True

                    logger.info(f"Напоминание за 30 минут запланировано на {pre_delivery_reminder_time} (message_id: {pre_delivery_message_id}) для заказа {order_id}")
                except TelegramError as e:
                    logger.error(f"Ошибка планирования напоминания за 30 минут: {e}")
                except Exception as e:
                    logger.error(f"Неожиданная ошибка при планировании напоминания за 30 минут: {e}")

            return {
                'morning': {
                    'scheduled': morning_scheduled,
                    'time': morning_reminder_time,
                    'message_id': morning_message_id
                },
                'pre_delivery': {
                    'scheduled': pre_delivery_scheduled,
                    'time': pre_delivery_reminder_time,
                    'message_id': pre_delivery_message_id
                }
            }

        except Exception as e:
            logger.error(f"Ошибка планирования напоминаний для заказа {order_id}: {e}")
            return None

    @staticmethod
    async def cancel_scheduled_messages(context, chat_id, message_ids):
        """
        Отменить запланированные сообщения в Telegram

        :param context: Context приложения с bot
        :param chat_id: ID чата
        :param message_ids: Список ID сообщений для отмены
        :return: Количество отмененных сообщений
        """
        if not message_ids:
            return 0

        cancelled_count = 0

        try:
            for message_id in message_ids:
                if message_id:
                    try:
                        await context.bot.delete_message(
                            chat_id=chat_id,
                            message_id=message_id
                        )
                        cancelled_count += 1
                        logger.info(f"Отменено запланированное сообщение: {message_id}")
                    except TelegramError as e:
                        logger.warning(f"Не удалось отменить сообщение {message_id}: {e}")
                    except Exception as e:
                        logger.error(f"Ошибка при отмене сообщения {message_id}: {e}")

            return cancelled_count

        except Exception as e:
            logger.error(f"Ошибка отмены запланированных сообщений: {e}")
            return cancelled_count

    @staticmethod
    async def cancel_reminders_for_order(context, order_id):
        """
        Отменить все напоминания для заказа по ID заказа

        :param context: Context приложения с bot
        :param order_id: ID заказа
        :return: Количество отмененных напоминаний
        """
        from database import Database

        try:
            # Получаем заказ из базы данных
            order = Database.get_order_by_id(order_id)
            if not order:
                logger.warning(f"Заказ {order_id} не найден")
                return 0

            # Получаем ID сообщений
            morning_msg_id = order.get('morning_reminder_id')
            pre_delivery_msg_id = order.get('pre_delivery_reminder_id')

            # Собираем список ID для отмены
            message_ids = []
            if morning_msg_id:
                message_ids.append(morning_msg_id)
            if pre_delivery_msg_id:
                message_ids.append(pre_delivery_msg_id)

            if not message_ids:
                logger.info(f"Нет запланированных сообщений для заказа {order_id}")
                return 0

            # Отменяем сообщения
            chat_id = order.get('user_id')
            cancelled_count = await ReminderScheduler.cancel_scheduled_messages(
                context, chat_id, message_ids
            )

            logger.info(f"Отменено {cancelled_count} напоминаний для заказа {order_id}")
            return cancelled_count

        except Exception as e:
            logger.error(f"Ошибка при отмене напоминаний для заказа {order_id}: {e}")
            return 0

    @staticmethod
    def can_reschedule(delivery_date_str, delivery_time_str, min_hours=4):
        """
        Проверить, можно ли перенести заказ (не позже чем за N часов)

        :param delivery_date_str: Дата доставки в формате YYYY-MM-DD
        :param delivery_time_str: Время доставки в формате HH:MM
        :param min_hours: Минимальное количество часов до доставки
        :return: True если можно перенести, False если нет
        """
        try:
            delivery_datetime = datetime.strptime(
                f"{delivery_date_str} {delivery_time_str}",
                '%Y-%m-%d %H:%M'
            )

            time_until_delivery = (delivery_datetime - datetime.now()).total_seconds() / 3600

            return time_until_delivery >= min_hours

        except Exception as e:
            logger.error(f"Ошибка проверки возможности переноса: {e}")
            return False
