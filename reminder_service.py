from datetime import datetime, timedelta
import logging
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


class ReminderScheduler:
    """Напоминания о доставке через JobQueue из python-telegram-bot.

    Bot API не умеет отправлять отложенные сообщения (параметра schedule_date у
    send_message нет), поэтому напоминания ставятся задачами в JobQueue.
    Вместо message_id в таблицу заказов пишется имя задачи — по нему её можно снять
    при отмене или переносе. Задачи живут в памяти процесса: после перезапуска бота
    напоминания для уже созданных заказов не восстанавливаются.
    """

    @staticmethod
    async def _send_reminder(context):
        job = context.job
        try:
            await context.bot.send_message(chat_id=job.chat_id, text=job.data)
        except TelegramError as e:
            logger.error(f"Не удалось отправить напоминание {job.name}: {e}")

    @staticmethod
    def _schedule(context, name, when, chat_id, text):
        """Ставит одну задачу; возвращает её имя или None, если время уже прошло."""
        if when <= datetime.now():
            return None
        context.job_queue.run_once(
            ReminderScheduler._send_reminder, when=when, chat_id=chat_id, name=name, data=text
        )
        logger.info(f"Напоминание {name} запланировано на {when}")
        return name

    @staticmethod
    async def schedule_reminders(context, chat_id, order_id, delivery_date_str, delivery_time_str, address):
        """
        Запланировать два напоминания: в 8:00 в день доставки и за 30 минут до неё.

        :return: Dict с информацией о напоминаниях или None при ошибке
        """
        try:
            delivery_datetime = datetime.strptime(f"{delivery_date_str} {delivery_time_str}", '%Y-%m-%d %H:%M')
            morning_time = delivery_datetime.replace(hour=8, minute=0)
            pre_delivery_time = delivery_datetime - timedelta(minutes=30)

            morning_text = (
                f"🌅 Доброе утро!\n\n"
                f"Напоминаем, что сегодня в {delivery_time_str} к вам приедет доставка воды.\n\n"
                f"📋 Заказ: {order_id}\n"
                f"📍 Адрес: {address}"
            )
            pre_delivery_text = (
                f"⏰ Напоминание!\n\n"
                f"Через 30 минут (в {delivery_time_str}) к вам приедет доставка воды.\n\n"
                f"📋 Заказ: {order_id}\n"
                f"📍 Адрес: {address}\n\n"
                f"Пожалуйста, будьте готовы принять доставку! 👍"
            )

            morning_job = ReminderScheduler._schedule(context, f"{order_id}:morning", morning_time, chat_id, morning_text)
            pre_delivery_job = ReminderScheduler._schedule(context, f"{order_id}:pre_delivery", pre_delivery_time, chat_id, pre_delivery_text)

            return {
                'morning': {'scheduled': morning_job is not None, 'time': morning_time, 'message_id': morning_job},
                'pre_delivery': {'scheduled': pre_delivery_job is not None, 'time': pre_delivery_time, 'message_id': pre_delivery_job},
            }
        except Exception as e:
            logger.error(f"Ошибка планирования напоминаний для заказа {order_id}: {e}")
            return None

    @staticmethod
    async def cancel_reminders_for_order(context, order_id):
        """Снять все напоминания заказа. Возвращает количество снятых задач."""
        cancelled = 0
        for name in (f"{order_id}:morning", f"{order_id}:pre_delivery"):
            for job in context.job_queue.get_jobs_by_name(name):
                job.schedule_removal()
                cancelled += 1
        logger.info(f"Отменено {cancelled} напоминаний для заказа {order_id}")
        return cancelled

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
