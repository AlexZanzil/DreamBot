import re
from aiogram import types, Dispatcher
from aiogram.filters import Command
from bot.database import Database
from bot.config import DB_PATH
from datetime import datetime, timedelta
import logging

# Инициализация базы данных
db = Database(DB_PATH)

# Регулярное выражение для проверки формата времени
TIME_PATTERN = r'^([01]?[0-9]|2[0-3]):([0-5][0-9])$'

def _format_display_name(username, first_name, last_name):
    """Форматирование отображаемого имени пользователя"""
    # Приоритет: Имя + Фамилия > Имя > Username > "Пользователь"
    if first_name and last_name:
        return f"{first_name} {last_name}"
    elif first_name:
        return first_name
    elif username:
        return f"@{username}"
    else:
        return "Пользователь"

def _check_time_until_lunch(time_str):
    """Проверяет, сколько времени осталось до обеда сегодня"""
    try:
        now = datetime.now()
        lunch_hour, lunch_minute = map(int, time_str.split(':'))

        # Время обеда сегодня
        lunch_time_today = now.replace(
            hour=lunch_hour,
            minute=lunch_minute,
            second=0,
            microsecond=0
        )

        # Если время обеда уже прошло сегодня, возвращаем None
        if lunch_time_today <= now:
            return None

        # Возвращаем разность во времени
        return lunch_time_today - now

    except Exception as e:
        logging.error(f"Ошибка при проверке времени до обеда: {e}")
        return None

# Обработчик команды /lunch
async def cmd_lunch(message: types.Message):
    args = message.text.split()
    user_id = message.from_user.id
    bot = message.bot

    if len(args) == 1:
        # Если команда без аргументов, показываем текущее время обеда
        lunch_time = db.get_lunch_time(user_id)
        if lunch_time:
            await bot.send_message(user_id, f"Ваше текущее время обеда: {lunch_time}")
        else:
            await bot.send_message(user_id, "У вас еще не установлено время обеда. Используйте команду /lunch ЧЧ:ММ для установки.")
        return

    # Проверяем формат времени
    time_str = args[1]
    if not re.match(TIME_PATTERN, time_str):
        await bot.send_message(user_id, "Неверный формат времени. Используйте формат ЧЧ:ММ, например: /lunch 13:30")
        return

    # Получаем информацию о пользователе
    username = message.from_user.username
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""

    # Сохраняем время обеда с полной информацией о пользователе
    db.set_lunch_time(user_id, username, first_name, last_name, time_str)

    # Форматируем имя для ответа
    display_name = _format_display_name(username, first_name, last_name)

    # Проверяем, сколько времени осталось до обеда сегодня
    time_until_lunch = _check_time_until_lunch(time_str)

    if time_until_lunch is None:
        # Время обеда уже прошло сегодня
        await bot.send_message(
            user_id,
            f"✅ Время обеда установлено на {time_str}\n"
            f"Уведомления придут на следующий рабочий день"
        )

    elif time_until_lunch.total_seconds() <= 300:  # Меньше 5 минут
        total_seconds = int(time_until_lunch.total_seconds())
        minutes = total_seconds // 60
        seconds = total_seconds % 60

        if minutes > 0:
            time_str_left = f"{minutes} мин. {seconds} сек."
        else:
            time_str_left = f"{seconds} сек."

        await bot.send_message(
            user_id,
            f"✅ Время обеда установлено на {time_str}\n\n"
            f"⏰ До обеда осталось {time_str_left}!\n"
        )
    else:
        # Обычная ситуация - до обеда больше 5 минут
        hours_left = int(time_until_lunch.total_seconds() // 3600)
        minutes_left = int((time_until_lunch.total_seconds() % 3600) // 60)

        time_left_str = ""
        if hours_left > 0:
            time_left_str = f"{hours_left} ч. {minutes_left} мин."
        else:
            time_left_str = f"{minutes_left} мин."

        await bot.send_message(
            user_id,
            f"✅ Время обеда установлено на {time_str}\n\n"
            f"⏰ До обеда сегодня: {time_left_str}\n"
            f"🔄 Изменения вступят в силу автоматически."
        )

    logging.info(f"Пользователь {user_id} ({display_name}) установил время обеда: {time_str}")

# Команда /notifications
async def cmd_notifications(message: types.Message):
    """Команда для включения/выключения уведомлений"""
    user_id = message.from_user.id
    bot = message.bot  # 🆕 Получаем bot
    lunch_time, notifications_enabled = db.get_user_lunch_time_with_notifications(user_id)

    if lunch_time is None:
        await bot.send_message(user_id, "❌ Вы не зарегистрированы в расписании. Используйте /lunch ЧЧ:ММ для установки времени обеда.")
        return

    # Переключаем уведомления
    if db.toggle_notifications(user_id):
        new_status = not notifications_enabled
        status_text = "включены ✅" if new_status else "выключены ❌"
        await bot.send_message(user_id, f"🔔 Уведомления {status_text}")

        if new_status:
            await bot.send_message(user_id, "Теперь вы будете получать напоминания о времени обеда.")
        else:
            await bot.send_message(user_id, "Вы больше не будете получать напоминания о времени обеда.")
    else:
        await bot.send_message(user_id, "❌ Ошибка при изменении настроек уведомлений.")

# Команда /remove
async def cmd_remove(message: types.Message):
    """Команда для удаления себя из расписания"""
    user_id = message.from_user.id
    bot = message.bot  # 🆕 Получаем bot
    lunch_time, _ = db.get_user_lunch_time_with_notifications(user_id)

    if lunch_time is None:
        await bot.send_message(user_id, "❌ Вы не зарегистрированы в расписании обедов.")
        return

    if db.remove_user_from_schedule(user_id):
        await bot.send_message(user_id, "✅ Вы успешно удалены из расписания обедов.\n"
                                        "Используйте /lunch ЧЧ:ММ для возвращения.")
    else:
        await bot.send_message(user_id, "❌ Ошибка при удалении из расписания.")

# Функция регистрации обработчиков
def register_lunch_handlers(dp: Dispatcher):
    """Регистрация обработчиков команд обеда"""
    dp.message.register(cmd_lunch, Command(commands=["lunch"]))
    logging.info("✅ Обработчики команд обеда зарегистрированы")