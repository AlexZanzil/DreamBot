import asyncio
import logging
from aiogram import Bot
from bot.database import Database
from bot.config import DB_PATH, GROUP_CHAT_ID, TOPIC_ID
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.base import JobLookupError
from datetime import datetime, timedelta, date
from bot.services.holidays import WorkdayChecker

workday_checker = WorkdayChecker()

async def send_lunch_reminder(chat_id: int, message_text: str, bot):
    try:
        # Проверяем, рабочий ли сегодня день
        if not workday_checker.is_workday():
            holiday_name = workday_checker.get_holiday_name()
            if holiday_name:
                logging.info(f"Сегодня праздник ({holiday_name}), уведомление пользователю {chat_id} не отправлено")
            else:
                logging.info(f"Сегодня выходной день, уведомление пользователю {chat_id} не отправлено")
            return

        await bot.send_message(chat_id, message_text)
        logging.info(f"Отправлено уведомление пользователю (ID: {chat_id}): {message_text}")
    except Exception as e:
        logging.error(f"Ошибка при отправке уведомления пользователю {chat_id}: {e}")

class LunchScheduler:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.db = Database(DB_PATH)
        self.workday_checker = WorkdayChecker()
        self.is_running = False
        self.current_schedule_hash = None

    async def start(self):
        """Запуск планировщика"""
        self.is_running = True

        # Отправляем расписание при запуске, если его еще нет
        await self._check_and_send_daily_schedule()

        # Запускаем основной цикл планировщика
        await self._scheduler_loop()

    async def stop(self):
        """Остановка планировщика"""
        self.is_running = False

    async def cleanup_on_shutdown(self):
        """Очистка при остановке бота"""
        try:
            await self._unpin_and_delete_old_message()
            logging.info("Выполнена очистка при остановке бота")
        except Exception as e:
            logging.error(f"Ошибка при очистке при остановке бота: {e}")

    async def _scheduler_loop(self):
        """Основной цикл планировщика с точной синхронизацией"""
        while self.is_running:
            try:
                # Получаем текущее время
                current_datetime = datetime.now()

                # Округляем до ближайшей минуты для точности
                current_datetime = current_datetime.replace(second=0, microsecond=0)
                current_time = current_datetime.strftime("%H:%M")

                # Время через 5 минут
                time_in_5_min = (current_datetime + timedelta(minutes=5)).strftime("%H:%M")

                # Проверяем, нужно ли обновить ежедневное расписание в 8:00
                if current_datetime.hour == 8 and current_datetime.minute == 0:
                    if self.workday_checker.is_workday():
                        await self._update_daily_schedule()

                # Проверяем изменения в расписании каждую минуту
                await self._check_schedule_changes()

                # 1. ОСНОВНЫЕ НАПОМИНАНИЯ (время обеда СЕЙЧАС)
                users_now = self.db.get_users_by_lunch_time_with_notifications(current_time)
                if users_now:
                    for user in users_now:
                        user_id, username, first_name, last_name = user
                        display_name = first_name or username or f"ID{user_id}"
                        message_text = f"🍽️ Время обеда! ({current_time})\n\nПриятного аппетита, {display_name}! 😊\nНе забудь выйти из КЦ!"
                        await send_lunch_reminder(user_id, message_text, self.bot)

                # 2. ПРЕДВАРИТЕЛЬНЫЕ НАПОМИНАНИЯ (обед через 5 минут)
                users_in_5_min = self.db.get_users_by_lunch_time_with_notifications(time_in_5_min)
                if users_in_5_min:
                    for user in users_in_5_min:
                        user_id, username, first_name, last_name = user
                        display_name = first_name or username or f"ID{user_id}"
                        message_text = f"⏰ До обеда осталось 5 минут!\n\nВремя обеда: {time_in_5_min} 🍽️"
                        await send_lunch_reminder(user_id, message_text, self.bot)

                # 🎯 ТОЧНАЯ СИНХРОНИЗАЦИЯ: спим до начала следующей минуты
                now = datetime.now()
                next_minute = (now.replace(second=0, microsecond=0) + timedelta(minutes=1))
                sleep_seconds = (next_minute - now).total_seconds()

                # Минимальная задержка 1 секунда для предотвращения гонки
                if sleep_seconds < 1:
                    sleep_seconds = 1

                await asyncio.sleep(sleep_seconds)

            except Exception as e:
                logging.error(f"Ошибка в цикле планировщика: {e}")
                # При ошибке спим 60 секунд и пытаемся снова
                await asyncio.sleep(60)

    async def _check_and_send_daily_schedule(self):
        """Проверка и отправка ежедневного расписания при необходимости"""
        today = date.today().strftime("%Y-%m-%d")
        pinned_info = self.db.get_pinned_message()

        # Если сообщения нет или оно от другого дня, создаем новое
        if not pinned_info or pinned_info[1] != today:
            if self.workday_checker.is_workday():
                await self._create_daily_schedule()

    async def _update_daily_schedule(self):
        """Обновление ежедневного расписания в 8:00"""
        # Открепляем и удаляем старое сообщение
        await self._unpin_and_delete_old_message()

        # Создаем новое расписание
        await self._create_daily_schedule()

    async def _create_daily_schedule(self):
        """Создание нового ежедневного расписания"""
        try:
            # Проверяем, что настройки группового чата заданы
            if not GROUP_CHAT_ID or not TOPIC_ID:
                logging.warning("GROUP_CHAT_ID или TOPIC_ID не настроены, пропускаем отправку группового расписания")
                return

            schedule_text = self._generate_schedule_text()
            today = date.today().strftime("%Y-%m-%d")

            # Отправляем сообщение в групповой чат
            message = await self.bot.send_message(
                chat_id=GROUP_CHAT_ID,
                message_thread_id=TOPIC_ID,
                text=schedule_text,
                parse_mode='HTML'
            )

            # Закрепляем сообщение
            await self.bot.pin_chat_message(
                chat_id=GROUP_CHAT_ID,
                message_id=message.message_id,
                disable_notification=True
            )

            # Сохраняем информацию о сообщении
            self.db.set_pinned_message(message.message_id, today)
            self.current_schedule_hash = self._get_schedule_hash()

            logging.info(f"Создано и закреплено новое расписание обедов (ID: {message.message_id})")

        except Exception as e:
            logging.error(f"Ошибка при создании ежедневного расписания: {e}")

    async def _check_schedule_changes(self):
        """Проверка изменений в расписании"""
        try:
            current_hash = self._get_schedule_hash()

            # Если расписание изменилось, обновляем сообщение
            if current_hash != self.current_schedule_hash:
                await self._update_pinned_message()
                self.current_schedule_hash = current_hash

        except Exception as e:
            logging.error(f"Ошибка при проверке изменений расписания: {e}")

    async def _update_pinned_message(self):
        """Обновление закрепленного сообщения"""
        try:
            # Проверяем, что настройки группового чата заданы
            if not GROUP_CHAT_ID or not TOPIC_ID:
                return

            pinned_info = self.db.get_pinned_message()
            if not pinned_info:
                return

            message_id, _ = pinned_info
            schedule_text = self._generate_schedule_text()

            # Обновляем текст сообщения
            await self.bot.edit_message_text(
                chat_id=GROUP_CHAT_ID,
                message_id=message_id,
                text=schedule_text,
                parse_mode='HTML'
            )

            logging.info("Расписание обедов обновлено")

        except Exception as e:
            logging.error(f"Ошибка при обновлении закрепленного сообщения: {e}")

    async def _unpin_and_delete_old_message(self):
        """Открепление и удаление старого сообщения"""
        try:
            # Проверяем, что настройки группового чата заданы
            if not GROUP_CHAT_ID:
                return

            pinned_info = self.db.get_pinned_message()
            if not pinned_info:
                return

            message_id, _ = pinned_info

            # Открепляем сообщение
            await self.bot.unpin_chat_message(
                chat_id=GROUP_CHAT_ID,
                message_id=message_id
            )

            # Удаляем сообщение
            await self.bot.delete_message(
                chat_id=GROUP_CHAT_ID,
                message_id=message_id
            )

            # Очищаем запись в базе данных
            self.db.clear_pinned_message()

            logging.info(f"Старое расписание откреплено и удалено (ID: {message_id})")

        except Exception as e:
            logging.error(f"Ошибка при удалении старого сообщения: {e}")

    @staticmethod
    def _format_display_name(username, first_name, last_name):
        """Форматирование отображаемого имени пользователя"""
        # Приоритет: Имя + Фамилия > Имя > Username > user_id
        if first_name and last_name:
            return f"{first_name} {last_name}"
        elif first_name:
            return first_name
        elif username:
            return f"@{username}"
        else:
            return "Пользователь"

    def _generate_schedule_text(self):
        """Генерация текста расписания"""
        schedules = self.db.get_all_lunch_schedules()

        if not schedules:
            return "📅 <b>Расписание обедов на сегодня</b>\n\n❌ Пока никто не записался на обед"

        text = "📅 <b>Расписание обедов на сегодня</b>\n\n"

        for user_id, username, first_name, last_name, lunch_time in schedules:
            # Форматируем имя пользователя
            display_name = self._format_display_name(username, first_name, last_name)
            text += f"🕐 <b>{lunch_time}</b> - {display_name}\n"

        text += f"\n<i>Последнее обновление: {datetime.now().strftime('%H:%M')}</i>"

        return text

    def _get_schedule_hash(self):
        """Получение хеша текущего расписания для отслеживания изменений"""
        schedules = self.db.get_all_lunch_schedules()
        return hash(str(schedules))

# Глобальный планировщик для других задач
scheduler = None


def init_scheduler(bot):
    """
    Инициализация планировщика задач
    """
    global scheduler
    scheduler = AsyncIOScheduler()

    return scheduler


def stop_scheduler(scheduler_instance=None):
    """
    Остановка всех задач и самого планировщика
    """
    global scheduler
    sch = scheduler_instance or scheduler
    if sch:
        try:
            sch.shutdown(wait=False)
        except JobLookupError as e:
            print(f"Ошибка при остановке планировщика: {e}")
            logging.error(f"Ошибка при остановке планировщика: {e}")