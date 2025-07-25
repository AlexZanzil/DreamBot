from aiogram import types, Dispatcher
from aiogram.filters import Command
from bot.handlers.lunch import cmd_remove, cmd_notifications, cmd_lunch

# Обработчик команды /start
async def cmd_start(message: types.Message):
    await message.answer("Привет! Я бот для управления расписанием обедов. "
                         "Используйте /help для получения списка команд.")

# Обработчик команды /help
async def cmd_help(message: types.Message):
    help_text = """
🍽 **Доступные команды:**

/start - Начать работу с ботом
/help - Показать список команд
/lunch - Показать ваше текущее время обеда
/lunch ЧЧ:ММ - Установить время обеда (например: /lunch 13:30)
/notifications - Включить/выключить уведомления
/remove - Удалить себя из расписания

📅 **Особенности работы:**
• Уведомления приходят только в рабочие дни (пн-пт)
• В праздничные дни уведомления не отправляются
• Вы получите напоминание за 5 минут до обеда и в момент обеда
"""
    await message.answer(help_text, parse_mode="Markdown")

# Функция регистрации обработчиков
def register_common_handlers(dp: Dispatcher):
    dp.message.register(cmd_start, Command(commands=["start"]))
    dp.message.register(cmd_help, Command(commands=["help"]))
    dp.message.register(cmd_notifications, Command("notifications"))
    dp.message.register(cmd_lunch, Command("lunch"))
    dp.message.register(cmd_remove, Command("remove"))
