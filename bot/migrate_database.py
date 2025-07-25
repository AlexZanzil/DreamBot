import sqlite3
import os
from bot.config import DB_PATH

def migrate_database():
    """Миграция базы данных для добавления новых полей"""
    print("Начинаем миграцию базы данных...")

    # Подключаемся к базе данных
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    try:
        # Проверяем, существуют ли уже новые колонки
        cursor.execute("PRAGMA table_info(lunch_schedule)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'first_name' not in columns:
            print("Добавляем колонку first_name...")
            cursor.execute("ALTER TABLE lunch_schedule ADD COLUMN first_name TEXT")

        if 'last_name' not in columns:
            print("Добавляем колонку last_name...")
            cursor.execute("ALTER TABLE lunch_schedule ADD COLUMN last_name TEXT")

        # Сохраняем изменения
        connection.commit()
        print("✅ Миграция успешно завершена!")

        # Показываем текущую структуру таблицы
        cursor.execute("PRAGMA table_info(lunch_schedule)")
        columns_info = cursor.fetchall()
        print("\n📋 Текущая структура таблицы lunch_schedule:")
        for column in columns_info:
            print(f"  - {column[1]} ({column[2]})")

    except Exception as e:
        print(f"❌ Ошибка при миграции: {e}")
        connection.rollback()
    finally:
        connection.close()

if __name__ == "__main__":
    migrate_database()