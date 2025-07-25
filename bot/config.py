import os
from dotenv import load_dotenv

# Загрузка переменных окружения из файла .env
load_dotenv()

# Токен вашего бота
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("Не найдены переменные окружения TOKEN")

GROUP_CHAT_ID = os.getenv('GROUP_CHAT_ID')  # ID группового чата
TOPIC_ID = os.getenv('TOPIC_ID')  # ID темы в групповом чате

# Путь к файлу базы данных
DB_PATH = os.getenv("DB_PATH", "lunch_bot.db")
